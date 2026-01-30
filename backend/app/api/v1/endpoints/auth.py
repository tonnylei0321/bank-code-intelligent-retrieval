"""
认证相关API端点
"""

from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    verify_password,
    get_password_hash
)
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import Token, TokenRefresh
from app.schemas.user import UserCreate, UserResponse
from app.core.exceptions import AuthenticationError, ValidationError

router = APIRouter()


@router.post("/login", response_model=Token, summary="用户登录")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """
    用户登录
    """
    # 查找用户
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise AuthenticationError("用户名或密码错误")
    
    if not user.is_active:
        raise AuthenticationError("用户账号已被禁用")
    
    # 创建访问令牌和刷新令牌
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        subject=user.id, expires_delta=refresh_token_expires
    )
    
    # 更新最后登录时间
    from datetime import datetime
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }


@router.post("/refresh", response_model=Token, summary="刷新令牌")
async def refresh_token(
    token_data: TokenRefresh,
    db: Session = Depends(get_db)
) -> Any:
    """
    刷新访问令牌
    """
    # 验证刷新令牌
    user_id = verify_token(token_data.refresh_token, "refresh")
    if not user_id:
        raise AuthenticationError("无效的刷新令牌")
    
    # 查找用户
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise AuthenticationError("用户不存在或已被禁用")
    
    # 创建新的访问令牌
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "refresh_token": token_data.refresh_token,
        "token_type": "Bearer",
        "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }


@router.post("/logout", summary="用户登出")
async def logout() -> Any:
    """
    用户登出
    注意：由于使用JWT，实际的登出需要在客户端删除令牌
    """
    return {"message": "登出成功"}


@router.post("/register", response_model=UserResponse, summary="用户注册")
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
) -> Any:
    """
    用户注册（仅管理员可用）
    """
    # 检查用户名是否已存在
    if db.query(User).filter(User.username == user_data.username).first():
        raise ValidationError("用户名已存在")
    
    # 检查邮箱是否已存在
    if db.query(User).filter(User.email == user_data.email).first():
        raise ValidationError("邮箱已存在")
    
    # 创建新用户
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user