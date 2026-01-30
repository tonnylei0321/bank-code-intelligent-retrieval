"""
FastAPI依赖注入函数模块

提供常用的依赖注入函数，包括：
1. 数据库会话获取
2. 当前用户认证
3. 活跃用户验证
4. 管理员权限验证

这些函数用于FastAPI的Depends系统，简化路由处理函数的参数注入。
"""
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import decode_access_token
from app.models.user import User
from app.schemas.auth import TokenData

# OAuth2认证方案，用于从请求头中提取JWT token
# tokenUrl指定获取token的登录端点
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_db() -> Generator[Session, None, None]:
    """
    数据库会话依赖注入函数
    
    为每个请求创建一个独立的数据库会话，
    请求处理完成后自动关闭会话。
    
    使用示例:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    
    Yields:
        SQLAlchemy数据库会话对象
    """
    db = SessionLocal()
    try:
        yield db  # 提供会话给路由处理函数
    finally:
        db.close()  # 请求结束后关闭会话


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    从JWT token获取当前认证用户
    
    验证JWT token并从数据库中获取对应的用户对象。
    这是大多数需要认证的端点的基础依赖。
    
    验证流程：
    1. 解码JWT token
    2. 提取用户ID
    3. 从数据库查询用户
    4. 检查用户是否活跃
    
    Args:
        token: JWT访问令牌（从Authorization头自动提取）
        db: 数据库会话（自动注入）
        
    Returns:
        当前认证的用户对象
        
    Raises:
        HTTPException 401: token无效或用户不存在
        HTTPException 403: 用户账号已停用
    
    使用示例:
        @app.get("/profile")
        def get_profile(current_user: User = Depends(get_current_user)):
            return {"username": current_user.username}
    """
    # 准备认证失败的异常
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 解码token
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    # 从token中提取用户信息
    user_id: Optional[int] = payload.get("user_id")
    if user_id is None:
        raise credentials_exception
    
    # 从数据库获取用户
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    # 检查用户是否活跃
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账号已停用"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前活跃用户
    
    在get_current_user的基础上，额外验证用户账号是否活跃。
    这是一个便捷函数，用于需要确保用户活跃的端点。
    
    Args:
        current_user: 当前用户（从get_current_user注入）
        
    Returns:
        当前活跃用户对象
        
    Raises:
        HTTPException 403: 用户账号已停用
    
    使用示例:
        @app.post("/action")
        def perform_action(current_user: User = Depends(get_current_active_user)):
            # 确保用户账号是活跃的
            ...
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账号已停用"
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前管理员用户（要求管理员角色）
    
    验证当前用户是否具有管理员权限。
    用于需要管理员权限的端点。
    
    Args:
        current_user: 当前用户（从get_current_user注入）
        
    Returns:
        当前管理员用户对象
        
    Raises:
        HTTPException 403: 用户不是管理员
    
    使用示例:
        @app.delete("/users/{user_id}")
        def delete_user(
            user_id: int,
            admin: User = Depends(get_current_admin_user)
        ):
            # 只有管理员可以删除用户
            ...
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足：需要管理员角色"
        )
    return current_user
