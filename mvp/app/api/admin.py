"""
Admin API Endpoints - 管理员专用API端点

本模块提供管理员专用的API端点。

端点列表：
    - GET /api/v1/admin/users: 列出所有用户
    - GET /api/v1/admin/users/{user_id}: 根据ID获取用户
    - DELETE /api/v1/admin/users/{user_id}: 删除用户

功能特性：
    - 用户管理：查看、删除用户
    - 安全限制：不能删除自己的账户
    - 权限控制：所有端点都需要管理员权限

权限要求：
    - 所有端点都需要管理员角色

使用示例：
    >>> # 列出所有用户
    >>> response = requests.get(
    ...     "http://localhost:8000/api/v1/admin/users",
    ...     headers={"Authorization": f"Bearer {admin_token}"}
    ... )
    >>> 
    >>> # 获取特定用户
    >>> response = requests.get(
    ...     "http://localhost:8000/api/v1/admin/users/1",
    ...     headers={"Authorization": f"Bearer {admin_token}"}
    ... )
    >>> 
    >>> # 删除用户
    >>> response = requests.delete(
    ...     "http://localhost:8000/api/v1/admin/users/2",
    ...     headers={"Authorization": f"Bearer {admin_token}"}
    ... )
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.deps import get_current_user, get_db
from app.core.permissions import require_admin
from app.models.user import User
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/users", response_model=List[UserResponse])
@require_admin
async def list_all_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all users (admin only)
    列出所有用户（仅管理员）
    
    Requires admin role.
    """
    users = db.query(User).all()
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
@require_admin
async def get_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user by ID (admin only)
    根据ID获取用户（仅管理员）
    
    Requires admin role.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.delete("/users/{user_id}")
@require_admin
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete user by ID (admin only)
    根据ID删除用户（仅管理员）
    
    Requires admin role.
    Cannot delete yourself.
    """
    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db.delete(user)
    db.commit()
    
    return {"message": f"User {user.username} deleted successfully"}
