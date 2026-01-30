"""
自定义异常类

本模块定义了应用中使用的所有自定义异常类。

异常层次：
    CustomException（基类）
    ├── ValidationError（422）- 数据验证错误
    ├── AuthenticationError（401）- 认证失败
    ├── AuthorizationError（403）- 权限不足
    ├── NotFoundError（404）- 资源不存在
    ├── ConflictError（409）- 资源冲突
    ├── BusinessError（400）- 业务逻辑错误
    ├── TrainingError（500）- 训练相关错误
    ├── ModelError（500）- 模型相关错误
    └── DataError（400）- 数据相关错误

使用方式：
    from app.core.exceptions import NotFoundError
    
    if not user:
        raise NotFoundError("用户不存在")
"""

from typing import Any, Dict, Optional


class CustomException(Exception):
    """自定义异常基类"""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(CustomException):
    """数据验证错误"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 422, details)


class AuthenticationError(CustomException):
    """认证错误"""
    
    def __init__(self, message: str = "认证失败"):
        super().__init__(message, 401)


class AuthorizationError(CustomException):
    """授权错误"""
    
    def __init__(self, message: str = "权限不足"):
        super().__init__(message, 403)


class NotFoundError(CustomException):
    """资源不存在错误"""
    
    def __init__(self, message: str = "资源不存在"):
        super().__init__(message, 404)


class ConflictError(CustomException):
    """资源冲突错误"""
    
    def __init__(self, message: str = "资源冲突"):
        super().__init__(message, 409)


class BusinessError(CustomException):
    """业务逻辑错误"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 400, details)


class TrainingError(CustomException):
    """训练相关错误"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 500, details)


class ModelError(CustomException):
    """模型相关错误"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 500, details)


class DataError(CustomException):
    """数据相关错误"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 400, details)