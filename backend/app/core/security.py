"""
安全认证模块

本模块提供应用程序的核心安全功能，包括：
- JWT令牌的创建和验证（访问令牌和刷新令牌）
- 密码的加密和验证（使用bcrypt算法）
- 密码重置令牌的生成和验证
- 会话令牌和API密钥的生成

技术栈：
- python-jose: JWT令牌处理
- passlib: 密码加密（bcrypt算法）
- secrets: 安全随机数生成

使用示例：
    # 创建访问令牌
    token = create_access_token(subject=user.id)
    
    # 验证密码
    is_valid = verify_password(plain_password, hashed_password)
    
    # 生成密码哈希
    hashed = get_password_hash(password)
"""

from datetime import datetime, timedelta
from typing import Any, Union, Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status
import secrets

from app.core.config import settings

# 密码加密上下文配置
# 使用bcrypt算法进行密码哈希，deprecated="auto"表示自动处理旧版本的哈希
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建JWT访问令牌
    
    访问令牌用于API请求的身份验证，有效期较短（默认配置）。
    令牌包含用户标识、过期时间和令牌类型信息。
    
    Args:
        subject: 令牌主体，通常是用户ID或用户名
        expires_delta: 可选的过期时间增量，如果不提供则使用配置的默认值
    
    Returns:
        str: 编码后的JWT令牌字符串
    
    示例：
        >>> token = create_access_token(subject="user123")
        >>> token = create_access_token(subject="user123", expires_delta=timedelta(hours=1))
    """
    # 计算令牌过期时间
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # 使用配置文件中的默认过期时间
        expire = datetime.utcnow() + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    # 构建令牌载荷
    # exp: 过期时间，sub: 主体（用户标识），type: 令牌类型
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    
    # 使用密钥和算法对载荷进行编码
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建JWT刷新令牌
    
    刷新令牌用于获取新的访问令牌，有效期较长（默认以天为单位）。
    当访问令牌过期时，客户端可以使用刷新令牌获取新的访问令牌，
    而无需用户重新登录。
    
    Args:
        subject: 令牌主体，通常是用户ID或用户名
        expires_delta: 可选的过期时间增量，如果不提供则使用配置的默认值
    
    Returns:
        str: 编码后的JWT刷新令牌字符串
    
    示例：
        >>> refresh_token = create_refresh_token(subject="user123")
        >>> refresh_token = create_refresh_token(subject="user123", expires_delta=timedelta(days=30))
    """
    # 计算令牌过期时间
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # 使用配置文件中的默认过期时间（天数）
        expire = datetime.utcnow() + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
    
    # 构建令牌载荷，type标记为refresh以区分访问令牌
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    
    # 使用密钥和算法对载荷进行编码
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[str]:
    """
    验证JWT令牌并提取用户标识
    
    解码JWT令牌，验证其有效性、类型和过期时间，并提取用户标识。
    如果令牌无效、类型不匹配或已过期，返回None。
    
    Args:
        token: JWT令牌字符串
        token_type: 期望的令牌类型，"access"或"refresh"，默认为"access"
    
    Returns:
        Optional[str]: 如果验证成功返回用户标识（subject），否则返回None
    
    示例：
        >>> user_id = verify_token(token, token_type="access")
        >>> if user_id:
        ...     print(f"Token valid for user: {user_id}")
    """
    try:
        # 解码JWT令牌
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # 检查令牌类型是否匹配
        # 防止使用刷新令牌进行API访问，或反之
        if payload.get("type") != token_type:
            return None
            
        # 获取用户ID（令牌主体）
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
            
        return user_id
    except JWTError:
        # JWT解码失败（令牌格式错误、签名无效、已过期等）
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码与哈希密码是否匹配
    
    使用bcrypt算法验证用户输入的明文密码是否与数据库中存储的
    哈希密码匹配。这是用户登录时的核心验证步骤。
    
    Args:
        plain_password: 用户输入的明文密码
        hashed_password: 数据库中存储的哈希密码
    
    Returns:
        bool: 如果密码匹配返回True，否则返回False
    
    示例：
        >>> is_valid = verify_password("user_password", stored_hash)
        >>> if is_valid:
        ...     print("Password correct")
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    生成密码的哈希值
    
    使用bcrypt算法对明文密码进行哈希处理。bcrypt是一种自适应哈希函数，
    专门设计用于密码存储，具有以下特点：
    - 自动加盐（salt）
    - 计算成本可调
    - 抗彩虹表攻击
    
    Args:
        password: 明文密码
    
    Returns:
        str: 哈希后的密码字符串，可安全存储在数据库中
    
    示例：
        >>> hashed = get_password_hash("user_password")
        >>> # 存储hashed到数据库
    """
    return pwd_context.hash(password)


def generate_password_reset_token(email: str) -> str:
    """
    生成密码重置令牌
    
    为用户的密码重置请求生成一个临时令牌。该令牌通常通过邮件发送给用户，
    用户点击邮件中的链接（包含该令牌）来重置密码。
    
    安全特性：
    - 24小时有效期，过期后无法使用
    - 包含nbf（not before）时间戳，防止令牌被提前使用
    - 令牌中包含用户邮箱，确保只能重置对应账户的密码
    
    Args:
        email: 用户的邮箱地址
    
    Returns:
        str: 编码后的密码重置令牌
    
    示例：
        >>> token = generate_password_reset_token("user@example.com")
        >>> # 将token通过邮件发送给用户
    """
    delta = timedelta(hours=24)  # 24小时有效期
    now = datetime.utcnow()
    expires = now + delta
    exp = expires.timestamp()
    
    # 构建令牌载荷
    # exp: 过期时间，nbf: 生效时间，sub: 用户邮箱
    encoded_jwt = jwt.encode(
        {"exp": exp, "nbf": now, "sub": email}, 
        settings.SECRET_KEY, 
        algorithm="HS256"
    )
    return encoded_jwt


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    验证密码重置令牌并提取邮箱
    
    验证用户提供的密码重置令牌是否有效，并提取其中的邮箱地址。
    如果令牌无效或已过期，返回None。
    
    Args:
        token: 密码重置令牌字符串
    
    Returns:
        Optional[str]: 如果令牌有效返回邮箱地址，否则返回None
    
    示例：
        >>> email = verify_password_reset_token(token)
        >>> if email:
        ...     # 允许用户重置该邮箱对应账户的密码
        ...     reset_password(email, new_password)
    """
    try:
        # 解码令牌并提取邮箱
        decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return decoded_token["sub"]
    except JWTError:
        # 令牌无效、已过期或签名错误
        return None


