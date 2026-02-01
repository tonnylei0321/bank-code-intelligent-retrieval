"""
智能问答API

提供基于小模型和Redis的智能问答接口：
1. 智能问答处理
2. 模型选择和管理
3. 问答历史查询
4. 统计信息获取
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.core.deps import get_db, get_current_user
from app.core.permissions import require_admin_user, check_permission, require_permission
from app.services.redis_service import RedisService
from app.services.small_model_service import SmallModelService, ModelType
from app.services.intelligent_qa_service import IntelligentQAService, RetrievalStrategy
from app.services.rag_service import RAGService
from app.models.user import User
from loguru import logger

router = APIRouter()


class QuestionRequest(BaseModel):
    """问题请求模型"""
    question: str
    model_type: Optional[str] = None
    retrieval_strategy: Optional[str] = None


class ModelConfigRequest(BaseModel):
    """模型配置请求模型"""
    model_type: str
    config: Dict[str, Any] = {}


def get_intelligent_qa_service(db: Session = Depends(get_db)) -> IntelligentQAService:
    """获取智能问答服务实例"""
    from app.core.config import settings
    
    # 初始化Redis服务
    redis_service = RedisService(db)
    
    # 初始化小模型服务，传入API密钥
    model_service = SmallModelService(
        openai_api_key=getattr(settings, 'OPENAI_API_KEY', None),
        anthropic_api_key=getattr(settings, 'ANTHROPIC_API_KEY', None)
    )
    
    # 初始化RAG服务（可选）
    try:
        rag_service = RAGService(db)
    except Exception as e:
        logger.warning(f"RAG service initialization failed: {e}")
        rag_service = None
    
    # 创建智能问答服务
    qa_service = IntelligentQAService(
        db=db,
        redis_service=redis_service,
        model_service=model_service,
        rag_service=rag_service
    )
    
    return qa_service


@router.post("/ask")
async def ask_question(
    request: QuestionRequest,
    qa_service: IntelligentQAService = Depends(get_intelligent_qa_service),
    current_user: User = Depends(get_current_user)
):
    """
    智能问答接口
    
    Args:
        request: 问题请求
        qa_service: 智能问答服务
        current_user: 当前用户
    
    Returns:
        问答结果
    """
    try:
        # 检查权限
        require_permission(current_user, "user")
        
        # 初始化服务
        if not await qa_service.initialize():
            raise HTTPException(status_code=500, detail="智能问答服务初始化失败")
        
        # 解析参数
        model_type = None
        if request.model_type:
            try:
                model_type = ModelType(request.model_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"不支持的模型类型: {request.model_type}")
        
        retrieval_strategy = None
        if request.retrieval_strategy:
            try:
                retrieval_strategy = RetrievalStrategy(request.retrieval_strategy)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"不支持的检索策略: {request.retrieval_strategy}")
        
        # 处理问题
        result = await qa_service.ask_question(
            question=request.question,
            user_id=current_user.id,
            retrieval_strategy=retrieval_strategy,
            model_type=model_type
        )
        
        logger.info(f"User {current_user.username} asked question: {request.question[:50]}...")
        
        return {
            "success": True,
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process question: {e}")
        raise HTTPException(status_code=500, detail=f"问题处理失败: {str(e)}")


@router.get("/models")
async def get_available_models(
    qa_service: IntelligentQAService = Depends(get_intelligent_qa_service),
    current_user: User = Depends(get_current_user)
):
    """
    获取可用的模型列表
    
    Args:
        qa_service: 智能问答服务
        current_user: 当前用户
    
    Returns:
        可用模型列表
    """
    try:
        # 检查权限
        require_permission(current_user, "user")
        
        # 获取可用模型
        models = qa_service.model_service.get_available_models()
        
        # 获取当前模型
        current_model = qa_service.model_service.current_model.value
        
        return {
            "success": True,
            "data": {
                "available_models": models,
                "current_model": current_model,
                "total_count": len(models)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get available models: {e}")
        raise HTTPException(status_code=500, detail=f"获取模型列表失败: {str(e)}")


@router.post("/models/set")
async def set_current_model(
    request: ModelConfigRequest,
    qa_service: IntelligentQAService = Depends(get_intelligent_qa_service),
    current_user: User = Depends(get_current_user)
):
    """
    设置当前使用的模型
    
    Args:
        request: 模型配置请求
        qa_service: 智能问答服务
        current_user: 当前用户
    
    Returns:
        设置结果
    """
    try:
        # 检查权限
        require_permission(current_user, "admin")
        
        # 解析模型类型
        try:
            model_type = ModelType(request.model_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"不支持的模型类型: {request.model_type}")
        
        # 设置模型
        success = qa_service.model_service.set_model(model_type)
        
        if not success:
            raise HTTPException(status_code=500, detail="设置模型失败")
        
        logger.info(f"User {current_user.username} set model to: {request.model_type}")
        
        return {
            "success": True,
            "message": f"模型已设置为: {request.model_type}",
            "current_model": model_type.value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set model: {e}")
        raise HTTPException(status_code=500, detail=f"设置模型失败: {str(e)}")


@router.get("/history")
async def get_user_qa_history(
    limit: int = Query(20, ge=1, le=100, description="返回记录数量限制"),
    question_type: Optional[str] = Query(None, description="问题类型过滤"),
    qa_service: IntelligentQAService = Depends(get_intelligent_qa_service),
    current_user: User = Depends(get_current_user)
):
    """
    获取用户问答历史
    
    Args:
        limit: 返回记录数量限制
        question_type: 问题类型过滤
        qa_service: 智能问答服务
        current_user: 当前用户
    
    Returns:
        问答历史记录
    """
    try:
        # 检查权限
        require_permission(current_user, "user")
        
        # 获取历史记录
        history = await qa_service.get_user_history(
            user_id=current_user.id,
            limit=limit,
            question_type=question_type
        )
        
        return {
            "success": True,
            "data": {
                "history": history,
                "count": len(history),
                "user_id": current_user.id
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get user QA history: {e}")
        raise HTTPException(status_code=500, detail=f"获取历史记录失败: {str(e)}")


@router.get("/popular-questions")
async def get_popular_questions(
    limit: int = Query(10, ge=1, le=50, description="返回记录数量限制"),
    qa_service: IntelligentQAService = Depends(get_intelligent_qa_service),
    current_user: User = Depends(get_current_user)
):
    """
    获取热门问题
    
    Args:
        limit: 返回记录数量限制
        qa_service: 智能问答服务
        current_user: 当前用户
    
    Returns:
        热门问题列表
    """
    try:
        # 检查权限
        require_permission(current_user, "user")
        
        # 获取热门问题
        popular_questions = await qa_service.get_popular_questions(limit=limit)
        
        return {
            "success": True,
            "data": {
                "popular_questions": popular_questions,
                "count": len(popular_questions)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get popular questions: {e}")
        raise HTTPException(status_code=500, detail=f"获取热门问题失败: {str(e)}")


@router.get("/stats")
async def get_qa_stats(
    qa_service: IntelligentQAService = Depends(get_intelligent_qa_service),
    current_user: User = Depends(get_current_user)
):
    """
    获取问答服务统计信息
    
    Args:
        qa_service: 智能问答服务
        current_user: 当前用户
    
    Returns:
        统计信息
    """
    try:
        # 检查权限
        require_permission(current_user, "user")
        
        # 获取统计信息
        stats = qa_service.get_stats()
        
        return {
            "success": True,
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get QA stats: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/retrieval-strategies")
async def get_retrieval_strategies(
    current_user: User = Depends(get_current_user)
):
    """
    获取可用的检索策略
    
    Args:
        current_user: 当前用户
    
    Returns:
        检索策略列表
    """
    try:
        # 检查权限
        require_permission(current_user, "user")
        
        strategies = [
            {
                "value": RetrievalStrategy.REDIS_ONLY.value,
                "name": "仅Redis检索",
                "description": "使用Redis缓存进行快速精确匹配"
            },
            {
                "value": RetrievalStrategy.RAG_ONLY.value,
                "name": "仅RAG检索",
                "description": "使用向量数据库进行语义相似度检索"
            },
            {
                "value": RetrievalStrategy.HYBRID.value,
                "name": "混合检索",
                "description": "结合Redis和RAG的优势进行检索"
            },
            {
                "value": RetrievalStrategy.INTELLIGENT.value,
                "name": "智能检索",
                "description": "根据问题类型自动选择最佳检索策略"
            }
        ]
        
        return {
            "success": True,
            "data": {
                "strategies": strategies,
                "default": RetrievalStrategy.INTELLIGENT.value
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get retrieval strategies: {e}")
        raise HTTPException(status_code=500, detail=f"获取检索策略失败: {str(e)}")


@router.post("/analyze")
async def analyze_question(
    question: str = Body(..., embed=True),
    qa_service: IntelligentQAService = Depends(get_intelligent_qa_service),
    current_user: User = Depends(get_current_user)
):
    """
    分析问题（不生成答案）
    
    Args:
        question: 用户问题
        qa_service: 智能问答服务
        current_user: 当前用户
    
    Returns:
        问题分析结果
    """
    try:
        # 检查权限
        require_permission(current_user, "user")
        
        # 分析问题
        analysis = await qa_service.model_service.analyze_question(question)
        
        return {
            "success": True,
            "data": analysis
        }
        
    except Exception as e:
        logger.error(f"Failed to analyze question: {e}")
        raise HTTPException(status_code=500, detail=f"问题分析失败: {str(e)}")


@router.get("/health")
async def check_qa_service_health(
    qa_service: IntelligentQAService = Depends(get_intelligent_qa_service),
    current_user: User = Depends(get_current_user)
):
    """
    检查智能问答服务健康状态
    
    Args:
        qa_service: 智能问答服务
        current_user: 当前用户
    
    Returns:
        健康状态信息
    """
    try:
        # 检查权限
        require_permission(current_user, "user")
        
        # 检查服务状态
        health_status = {
            "qa_service": "unknown",
            "redis_service": "unknown",
            "model_service": "unknown",
            "rag_service": "unknown"
        }
        
        # 检查QA服务
        try:
            qa_initialized = await qa_service.initialize()
            health_status["qa_service"] = "healthy" if qa_initialized else "unhealthy"
        except Exception as e:
            health_status["qa_service"] = f"error: {str(e)}"
        
        # 检查Redis服务
        try:
            await qa_service.redis_service.initialize()
            await qa_service.redis_service.redis_client.ping()
            health_status["redis_service"] = "healthy"
        except Exception as e:
            health_status["redis_service"] = f"error: {str(e)}"
        
        # 检查模型服务
        try:
            available_models = qa_service.model_service.get_available_models()
            health_status["model_service"] = "healthy" if available_models else "no_models"
        except Exception as e:
            health_status["model_service"] = f"error: {str(e)}"
        
        # 检查RAG服务
        if qa_service.rag_service:
            try:
                rag_stats = qa_service.rag_service.get_database_stats()
                health_status["rag_service"] = "healthy" if "error" not in rag_stats else "error"
            except Exception as e:
                health_status["rag_service"] = f"error: {str(e)}"
        else:
            health_status["rag_service"] = "not_configured"
        
        # 判断整体健康状态
        overall_healthy = all(
            status == "healthy" or status == "not_configured" 
            for status in health_status.values()
        )
        
        return {
            "success": True,
            "status": "healthy" if overall_healthy else "unhealthy",
            "services": health_status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to check QA service health: {e}")
        return {
            "success": False,
            "status": "error",
            "message": f"健康检查失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }