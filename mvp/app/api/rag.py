"""
RAG API Endpoints - RAG系统管理API端点

本模块提供RAG系统管理相关的API端点。

端点列表：
    - POST /api/v1/rag/initialize: 初始化向量数据库（仅管理员）
    - POST /api/v1/rag/update: 更新向量数据库（仅管理员）
    - GET /api/v1/rag/stats: 获取RAG系统统计信息
    - POST /api/v1/rag/search: 测试RAG检索功能
    - POST /api/v1/rag/rebuild: 重建向量数据库（仅管理员）

权限要求：
    - 管理操作：仅管理员
    - 查看统计和测试检索：所有认证用户

使用示例：
    >>> # 初始化向量数据库
    >>> response = requests.post(
    ...     "http://localhost:8000/api/v1/rag/initialize",
    ...     headers={"Authorization": f"Bearer {admin_token}"}
    ... )
    >>> 
    >>> # 测试检索
    >>> response = requests.post(
    ...     "http://localhost:8000/api/v1/rag/search",
    ...     json={"question": "工商银行北京分行", "top_k": 5},
    ...     headers={"Authorization": f"Bearer {token}"}
    ... )
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from loguru import logger

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_admin_user
from app.models.user import User
from app.core.rag_singleton import get_rag_service


router = APIRouter(prefix="/api/v1/rag", tags=["rag"])


# Request/Response schemas
class RAGConfigRequest(BaseModel):
    """RAG配置更新请求"""
    chunk_size: Optional[int] = Field(None, ge=100, le=2048, description="文档分块大小")
    chunk_overlap: Optional[int] = Field(None, ge=0, le=200, description="分块重叠大小")
    top_k: Optional[int] = Field(None, ge=1, le=50, description="检索结果数量")
    similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="相似度阈值")
    vector_model: Optional[str] = Field(None, description="向量模型名称")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="生成温度")
    max_tokens: Optional[int] = Field(None, ge=50, le=2048, description="最大生成长度")
    context_format: Optional[str] = Field(None, description="上下文格式")
    instruction: Optional[str] = Field(None, min_length=10, description="系统指令")
    vector_weight: Optional[float] = Field(None, ge=0.0, le=1.0, description="向量检索权重")
    keyword_weight: Optional[float] = Field(None, ge=0.0, le=1.0, description="关键词检索权重")
    enable_hybrid: Optional[bool] = Field(None, description="启用混合检索")
    batch_size: Optional[int] = Field(None, ge=10, le=1000, description="批处理大小")
    cache_enabled: Optional[bool] = Field(None, description="启用缓存")
    cache_ttl: Optional[int] = Field(None, ge=60, le=86400, description="缓存过期时间")


class RAGConfigResponse(BaseModel):
    """RAG配置响应"""
    config: Dict[str, Any]
    message: str


class RAGSearchRequest(BaseModel):
    """RAG检索请求"""
    question: str = Field(..., description="用户问题")
    top_k: int = Field(default=5, ge=1, le=20, description="返回结果数量")
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="相似度阈值")


class RAGSearchResponse(BaseModel):
    """RAG检索响应"""
    question: str
    results: List[Dict[str, Any]]
    total_found: int
    search_time_ms: float


class RAGStatsResponse(BaseModel):
    """RAG统计信息响应"""
    vector_db_count: int
    source_db_count: int
    is_synced: bool
    collection_name: str
    embedding_model_dimension: int
    vector_db_path: str


class RAGOperationResponse(BaseModel):
    """RAG操作响应"""
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


@router.get("/config", response_model=RAGConfigResponse)
async def get_rag_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取RAG系统配置参数
    
    所有认证用户都可以查看配置参数。
    
    Args:
        current_user: 当前用户
        db: 数据库会话
    
    Returns:
        RAG系统配置参数
    """
    try:
        rag_service = get_rag_service(db)
        config = rag_service.get_config()
        
        return RAGConfigResponse(
            config=config,
            message="RAG配置获取成功"
        )
        
    except Exception as e:
        logger.error(f"Failed to get RAG config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get RAG config: {str(e)}"
        )