def generate_session_token() -> str:
    """
    生成安全的会话令牌
    
    使用密码学安全的随机数生成器创建会话令牌。该令牌可用于：
    - 用户会话标识
    - CSRF保护
    - 临时授权码
    
    生成的令牌是URL安全的，可以直接在URL参数或Cookie中使用。
    
    Returns:
        str: 32字节的URL安全随机令牌（Base64编码后约43个字符）
    
    示例：
        >>> session_token = generate_session_token()
        >>> # 存储到Redis或数据库中作为会话标识
    """
    return secrets.token_urlsafe(32)


def generate_api_key() -> str:
    """
    生成API密钥
    
    使用密码学安全的随机数生成器创建API密钥。API密钥用于：
    - 第三方应用访问API
    - 服务间认证
    - 长期有效的访问凭证
    
    生成的密钥是URL安全的，可以直接在HTTP头部或URL参数中使用。
    
    Returns:
        str: 32字节的URL安全随机密钥（Base64编码后约43个字符）
    
    安全建议：
        - API密钥应该安全存储，不要明文记录在日志中
        - 建议在数据库中存储密钥的哈希值
        - 支持密钥的撤销和轮换机制
    
    示例：
        >>> api_key = generate_api_key()
        >>> # 返回给用户，并在数据库中存储其哈希值
    """
    return secrets.token_urlsafe(32)