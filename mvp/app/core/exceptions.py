"""
Custom exceptions and unified error response handling
自定义异常和统一错误响应处理
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from datetime import datetime
from typing import Optional, Dict, Any
import uuid

from app.core.logging import logger


class APIException(Exception):
    """
    Base API exception with error code and details
    基础API异常，包含错误码和详情
    """
    
    def __init__(
        self,
        error_code: str,
        error_message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize API exception
        
        Args:
            error_code: Error code (e.g., "INVALID_FILE_FORMAT")
            error_message: Human-readable error message
            status_code: HTTP status code
            error_details: Additional error details
        """
        self.error_code = error_code
        self.error_message = error_message
        self.status_code = status_code
        self.error_details = error_details or {}
        super().__init__(error_message)


class ErrorResponse:
    """
    Unified error response format
    统一错误响应格式
    """
    
    @staticmethod
    def create(
        error_code: str,
        error_message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create standardized error response
        创建标准化错误响应
        
        Args:
            error_code: Error code
            error_message: Error message
            status_code: HTTP status code
            error_details: Additional error details
            request_id: Request ID for tracking
            
        Returns:
            Error response dictionary
        """
        return {
            "success": False,
            "error_code": error_code,
            "error_message": error_message,
            "error_details": error_details,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id or str(uuid.uuid4())
        }


class SuccessResponse:
    """
    Unified success response format
    统一成功响应格式
    """
    
    @staticmethod
    def create(
        data: Any,
        message: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create standardized success response
        创建标准化成功响应
        
        Args:
            data: Response data
            message: Optional success message
            meta: Optional metadata
            
        Returns:
            Success response dictionary
        """
        response = {
            "success": True,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if message:
            response["message"] = message
        
        if meta:
            response["meta"] = meta
        
        return response


# Custom exception handlers

async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """
    Handler for custom API exceptions
    自定义API异常处理器
    
    Args:
        request: FastAPI request
        exc: API exception
        
    Returns:
        JSON error response
    """
    request_id = str(uuid.uuid4())
    
    logger.error(
        f"API Exception [{request_id}]: {exc.error_code} - {exc.error_message}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "error_code": exc.error_code,
            "error_details": exc.error_details
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse.create(
            error_code=exc.error_code,
            error_message=exc.error_message,
            status_code=exc.status_code,
            error_details=exc.error_details,
            request_id=request_id
        )
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handler for HTTP exceptions
    HTTP异常处理器
    
    Args:
        request: FastAPI request
        exc: HTTP exception
        
    Returns:
        JSON error response
    """
    request_id = str(uuid.uuid4())
    
    # Map HTTP status codes to error codes
    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_SERVER_ERROR",
        503: "SERVICE_UNAVAILABLE"
    }
    
    error_code = error_code_map.get(exc.status_code, "UNKNOWN_ERROR")
    
    logger.warning(
        f"HTTP Exception [{request_id}]: {exc.status_code} - {exc.detail}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse.create(
            error_code=error_code,
            error_message=str(exc.detail),
            status_code=exc.status_code,
            request_id=request_id
        )
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handler for request validation errors
    请求验证错误处理器
    
    Args:
        request: FastAPI request
        exc: Validation error
        
    Returns:
        JSON error response
    """
    request_id = str(uuid.uuid4())
    
    # Extract validation errors
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        f"Validation Error [{request_id}]: {len(errors)} validation errors",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "errors": errors
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse.create(
            error_code="VALIDATION_ERROR",
            error_message="Request validation failed",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_details={"validation_errors": errors},
            request_id=request_id
        )
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler for unhandled exceptions
    未处理异常的处理器
    
    Args:
        request: FastAPI request
        exc: Exception
        
    Returns:
        JSON error response
    """
    request_id = str(uuid.uuid4())
    
    logger.exception(
        f"Unhandled Exception [{request_id}]: {type(exc).__name__} - {str(exc)}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse.create(
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred. Please try again later.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_details={"exception_type": type(exc).__name__},
            request_id=request_id
        )
    )


def register_exception_handlers(app):
    """
    Register all exception handlers with FastAPI app
    注册所有异常处理器到FastAPI应用
    
    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
