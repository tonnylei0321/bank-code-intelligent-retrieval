"""
用户管理API端点
"""

from typing import Any, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_admin_user
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate, UserProfile, PasswordChange
from app.schemas.common import PaginationResponse, PaginationInfo
from app.core.security import verify_password, get_password_hash
from app.core.exceptions import NotFoundError, ValidationError, AuthorizationError

router = APIRouter()


@router.get("/profile", response_model=UserProfile, summary="获取当前用户信息")
async def get_profile(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    获取当前登录用户的个人信息
    """
    return current_user


@router.put("/profile", response_model=UserProfile, summary="更新当前用户信息")
async def update_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    更新当前登录用户的个人信息
    """
    # 只允许更新邮箱
    if user_data.email:
        # 检查邮箱是否已被使用
        existing_user = db.query(User).filter(
            User.email == user_data.email,
            User.id != current_user.id
        ).first()
        if existing_user:
            raise ValidationError("邮箱已被使用")
        
        current_user.email = user_data.email
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.post("/profile/password", summary="修改密码")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    修改当前用户密码
    """
    # 验证旧密码
    if not verify_password(password_data.old_password, current_user.password_hash):
        raise ValidationError("旧密码错误")
    
    # 更新密码
    current_user.password_hash = get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "密码修改成功"}


@router.get("", response_model=PaginationResponse[UserResponse], summary="获取用户列表")
async def get_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    role: str = Query(None),
    is_active: bool = Query(None),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    获取用户列表（仅管理员）
    """
    # 构建查询
    query = db.query(User)
    
    # 过滤条件
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    # 获取总数
    total = query.count()
    
    # 分页查询
    offset = (page - 1) * size
    users = query.offset(offset).limit(size).all()
    
    return {
        "items": users,
        "pagination": PaginationInfo.create(page, size, total)
    }


@router.get("/{user_id}", response_model=UserResponse, summary="获取用户详情")
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    获取指定用户详情（仅管理员）
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("用户不存在")
    
    return user


@router.put("/{user_id}", response_model=UserResponse, summary="更新用户信息")
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    更新指定用户信息（仅管理员）
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("用户不存在")
    
    # 更新字段
    if user_data.email:
        # 检查邮箱是否已被使用
        existing_user = db.query(User).filter(
            User.email == user_data.email,
            User.id != user_id
        ).first()
        if existing_user:
            raise ValidationError("邮箱已被使用")
        user.email = user_data.email
    
    if user_data.password:
        user.password_hash = get_password_hash(user_data.password)
    
    if user_data.role:
        user.role = user_data.role
    
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/{user_id}", summary="删除用户")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    删除指定用户（仅管理员）
    """
    # 不能删除自己
    if user_id == current_user.id:
        raise ValidationError("不能删除自己")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("用户不存在")
    
    db.delete(user)
    db.commit()
    
    return {"message": "用户删除成功"}