"""
API依赖项模块

本模块提供FastAPI路由中常用的依赖项函数，主要包括：
- 用户认证：从JWT令牌中提取和验证用户身份
- 权限检查：验证用户角色和权限
- 数据库会话：提供数据库访问

这些依赖项通过FastAPI的依赖注入系统使用，可以在路由函数中
通过Depends()声明，自动完成认证和授权检查。

使用示例：
    @router.get("/protected")
    def protected_route(current_user: User = Depends(get_current_user)):
        return {"user": current_user.username}
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models.user import User, UserRole
from app.core.exceptions import AuthenticationError, AuthorizationError

# OAuth2密码认证方案配置
# tokenUrl指定获取令牌的端点，用于Swagger UI的"Authorize"功能
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    获取当前认证用户
    
    从请求的Authorization头中提取JWT令牌，验证令牌有效性，
    并从数据库中查询对应的用户对象。这是最基础的认证依赖项。
    
    Args:
        db: 数据库会话（自动注入）
        token: JWT访问令牌（从Authorization头自动提取）
    
    Returns:
        User: 当前认证的用户对象
    
    Raises:
        AuthenticationError: 令牌无效、用户不存在或账号已禁用
    
    使用示例：
        @router.get("/profile")
        def get_profile(user: User = Depends(get_current_user)):
            return {"username": user.username}
    """
    # 验证JWT令牌并提取用户ID
    user_id = verify_token(token, "access")
    if not user_id:
        raise AuthenticationError("无效的访问令牌")
    
    # 从数据库查询用户
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise AuthenticationError("用户不存在")
    
    # 检查用户账号状态
    if not user.is_active:
        raise AuthenticationError("用户账号已被禁用")
    
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前活跃用户
    
    在get_current_user的基础上，额外确保用户账号处于活跃状态。
    这是一个便捷的依赖项，语义更明确。
    
    Args:
        current_user: 当前用户（通过get_current_user注入）
    
    Returns:
        User: 活跃的用户对象
    
    Raises:
        AuthenticationError: 用户账号已被禁用
    
    使用示例：
        @router.post("/action")
        def perform_action(user: User = Depends(get_current_active_user)):
            # 确保用户是活跃状态
            pass
    """
    if not current_user.is_active:
        raise AuthenticationError("用户账号已被禁用")
    return current_user


def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前管理员用户
    
    验证当前用户是否具有管理员权限。用于需要管理员权限的端点。
    
    Args:
        current_user: 当前用户（通过get_current_user注入）
    
    Returns:
        User: 具有管理员权限的用户对象
    
    Raises:
        AuthorizationError: 用户不是管理员
    
    使用示例：
        @router.delete("/users/{user_id}")
        def delete_user(
            user_id: int,
            admin: User = Depends(get_current_admin_user)
        ):
            # 只有管理员可以删除用户
            pass
    """
    if current_user.role != UserRole.ADMIN:
        raise AuthorizationError("需要管理员权限")
    return current_user


def get_optional_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[User]:
    """
    获取可选的当前用户
    
    用于支持可选认证的端点。如果请求包含有效的令牌，返回用户对象；
    否则返回None。不会抛出认证异常，允许匿名访问。
    
    适用场景：
    - 公开端点，但认证用户可以获得额外功能
    - 内容根据用户身份显示不同结果
    - 统计认证和匿名用户的访问
    
    Args:
        db: 数据库会话（自动注入）
        token: 可选的JWT访问令牌
    
    Returns:
        Optional[User]: 如果认证成功返回用户对象，否则返回None
    
    使用示例：
        @router.get("/content")
        def get_content(user: Optional[User] = Depends(get_optional_current_user)):
            if user:
                return {"content": "premium", "user": user.username}
            return {"content": "basic"}
    """
    # 如果没有提供令牌，返回None（匿名访问）
    if not token:
        return None
    
    try:
        # 尝试验证令牌并获取用户
        user_id = verify_token(token, "access")
        if not user_id:
            return None
        
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            return None
        
        return user
    except Exception:
        # 任何异常都返回None，不影响匿名访问
        return None