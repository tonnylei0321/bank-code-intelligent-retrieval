"""
API请求频率限制中间件模块

提供基于滑动窗口算法的请求频率限制功能，用于：
1. 防止API滥用和DDoS攻击
2. 保护服务器资源
3. 确保服务质量

特性：
- 基于内存的计数器（适合单机部署）
- 滑动窗口算法（更精确的限流）
- 支持按用户ID或IP地址限流
- 自动清理过期记录
- 提供详细的限流响应头
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, Tuple
import time

from app.core.logging import logger


class RateLimiter:
    """
    基于滑动窗口算法的内存限流器
    
    使用滑动时间窗口算法跟踪每个客户端的请求频率。
    相比固定窗口算法，滑动窗口能更精确地控制请求速率。
    
    工作原理：
    1. 为每个客户端维护一个请求时间戳列表
    2. 检查请求时，清理超出时间窗口的旧记录
    3. 统计当前窗口内的请求数量
    4. 如果超过限制则拒绝请求
    
    注意：
        - 数据存储在内存中，重启后会丢失
        - 不适合分布式部署（建议使用Redis）
    """
    
    def __init__(self, requests_per_minute: int = 100):
        """
        初始化限流器
        
        Args:
            requests_per_minute: 每个客户端每分钟允许的最大请求数，默认100
        """
        self.requests_per_minute = requests_per_minute  # 每分钟请求限制
        self.window_size = 60  # 时间窗口大小：60秒 = 1分钟
        # 存储每个客户端的请求时间戳列表：{client_id: [timestamp1, timestamp2, ...]}
        self.request_history: Dict[str, list] = defaultdict(list)
        
    def _get_client_id(self, request: Request) -> str:
        """
        从请求中获取客户端标识符
        
        优先使用用户ID（如果已认证），否则使用IP地址。
        这样可以对已登录用户进行更精确的限流控制。
        
        Args:
            request: FastAPI请求对象
            
        Returns:
            客户端标识符字符串（格式：user_<id> 或 ip_<address>）
        """
        # 尝试从请求状态中获取用户ID（由认证中间件设置）
        if hasattr(request.state, "user_id"):
            return f"user_{request.state.user_id}"
        
        # 回退到使用IP地址
        client_ip = request.client.host if request.client else "unknown"
        # 处理代理转发的请求（获取真实IP）
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # X-Forwarded-For可能包含多个IP，取第一个
            client_ip = forwarded.split(",")[0].strip()
        
        return f"ip_{client_ip}"
    
    def _clean_old_requests(self, client_id: str, current_time: float) -> None:
        """
        清理超出时间窗口的旧请求记录
        
        删除时间戳早于(当前时间 - 窗口大小)的请求记录，
        保持内存使用在合理范围内。
        
        Args:
            client_id: 客户端标识符
            current_time: 当前时间戳（秒）
        """
        # 计算截止时间：当前时间减去窗口大小
        cutoff_time = current_time - self.window_size
        # 只保留在时间窗口内的请求记录
        self.request_history[client_id] = [
            ts for ts in self.request_history[client_id]
            if ts > cutoff_time
        ]
    
    def is_allowed(self, request: Request) -> Tuple[bool, int, int]:
        """
        检查请求是否在频率限制内
        
        执行限流检查的核心方法：
        1. 获取客户端标识符
        2. 清理过期的请求记录
        3. 统计当前窗口内的请求数
        4. 判断是否超过限制
        
        Args:
            request: FastAPI请求对象
            
        Returns:
            三元组 (是否允许, 剩余请求数, 重试等待秒数)
            - is_allowed: True表示允许请求，False表示超过限制
            - remaining_requests: 剩余可用请求数
            - retry_after_seconds: 如果被限流，需要等待的秒数
        """
        client_id = self._get_client_id(request)
        current_time = time.time()
        
        # Clean old requests
        self._clean_old_requests(client_id, current_time)
        
        # Count requests in current window
        request_count = len(self.request_history[client_id])
        
        if request_count >= self.requests_per_minute:
            # Rate limit exceeded
            # Calculate retry after time (time until oldest request expires)
            oldest_request = self.request_history[client_id][0]
            retry_after = int(oldest_request + self.window_size - current_time) + 1
            return False, 0, retry_after
        
        # Request allowed
        self.request_history[client_id].append(current_time)
        remaining = self.requests_per_minute - request_count - 1
        return True, remaining, 0
    
    def reset_client(self, client_id: str) -> None:
        """
        Reset rate limit for a specific client (for testing)
        重置特定客户端的限流记录（用于测试）
        
        Args:
            client_id: Client identifier
        """
        if client_id in self.request_history:
            del self.request_history[client_id]
    
    def reset_all(self) -> None:
        """
        Reset all rate limit records (for testing)
        重置所有限流记录（用于测试）
        """
        self.request_history.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting
    FastAPI限流中间件
    """
    
    def __init__(self, app, rate_limiter: RateLimiter):
        """
        Initialize middleware
        
        Args:
            app: FastAPI application
            rate_limiter: RateLimiter instance
        """
        super().__init__(app)
        self.rate_limiter = rate_limiter
        # Paths to exclude from rate limiting (health checks, etc.)
        self.excluded_paths = ["/", "/health", "/docs", "/openapi.json", "/redoc"]
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and apply rate limiting
        处理请求并应用限流
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response or error response if rate limited
        """
        # Skip rate limiting for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Check rate limit
        is_allowed, remaining, retry_after = self.rate_limiter.is_allowed(request)
        
        if not is_allowed:
            # Rate limit exceeded
            client_id = self.rate_limiter._get_client_id(request)
            logger.warning(
                f"Rate limit exceeded for {client_id} on {request.url.path}"
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "success": False,
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "error_message": f"Rate limit exceeded. Maximum {self.rate_limiter.requests_per_minute} requests per minute.",
                    "retry_after": retry_after,
                    "timestamp": datetime.utcnow().isoformat()
                },
                headers={
                    "X-RateLimit-Limit": str(self.rate_limiter.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + retry_after),
                    "Retry-After": str(retry_after)
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(self.rate_limiter.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