@router.post("/config", response_model=RAGConfigResponse)
async def update_rag_config(
    request: RAGConfigRequest,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    """
    更新RAG系统配置参数
    
    仅管理员可以更新配置参数。
    
    Args:
        request: 配置更新请求
        current_user: 当前用户（必须是管理员）
        db: 数据库会话
    
    Returns:
        更新后的配置参数
    """
    try:
        logger.info(f"Admin {current_user.username} updating RAG config")
        
        rag_service = get_rag_service(db)
        
        # 转换请求为字典，过滤None值
        config_updates = {
            k: v for k, v in request.dict().items() 
            if v is not None
        }
        
        if not config_updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No configuration parameters provided"
            )
        
        # 更新配置
        success = rag_service.update_config(config_updates)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update RAG configuration"
            )
        
        # 获取更新后的配置
        updated_config = rag_service.get_config()
        
        return RAGConfigResponse(
            config=updated_config,
            message=f"RAG配置更新成功，共更新{len(config_updates)}个参数"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update RAG config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update RAG config: {str(e)}"
        )


@router.post("/config/reset", response_model=RAGConfigResponse)
async def reset_rag_config(
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    """
    重置RAG系统配置为默认值
    
    仅管理员可以重置配置。
    
    Args:
        current_user: 当前用户（必须是管理员）
        db: 数据库会话
    
    Returns:
        重置后的配置参数
    """
    try:
        logger.info(f"Admin {current_user.username} resetting RAG config to defaults")
        
        rag_service = get_rag_service(db)
        
        # 获取默认配置
        default_config = rag_service._get_default_config()
        
        # 重置配置
        success = rag_service.update_config(default_config)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reset RAG configuration"
            )
        
        return RAGConfigResponse(
            config=default_config,
            message="RAG配置已重置为默认值"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset RAG config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset RAG config: {str(e)}"
        )


