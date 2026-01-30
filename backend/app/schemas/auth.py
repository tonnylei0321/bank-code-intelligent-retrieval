"""
认证相关的Pydantic模式
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any


class Token(BaseModel):
    """令牌响应模式"""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: Dict[str, Any]


class TokenRefresh(BaseModel):
    """令牌刷新请求模式"""
    refresh_token: str


class LoginRequest(BaseModel):
    """登录请求模式"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """登录响应模式"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: Dict[str, Any]