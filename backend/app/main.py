"""
企业级小模型训练平台 - 主应用入口

本模块是FastAPI应用的主入口，负责：
    - 应用初始化和配置
    - 中间件配置（CORS、可信主机、请求计时）
    - 异常处理（自定义异常、全局异常）
    - 路由注册
    - 生命周期管理

应用特性：
    - 自动创建数据库表
    - 请求处理时间追踪
    - 统一的异常响应格式
    - 健康检查端点
    - API文档（Swagger UI和ReDoc）

启动方式：
    开发环境：python -m app.main
    生产环境：uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time
import logging
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1.api import api_router
from app.core.exceptions import CustomException


# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("🚀 启动企业级小模型训练平台")
    
    # 创建数据库表
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ 数据库表创建成功")
    except Exception as e:
        logger.error(f"❌ 数据库表创建失败: {e}")
    
    yield
    
    # 关闭时执行
    logger.info("🛑 关闭企业级小模型训练平台")


# 创建FastAPI应用
app = FastAPI(
    title="企业级小模型训练平台",
    description="基于大模型的智能化小模型训练和部署平台",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加可信主机中间件
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """添加请求处理时间头"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.exception_handler(CustomException)
async def custom_exception_handler(request: Request, exc: CustomException):
    """自定义异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.message,
            "data": None,
            "timestamp": time.time(),
            "request_id": getattr(request.state, "request_id", None)
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "服务器内部错误",
            "data": None,
            "timestamp": time.time(),
            "request_id": getattr(request.state, "request_id", None)
        }
    )


# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "企业级小模型训练平台",
        "version": "1.0.0",
        "timestamp": time.time()
    }


# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "欢迎使用企业级小模型训练平台",
        "docs": "/docs",
        "health": "/health",
        "api": "/api/v1"
    }


# 包含API路由
app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.ENVIRONMENT == "development" else False
    )