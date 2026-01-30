"""
Authentication API Endpoints - 认证API端点

本模块提供用户认证相关的API端点。

端点列表：
    - POST /api/v1/auth/login: 用户登录
    - GET /api/v1/auth/me: 获取当前用户信息
    - POST /api/v1/auth/register: 注册新用户（仅管理员）

认证流程：
    1. 用户提交用户名和密码到/login端点
    2. 系统验证用户身份
    3. 返回JWT访问令牌
    4. 客户端在后续请求中携带令牌（Authorization: Bearer <token>）
    5. 系统验证令牌并识别用户身份

安全特性：
    - 密码使用bcrypt加密存储
    - JWT令牌有过期时间限制
    - 支持账户禁用功能
    - 记录所有登录尝试

使用示例：
    >>> # 登录
    >>> response = requests.post(
    ...     "http://localhost:8000/api/v1/auth/login",
    ...     data={"username": "admin", "password": "password123"}
    ... )
    >>> token = response.json()["access_token"]
    >>> 
    >>> # 获取当前用户信息
    >>> response = requests.get(
    ...     "http://localhost:8000/api/v1/auth/me",
    ...     headers={"Authorization": f"Bearer {token}"}
    ... )
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.core.deps import get_db, get_current_user, get_current_admin_user
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import Token, UserResponse, LoginRequest, UserCreate
from app.core.logging import logger

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    用户登录端点 - 验证用户身份并返回JWT令牌
    
    本端点接收用户名和密码，验证后返回JWT访问令牌。
    
    Args:
        form_data (OAuth2PasswordRequestForm): OAuth2密码表单（包含username和password）
        db (Session): 数据库会话
        
    Returns:
        Token: JWT访问令牌和令牌类型
        
    Raises:
        HTTPException 401: 如果用户名或密码错误
        HTTPException 403: 如果用户账户未激活
    
    流程：
        1. 根据用户名查找用户
        2. 验证密码是否正确
        3. 检查用户账户是否激活
        4. 生成JWT访问令牌
        5. 记录登录日志
    """
    # 根据用户名查找用户
    user = db.query(User).filter(User.username == form_data.username).first()
    
    # 验证用户存在且密码正确
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Failed login attempt for username: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 检查用户是否激活
    if not user.is_active:
        logger.warning(f"Login attempt for inactive user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # 创建访问令牌
    access_token_expires = timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    access_token = create_access_token(
        data={"user_id": user.id, "username": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    
    logger.info(f"User logged in successfully: {user.username} (role: {user.role})")
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户信息
    
    返回当前已认证用户的详细信息（不包含密码）。
    
    Args:
        current_user (User): 当前已认证的用户对象
        
    Returns:
        UserResponse: 用户信息（id, username, email, role, is_active, created_at）
    """
    return current_user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    注册新用户（仅管理员）
    
    本端点允许管理员创建新用户账户。
    
    Args:
        user_data (UserCreate): 用户创建数据（username, email, password, role）
        db (Session): 数据库会话
        current_admin (User): 当前管理员用户（用于授权）
        
    Returns:
        UserResponse: 创建的用户信息
        
    Raises:
        HTTPException 400: 如果用户名或邮箱已存在
    
    流程：
        1. 检查用户名是否已存在
        2. 检查邮箱是否已存在
        3. 创建新用户（密码使用bcrypt加密）
        4. 保存到数据库
        5. 记录操作日志
    """
    # 检查用户名是否已存在
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # 检查邮箱是否已存在
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # 创建新用户
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role,
        is_active=1
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"New user registered: {new_user.username} (role: {new_user.role}) by admin: {current_admin.username}")
    
    return new_user
