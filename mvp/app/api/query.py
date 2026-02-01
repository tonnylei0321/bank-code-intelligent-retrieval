"""
Query API Endpoints - 查询服务API端点

本模块提供银行联行号查询相关的API端点。

端点列表：
    - POST /api/v1/query/: 单个查询
    - POST /api/v1/query/batch: 批量查询
    - GET /api/v1/query/history: 查询历史记录

查询流程：
    1. 用户提交自然语言问题
    2. 系统使用训练好的模型生成答案
    3. 从答案中提取银行联行号
    4. 在数据库中查找完整的银行信息
    5. 计算置信度分数
    6. 记录查询日志
    7. 返回结构化响应

特性：
    - 支持自然语言查询
    - 自动提取联行号信息
    - 置信度评分
    - 查询历史记录
    - 批量查询支持

权限要求：
    - 所有认证用户都可以使用查询功能
    - 用户只能查看自己的查询历史

使用示例：
    >>> # 单个查询
    >>> response = requests.post(
    ...     "http://localhost:8000/api/v1/query/",
    ...     json={"question": "中国工商银行北京分行的联行号是什么？"},
    ...     headers={"Authorization": f"Bearer {token}"}
    ... )
    >>> print(response.json()["answer"])
    >>> 
    >>> # 批量查询
    >>> response = requests.post(
    ...     "http://localhost:8000/api/v1/query/batch",
    ...     json={"questions": ["工行的联行号？", "建行的联行号？"]},
    ...     headers={"Authorization": f"Bearer {token}"}
    ... )
    >>> 
    >>> # 查询历史
    >>> response = requests.get(
    ...     "http://localhost:8000/api/v1/query/history?limit=10",
    ...     headers={"Authorization": f"Bearer {token}"}
    ... )
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query as QueryParam
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field

from app.core.deps import get_current_user, get_db, get_current_admin_user
from app.models.user import User
from app.services.query_service import QueryService, QueryServiceError
from app.core.logging import logger

router = APIRouter(prefix="/api/v1/query", tags=["query"])


# Pydantic schemas for request/response
class QueryRequest(BaseModel):
    """Single query request"""
    question: str = Field(..., min_length=1, max_length=500, description="User's question")
    model_id: Optional[int] = Field(None, description="Training job ID to use for query (optional, uses latest if not specified)")
    use_rag: bool = Field(True, description="Whether to use RAG (Retrieval-Augmented Generation)")
    top_k: int = Field(5, ge=1, le=20, description="Number of documents to retrieve for RAG")


class BatchQueryRequest(BaseModel):
    """Batch query request"""
    questions: List[str] = Field(..., min_items=1, max_items=100, description="List of questions")


class BankCodeInfo(BaseModel):
    """Bank code information"""
    bank_name: str
    bank_code: str
    clearing_code: str


class QueryResponse(BaseModel):
    """Query response"""
    question: str
    answer: str
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    response_time: float = Field(..., description="Response time in milliseconds")
    matched_records: List[BankCodeInfo]
    timestamp: float


class BatchQueryResponse(BaseModel):
    """Batch query response"""
    results: List[QueryResponse]
    total_queries: int
    successful_queries: int
    failed_queries: int


class QueryHistoryItem(BaseModel):
    """Query history item"""
    id: int
    user_id: Optional[int]
    question: str
    answer: str
    confidence: Optional[float]
    response_time: Optional[float]
    model_version: Optional[str]
    created_at: str


class QueryHistoryResponse(BaseModel):
    """Query history response"""
    items: List[QueryHistoryItem]
    total: int
    limit: int
    offset: int


# Global query service instance (will be initialized on startup)
_query_service: Optional[QueryService] = None


# Global model cache to avoid reloading models for every request
_model_cache = {}
_cache_lock = {}
_max_cached_models = 1  # 限制缓存的模型数量，避免内存不足

def clear_gpu_memory():
    """清理GPU内存"""
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            torch.mps.empty_cache()
        logger.info("GPU memory cleared")
    except Exception as e:
        logger.warning(f"Failed to clear GPU memory: {e}")

def get_cached_query_service(model_path: str, db: Session) -> QueryService:
    """
    Get or create a cached query service for the specified model
    
    Args:
        model_path: Path to the model
        db: Database session
    
    Returns:
        Cached QueryService instance
    """
    global _model_cache, _cache_lock, _max_cached_models
    
    # Use model path as cache key
    cache_key = model_path
    
    # Check if model is already loaded
    if cache_key in _model_cache:
        service = _model_cache[cache_key]
        # 重要修复：确保数据库会话是新鲜的
        service.db = db
        # 确保会话状态正常
        try:
            if not service.db.is_active:
                service.db.rollback()  # 重置会话状态
        except Exception as e:
            logger.warning(f"Failed to check/reset database session: {e}")
        
        logger.info(f"Using cached model: {model_path}")
        return service
    
    # Prevent concurrent loading of the same model
    if cache_key in _cache_lock:
        import time
        # Wait for other thread to finish loading
        while cache_key in _cache_lock:
            time.sleep(0.1)
        # Return the loaded model
        if cache_key in _model_cache:
            service = _model_cache[cache_key]
            service.db = db
            return service
    
    # Mark as loading
    _cache_lock[cache_key] = True
    
    try:
        # 内存管理：如果缓存已满，清理最旧的模型
        if len(_model_cache) >= _max_cached_models:
            logger.info(f"Model cache full ({len(_model_cache)}/{_max_cached_models}), clearing oldest model")
            
            # 找到最旧的模型（简单策略：清理第一个）
            oldest_key = next(iter(_model_cache))
            old_service = _model_cache[oldest_key]
            
            # 清理旧模型的内存
            try:
                if hasattr(old_service, 'model') and old_service.model is not None:
                    del old_service.model
                if hasattr(old_service, 'tokenizer') and old_service.tokenizer is not None:
                    del old_service.tokenizer
                del _model_cache[oldest_key]
                logger.info(f"Cleared cached model: {oldest_key}")
            except Exception as e:
                logger.warning(f"Failed to clear old model: {e}")
            
            # 强制清理GPU内存
            clear_gpu_memory()
        
        logger.info(f"Loading new model into cache: {model_path}")
        # Create and load new service
        service = QueryService(db=db)
        service.load_model(model_path)
        
        # Cache the service
        _model_cache[cache_key] = service
        logger.info(f"Model cached successfully: {model_path} (Cache size: {len(_model_cache)}/{_max_cached_models})")
        
        return service
    
    except Exception as e:
        # 如果加载失败，尝试清理内存后重试
        logger.error(f"Model loading failed: {e}")
        
        # 清理所有缓存的模型
        logger.info("Clearing all cached models due to memory error")
        for cached_key, cached_service in _model_cache.items():
            try:
                if hasattr(cached_service, 'model') and cached_service.model is not None:
                    del cached_service.model
                if hasattr(cached_service, 'tokenizer') and cached_service.tokenizer is not None:
                    del cached_service.tokenizer
            except:
                pass
        
        _model_cache.clear()
        clear_gpu_memory()
        
        # 重新抛出异常
        raise e
    
    finally:
        # Remove loading lock
        if cache_key in _cache_lock:
            del _cache_lock[cache_key]


@router.post("/", response_model=QueryResponse, status_code=status.HTTP_200_OK)
async def query_bank_code(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Query bank code information (all authenticated users)
    查询联行号信息（所有认证用户）
    
    This endpoint:
    1. Accepts a natural language question about bank codes
    2. Uses the specified trained model (or latest if not specified) to generate an answer
    3. Extracts bank code information from the answer
    4. Returns structured response with confidence score
    5. Logs the query to database
    
    Available to all authenticated users.
    
    Performance optimized:
    - Models are cached after first load (no more 20-second delays!)
    - Query results are cached for repeated questions
    - Entity extraction is cached for similar questions
    
    Args:
        request: Query request with question and optional model_id
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Query response with answer and matched records
    
    Raises:
        HTTPException: If query processing fails
    
    Example:
        Request:
        {
            "question": "中国工商银行北京分行的联行号是什么？",
            "model_id": 20,
            "use_rag": true,
            "top_k": 5
        }
        
        Response:
        {
            "question": "中国工商银行北京分行的联行号是什么？",
            "answer": "中国工商银行北京分行的联行号是102100000026",
            "confidence": 0.9,
            "response_time": 234.5,
            "matched_records": [
                {
                    "bank_name": "中国工商银行北京分行",
                    "bank_code": "102100000026",
                    "clearing_code": "102100000000"
                }
            ],
            "timestamp": 1704902400.0
        }
    """
    try:
        logger.info(f"Processing query from user {current_user.username}: {request.question}")
        
        # Determine which model to use
        model_path = None
        if request.model_id:
            # Use specified model
            from app.models.training_job import TrainingJob
            job = db.query(TrainingJob).filter(
                TrainingJob.id == request.model_id,
                TrainingJob.status == "completed",
                TrainingJob.model_path.isnot(None)
            ).first()
            
            if not job:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Training job {request.model_id} not found or not completed"
                )
            
            model_path = job.model_path
            logger.info(f"Using specified model: Job {request.model_id} - {job.model_name}")
        else:
            # Use latest model
            from app.models.training_job import TrainingJob
            latest_job = db.query(TrainingJob).filter(
                TrainingJob.status == "completed",
                TrainingJob.model_path.isnot(None)
            ).order_by(TrainingJob.completed_at.desc()).first()
            
            if not latest_job:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="No trained model available. Please train a model first."
                )
            
            model_path = latest_job.model_path
            logger.info(f"Using latest model: Job {latest_job.id} - {latest_job.model_name}")
        
        # Get cached query service (this is the key optimization!)
        query_service = get_cached_query_service(model_path, db)
        
        # Process query with RAG
        response = query_service.query(
            question=request.question,
            user_id=current_user.id,
            log_query=True,
            use_rag=request.use_rag  # Pass RAG parameter
        )
        
        logger.info(
            f"Query completed - Response time: {response['response_time']:.2f}ms, "
            f"Confidence: {response['confidence']:.2f}, "
            f"Matched records: {len(response['matched_records'])}"
        )
        
        return QueryResponse(**response)
    
    except QueryServiceError as e:
        logger.error(f"Query processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query processing failed: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.post("/batch", response_model=BatchQueryResponse, status_code=status.HTTP_200_OK)
async def batch_query_bank_codes(
    request: BatchQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Batch query bank code information (all authenticated users)
    批量查询联行号信息（所有认证用户）
    
    This endpoint:
    1. Accepts multiple questions in a single request
    2. Processes each question independently using cached models
    3. Returns results for all questions
    4. Logs all queries to database
    
    Available to all authenticated users.
    Performance optimized with model caching.
    
    Args:
        request: Batch query request with list of questions
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Batch query response with results for all questions
    
    Raises:
        HTTPException: If batch processing fails
    
    Example:
        Request:
        {
            "questions": [
                "中国工商银行北京分行的联行号是什么？",
                "工行上海分行的联行号"
            ]
        }
        
        Response:
        {
            "results": [
                {
                    "question": "中国工商银行北京分行的联行号是什么？",
                    "answer": "...",
                    "confidence": 0.9,
                    "response_time": 234.5,
                    "matched_records": [...]
                },
                {
                    "question": "工行上海分行的联行号",
                    "answer": "...",
                    "confidence": 0.85,
                    "response_time": 198.3,
                    "matched_records": [...]
                }
            ],
            "total_queries": 2,
            "successful_queries": 2,
            "failed_queries": 0
        }
    """
    try:
        logger.info(
            f"Processing batch query from user {current_user.username} - "
            f"{len(request.questions)} questions"
        )
        
        # Get latest model for batch processing
        from app.models.training_job import TrainingJob
        latest_job = db.query(TrainingJob).filter(
            TrainingJob.status == "completed",
            TrainingJob.model_path.isnot(None)
        ).order_by(TrainingJob.completed_at.desc()).first()
        
        if not latest_job:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No trained model available. Please train a model first."
            )
        
        # Get cached query service
        query_service = get_cached_query_service(latest_job.model_path, db)
        
        # Process batch query
        responses = query_service.batch_query(
            questions=request.questions,
            user_id=current_user.id,
            log_queries=True
        )
        
        # Count successful and failed queries
        successful = sum(1 for r in responses if "error" not in r)
        failed = len(responses) - successful
        
        logger.info(
            f"Batch query completed - Total: {len(responses)}, "
            f"Successful: {successful}, Failed: {failed}"
        )
        
        return BatchQueryResponse(
            results=[QueryResponse(**r) for r in responses if "error" not in r],
            total_queries=len(responses),
            successful_queries=successful,
            failed_queries=failed
        )
    
    except QueryServiceError as e:
        logger.error(f"Batch query processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch query processing failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during batch query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get("/model-cache-stats", status_code=status.HTTP_200_OK)
async def get_model_cache_stats(
    current_user: User = Depends(get_current_admin_user)
):
    """
    获取模型缓存统计信息（仅管理员）
    
    Returns:
        模型缓存统计信息
    """
    try:
        global _model_cache
        
        cache_info = {}
        for model_path, service in _model_cache.items():
            cache_info[model_path] = {
                "model_version": service.model_version,
                "device": service.device,
                "base_model_name": service.base_model_name,
                "cache_stats": service.get_cache_stats()
            }
        
        return {
            "success": True,
            "cached_models": len(_model_cache),
            "model_cache_details": cache_info
        }
        
    except Exception as e:
        logger.error(f"Failed to get model cache stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve model cache statistics"
        )


@router.post("/clear-model-cache", status_code=status.HTTP_200_OK)
async def clear_model_cache(
    current_user: User = Depends(get_current_admin_user)
):
    """
    清空模型缓存（仅管理员）
    
    Returns:
        操作结果
    """
    try:
        global _model_cache
        
        cache_size = len(_model_cache)
        
        # Clear all cached models properly
        for model_path, service in _model_cache.items():
            try:
                # Clear the service's query cache as well
                service.query_cache.clear()
                service._cache_hits = 0
                service._total_queries = 0
                
                # Clear model and tokenizer from memory
                if hasattr(service, 'model') and service.model is not None:
                    del service.model
                if hasattr(service, 'tokenizer') and service.tokenizer is not None:
                    del service.tokenizer
                    
            except Exception as e:
                logger.warning(f"Failed to clear service {model_path}: {e}")
        
        _model_cache.clear()
        
        # Clear GPU memory
        clear_gpu_memory()
        
        logger.info(f"Admin {current_user.username} cleared model cache ({cache_size} models)")
        
        return {
            "success": True,
            "message": f"Successfully cleared {cache_size} cached models and GPU memory"
        }
        
    except Exception as e:
        logger.error(f"Failed to clear model cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear model cache"
        )


@router.post("/clear-cache", status_code=status.HTTP_200_OK)
async def clear_query_cache(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    清空查询缓存（仅管理员）
    
    Returns:
        操作结果
    """
    try:
        # 清空全局查询服务的缓存
        global _query_service
        if _query_service:
            cache_size = len(_query_service.query_cache)
            _query_service.query_cache.clear()
            _query_service._cache_hits = 0
            _query_service._total_queries = 0
            
            logger.info(f"Admin {current_user.username} cleared query cache ({cache_size} entries)")
            
            return {
                "success": True,
                "message": f"Successfully cleared {cache_size} cache entries"
            }
        else:
            return {
                "success": True,
                "message": "No active query service found"
            }
        
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache"
        )


@router.get("/history", response_model=QueryHistoryResponse, status_code=status.HTTP_200_OK)
async def get_query_history(
    limit: int = QueryParam(100, ge=1, le=1000, description="Maximum number of records to return"),
    offset: int = QueryParam(0, ge=0, description="Number of records to skip"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get query history (all authenticated users)
    获取查询历史（所有认证用户）
    
    This endpoint:
    1. Returns query history for the current user
    2. Supports pagination with limit and offset
    3. Orders results by creation time (newest first)
    
    Available to all authenticated users. Users can only see their own history.
    Note: This endpoint does not require a trained model.
    
    Args:
        limit: Maximum number of records to return (1-1000)
        offset: Number of records to skip
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Query history response with paginated results
    
    Raises:
        HTTPException: If history retrieval fails
    
    Example:
        GET /api/v1/query/history?limit=10&offset=0
        
        Response:
        {
            "items": [
                {
                    "id": 123,
                    "user_id": 1,
                    "question": "中国工商银行北京分行的联行号是什么？",
                    "answer": "...",
                    "confidence": 0.9,
                    "response_time": 234.5,
                    "model_version": "job_1",
                    "created_at": "2026-01-10T12:00:00"
                },
                ...
            ],
            "total": 50,
            "limit": 10,
            "offset": 0
        }
    """
    try:
        logger.info(
            f"Fetching query history for user {current_user.username} - "
            f"Limit: {limit}, Offset: {offset}"
        )
        
        # Import QueryLog model
        from app.models.query_log import QueryLog
        
        # Get total count for current user
        total = db.query(QueryLog).filter(QueryLog.user_id == current_user.id).count()
        
        # Get query history for current user with pagination
        query_logs = db.query(QueryLog).filter(
            QueryLog.user_id == current_user.id
        ).order_by(
            QueryLog.created_at.desc()
        ).limit(limit).offset(offset).all()
        
        # Convert to response format
        history_items = []
        for log in query_logs:
            history_items.append({
                "id": log.id,
                "user_id": log.user_id,
                "question": log.question,
                "answer": log.answer or "",
                "confidence": log.confidence or 0.0,
                "response_time": log.response_time or 0.0,
                "model_version": log.model_version or "",
                "created_at": log.created_at.isoformat() if log.created_at else ""
            })
        
        logger.info(f"Retrieved {len(history_items)} query history records")
        
        return QueryHistoryResponse(
            items=[QueryHistoryItem(**item) for item in history_items],
            total=total,
            limit=limit,
            offset=offset
        )
    
    except Exception as e:
        logger.error(f"Failed to get query history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve query history"
        )