@router.post("/initialize", response_model=RAGOperationResponse)
async def initialize_rag(
    force_rebuild: bool = False,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    初始化RAG向量数据库
    
    仅管理员可以执行此操作。
    
    Args:
        force_rebuild: 是否强制重建数据库
        background_tasks: 后台任务
        current_user: 当前用户（必须是管理员）
        db: 数据库会话
    
    Returns:
        操作结果
    """
    try:
        logger.info(f"Admin {current_user.username} initiated RAG initialization (force_rebuild={force_rebuild})")
        
        rag_service = get_rag_service(db)
        
        # 在后台执行初始化
        async def init_task():
            try:
                success = await rag_service.initialize_vector_db(force_rebuild=force_rebuild)
                if success:
                    logger.info("RAG initialization completed successfully")
                else:
                    logger.error("RAG initialization failed")
            except Exception as e:
                logger.error(f"RAG initialization error: {e}")
        
        background_tasks.add_task(init_task)
        
        return RAGOperationResponse(
            success=True,
            message="RAG initialization started in background",
            details={
                "force_rebuild": force_rebuild,
                "initiated_by": current_user.username
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to start RAG initialization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start RAG initialization: {str(e)}"
        )


@router.post("/update", response_model=RAGOperationResponse)
async def update_rag(
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    更新RAG向量数据库（增量更新）
    
    仅管理员可以执行此操作。
    
    Args:
        background_tasks: 后台任务
        current_user: 当前用户（必须是管理员）
        db: 数据库会话
    
    Returns:
        操作结果
    """
    try:
        logger.info(f"Admin {current_user.username} initiated RAG update")
        
        rag_service = get_rag_service(db)
        
        # 在后台执行更新
        async def update_task():
            try:
                success = await rag_service.update_vector_db()
                if success:
                    logger.info("RAG update completed successfully")
                else:
                    logger.error("RAG update failed")
            except Exception as e:
                logger.error(f"RAG update error: {e}")
        
        background_tasks.add_task(update_task)
        
        return RAGOperationResponse(
            success=True,
            message="RAG update started in background",
            details={
                "initiated_by": current_user.username
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to start RAG update: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start RAG update: {str(e)}"
        )


@router.get("/stats", response_model=RAGStatsResponse)
async def get_rag_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取RAG系统统计信息
    
    所有认证用户都可以查看统计信息。
    
    Args:
        current_user: 当前用户
        db: 数据库会话
    
    Returns:
        RAG系统统计信息
    """
    try:
        rag_service = get_rag_service(db)
        stats = rag_service.get_database_stats()
        
        if "error" in stats:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get RAG stats: {stats['error']}"
            )
        
        return RAGStatsResponse(
            vector_db_count=stats["vector_db_count"],
            source_db_count=stats["source_db_count"],
            is_synced=stats["is_synced"],
            collection_name=stats["collection_name"],
            embedding_model_dimension=stats["embedding_model"],
            vector_db_path=stats["vector_db_path"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get RAG stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get RAG stats: {str(e)}"
        )


@router.post("/search", response_model=RAGSearchResponse)
async def search_rag(
    request: RAGSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    测试RAG检索功能
    
    所有认证用户都可以测试检索功能。
    
    Args:
        request: 检索请求
        current_user: 当前用户
        db: 数据库会话
    
    Returns:
        检索结果
    """
    import time
    
    try:
        start_time = time.time()
        
        rag_service = get_rag_service(db)
        results = await rag_service.retrieve_relevant_banks(
            question=request.question,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold
        )
        
        search_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        logger.info(f"RAG search by user {current_user.username}: '{request.question}' -> {len(results)} results")
        
        return RAGSearchResponse(
            question=request.question,
            results=results,
            total_found=len(results),
            search_time_ms=search_time
        )
        
    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG search failed: {str(e)}"
        )


@router.post("/rebuild", response_model=RAGOperationResponse)
async def rebuild_rag(
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    重建RAG向量数据库（完全重建）
    
    仅管理员可以执行此操作。这会删除现有的向量数据库并重新创建。
    
    Args:
        background_tasks: 后台任务
        current_user: 当前用户（必须是管理员）
        db: 数据库会话
    
    Returns:
        操作结果
    """
    try:
        logger.info(f"Admin {current_user.username} initiated RAG rebuild")
        
        rag_service = get_rag_service(db)
        
        # 在后台执行重建
        async def rebuild_task():
            try:
                success = await rag_service.initialize_vector_db(force_rebuild=True)
                if success:
                    logger.info("RAG rebuild completed successfully")
                else:
                    logger.error("RAG rebuild failed")
            except Exception as e:
                logger.error(f"RAG rebuild error: {e}")
        
        background_tasks.add_task(rebuild_task)
        
        return RAGOperationResponse(
            success=True,
            message="RAG rebuild started in background",
            details={
                "operation": "full_rebuild",
                "initiated_by": current_user.username
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to start RAG rebuild: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start RAG rebuild: {str(e)}"
        )


@router.post("/load-from-file", response_model=RAGOperationResponse)
async def load_from_file(
    file_path: str,
    force_rebuild: bool = False,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    从文件直接加载银行数据到RAG向量数据库
    
    仅管理员可以执行此操作。
    
    Args:
        file_path: 银行数据文件路径
        force_rebuild: 是否强制重建数据库
        background_tasks: 后台任务
        current_user: 当前用户（必须是管理员）
        db: 数据库会话
    
    Returns:
        操作结果
    """
    try:
        logger.info(f"Admin {current_user.username} initiated RAG load from file: {file_path} (force_rebuild={force_rebuild})")
        
        rag_service = get_rag_service(db)
        
        # 在后台执行文件加载
        async def load_task():
            try:
                success = await rag_service.load_from_file(file_path, force_rebuild=force_rebuild)
                if success:
                    logger.info(f"RAG load from file completed successfully: {file_path}")
                else:
                    logger.error(f"RAG load from file failed: {file_path}")
            except Exception as e:
                logger.error(f"RAG load from file error: {e}")
        
        background_tasks.add_task(load_task)
        
        return RAGOperationResponse(
            success=True,
            message=f"RAG load from file started in background: {file_path}",
            details={
                "file_path": file_path,
                "force_rebuild": force_rebuild,
                "initiated_by": current_user.username
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to start RAG load from file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start RAG load from file: {str(e)}"
        )


@router.post("/hybrid-search", response_model=RAGSearchResponse)
async def hybrid_search_rag(
    request: RAGSearchRequest,
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    测试混合检索功能（向量检索 + 关键词检索）
    
    Args:
        request: 检索请求
        vector_weight: 向量检索权重
        keyword_weight: 关键词检索权重
        current_user: 当前用户
        db: 数据库会话
    
    Returns:
        混合检索结果
    """
    import time
    
    try:
        # 确保权重和为1
        total_weight = vector_weight + keyword_weight
        if abs(total_weight - 1.0) > 0.01:
            vector_weight = vector_weight / total_weight
            keyword_weight = keyword_weight / total_weight
        
        start_time = time.time()
        
        rag_service = get_rag_service(db)
        results = await rag_service.hybrid_retrieve(
            question=request.question,
            top_k=request.top_k,
            vector_weight=vector_weight,
            keyword_weight=keyword_weight
        )
        
        search_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        logger.info(f"Hybrid RAG search by user {current_user.username}: '{request.question}' -> {len(results)} results")
        
        return RAGSearchResponse(
            question=request.question,
            results=results,
            total_found=len(results),
            search_time_ms=search_time
        )
        
    except Exception as e:
        logger.error(f"Hybrid RAG search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hybrid RAG search failed: {str(e)}"
        )