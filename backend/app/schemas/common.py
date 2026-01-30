"""
通用的Pydantic模式
"""

from pydantic import BaseModel
from typing import Any, Optional, List, Generic, TypeVar
from datetime import datetime

T = TypeVar('T')


class APIResponse(BaseModel, Generic[T]):
    """统一API响应格式"""
    code: int = 200
    message: str = "success"
    data: Optional[T] = None
    timestamp: datetime = datetime.utcnow()
    request_id: Optional[str] = None


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = 1
    size: int = 20
    
    def get_offset(self) -> int:
        return (self.page - 1) * self.size
    
    def get_limit(self) -> int:
        return self.size


class PaginationResponse(BaseModel, Generic[T]):
    """分页响应"""
    items: List[T]
    pagination: "PaginationInfo"


class PaginationInfo(BaseModel):
    """分页信息"""
    page: int
    size: int
    total: int
    pages: int
    
    @classmethod
    def create(cls, page: int, size: int, total: int) -> "PaginationInfo":
        pages = (total + size - 1) // size  # 向上取整
        return cls(page=page, size=size, total=total, pages=pages)


class HealthCheck(BaseModel):
    """健康检查响应"""
    status: str = "healthy"
    service: str
    version: str
    timestamp: datetime = datetime.utcnow()


class ErrorResponse(BaseModel):
    """错误响应"""
    code: int
    message: str
    details: Optional[dict] = None
    timestamp: datetime = datetime.utcnow()
    request_id: Optional[str] = None