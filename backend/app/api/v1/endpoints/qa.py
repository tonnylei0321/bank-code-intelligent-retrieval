"""
问答服务API端点
"""

from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import time
import uuid

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.qa import QAHistory, QASession
from app.models.model import Model
from app.schemas.common import PaginationResponse, PaginationInfo
from app.core.exceptions import NotFoundError, BusinessError

router = APIRouter()


@router.post("/ask", summary="提交问题")
async def ask(
    question_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    提交问题并获取答案
    """
    question = question_data.get("question")
    session_id = question_data.get("session_id") or str(uuid.uuid4())
    model_id = question_data.get("model_id")
    
    if not question:
        raise BusinessError("问题不能为空")
    
    # 获取激活的模型
    if model_id:
        model = db.query(Model).filter(Model.id == model_id).first()
    else:
        model = db.query(Model).filter(Model.is_active == True).first()
    
    if not model:
        raise NotFoundError("没有可用的模型")
    
    # 记录开始时间
    start_time = time.time()
    
    # TODO: 调用模型进行推理
    # 这里暂时返回模拟答案
    answer = f"这是对问题「{question}」的模拟回答。实际推理功能待实现。"
    confidence = 0.95
    
    # 计算响应时间
    response_time = int((time.time() - start_time) * 1000)
    
    # 保存问答历史
    qa_history = QAHistory(
        session_id=session_id,
        user_id=current_user.id,
        question=question,
        answer=answer,
        model_id=model.id,
        confidence=confidence,
        response_time=response_time
    )
    
    db.add(qa_history)
    db.commit()
    db.refresh(qa_history)
    
    return {
        "question": question,
        "answer": answer,
        "confidence": confidence,
        "response_time": response_time,
        "session_id": session_id,
        "model_info": {
            "model_id": model.id,
            "model_name": model.name,
            "version": model.version
        }
    }


@router.get("/history", response_model=PaginationResponse, summary="获取问答历史")
async def get_history(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session_id: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    获取问答历史
    """
    query = db.query(QAHistory).filter(QAHistory.user_id == current_user.id)
    
    if session_id:
        query = query.filter(QAHistory.session_id == session_id)
    
    total = query.count()
    offset = (page - 1) * size
    history = query.order_by(QAHistory.created_at.desc()).offset(offset).limit(size).all()
    
    return {
        "items": history,
        "pagination": PaginationInfo.create(page, size, total)
    }


@router.get("/history/{session_id}", summary="获取会话历史")
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    获取指定会话的历史记录
    """
    history = db.query(QAHistory).filter(
        QAHistory.session_id == session_id,
        QAHistory.user_id == current_user.id
    ).order_by(QAHistory.created_at.asc()).all()
    
    return {
        "session_id": session_id,
        "history": history
    }


@router.delete("/history/{history_id}", summary="删除历史记录")
async def delete_history(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    删除指定的历史记录
    """
    history = db.query(QAHistory).filter(
        QAHistory.id == history_id,
        QAHistory.user_id == current_user.id
    ).first()
    
    if not history:
        raise NotFoundError("历史记录不存在")
    
    db.delete(history)
    db.commit()
    
    return {"message": "历史记录删除成功"}