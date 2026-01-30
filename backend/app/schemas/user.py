"""
用户相关的Pydantic模式
"""

from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    USER = "user"


class UserBase(BaseModel):
    """用户基础模式"""
    username: str
    email: EmailStr
    role: UserRole = UserRole.USER


class UserCreate(UserBase):
    """用户创建模式"""
    password: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('密码长度至少6位')
        return v
    
    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('用户名长度至少3位')
        if not v.isalnum():
            raise ValueError('用户名只能包含字母和数字')
        return v


class UserUpdate(BaseModel):
    """用户更新模式"""
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    
    @validator('password')
    def validate_password(cls, v):
        if v is not None and len(v) < 6:
            raise ValueError('密码长度至少6位')
        return v


class UserResponse(UserBase):
    """用户响应模式"""
    id: int
    is_active: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    """用户个人资料模式"""
    id: int
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class PasswordChange(BaseModel):
    """密码修改模式"""
    old_password: str
    new_password: str
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 6:
            raise ValueError('新密码长度至少6位')
        return v