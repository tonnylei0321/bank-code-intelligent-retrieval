"""
Authentication Schemas - 认证相关的Pydantic模式

本模块定义认证和用户管理相关的数据模型。

模式列表：
    - Token: JWT令牌响应
    - TokenData: JWT令牌中编码的数据
    - LoginRequest: 登录请求
    - UserResponse: 用户信息响应（不含密码）
    - UserCreate: 用户创建请求
    - UserUpdate: 用户更新请求

使用示例：
    >>> # 登录请求
    >>> login = LoginRequest(username="admin", password="password123")
    >>> 
    >>> # 用户创建
    >>> user = UserCreate(
    ...     username="newuser",
    ...     email="user@example.com",
    ...     password="password123",
    ...     role="user"
    ... )
    >>> 
    >>> # Token响应
    >>> token = Token(access_token="eyJ...", token_type="bearer")

验证规则：
    - username: 3-50个字符
    - password: 至少6个字符
    - email: 必须是有效的邮箱格式
    - role: 只能是"admin"或"user"
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class Token(BaseModel):
    """
    JWT令牌响应模式
    
    用于返回登录成功后的访问令牌。
    
    属性：
        access_token (str): JWT访问令牌字符串
        token_type (str): 令牌类型，默认为"bearer"
    """
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """
    JWT令牌数据模式
    
    定义JWT令牌中编码的用户信息。
    
    属性：
        user_id (Optional[int]): 用户ID
        username (Optional[str]): 用户名
        role (Optional[str]): 用户角色（admin/user）
    """
    user_id: Optional[int] = None
    username: Optional[str] = None
    role: Optional[str] = None


class LoginRequest(BaseModel):
    """
    登录请求模式
    
    用于用户登录时提交的数据。
    
    属性：
        username (str): 用户名，3-50个字符
        password (str): 密码，至少6个字符
    """
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class UserResponse(BaseModel):
    """
    用户信息响应模式
    
    用于返回用户信息（不包含密码）。
    
    属性：
        id (int): 用户ID
        username (str): 用户名
        email (str): 电子邮箱
        role (str): 用户角色
        is_active (bool): 账户是否激活
        created_at (str): 创建时间
    """
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: str
    
    class Config:
        from_attributes = True  # 支持从SQLAlchemy模型转换


class UserCreate(BaseModel):
    """
    用户创建请求模式
    
    用于创建新用户时提交的数据。
    
    属性：
        username (str): 用户名，3-50个字符
        email (EmailStr): 电子邮箱，必须是有效格式
        password (str): 密码，至少6个字符
        role (str): 用户角色，只能是"admin"或"user"，默认为"user"
    """
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: str = Field(default="user", pattern="^(admin|user)$")


class UserUpdate(BaseModel):
    """
    用户更新请求模式
    
    用于更新用户信息时提交的数据。所有字段都是可选的。
    
    属性：
        email (Optional[EmailStr]): 新的电子邮箱
        password (Optional[str]): 新的密码，至少6个字符
        role (Optional[str]): 新的角色，只能是"admin"或"user"
        is_active (Optional[bool]): 账户激活状态
    """
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)
    role: Optional[str] = Field(None, pattern="^(admin|user)$")
    is_active: Optional[bool] = None
