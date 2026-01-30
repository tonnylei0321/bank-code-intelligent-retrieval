"""
训练管理API端点
"""

from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_admin_user
from app.models.user import User
from app.models.training import TrainingTask, TrainingStatus
from app.schemas.common import PaginationResponse, PaginationInfo
from app.core.exceptions import NotFoundError

router = APIRouter()


@router.post("/tasks", summary="创建训练任务")
async def create_task(
    task_data: dict,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    创建训练任务（仅管理员）
    """
    # TODO: 实现训练任务创建逻辑
    return {"message": "训练任务创建功能待实现"}


@router.get("/tasks", response_model=PaginationResponse, summary="获取训练任务列表")
async def get_tasks(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    获取训练任务列表
    """
    query = db.query(TrainingTask)
    
    if status:
        query = query.filter(TrainingTask.status == status)
    
    total = query.count()
    offset = (page - 1) * size
    tasks = query.order_by(TrainingTask.created_at.desc()).offset(offset).limit(size).all()
    
    return {
        "items": tasks,
        "pagination": PaginationInfo.create(page, size, total)
    }


@router.get("/tasks/{task_id}", summary="获取训练任务详情")
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    获取训练任务详情
    """
    task = db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
    if not task:
        raise NotFoundError("训练任务不存在")
    
    return task


@router.post("/tasks/{task_id}/start", summary="启动训练任务")
async def start_task(
    task_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    启动训练任务（仅管理员）
    """
    # TODO: 实现训练任务启动逻辑
    return {"message": "训练任务启动功能待实现"}


@router.post("/tasks/{task_id}/stop", summary="停止训练任务")
async def stop_task(
    task_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    停止训练任务（仅管理员）
    """
    # TODO: 实现训练任务停止逻辑
    return {"message": "训练任务停止功能待实现"}


@router.get("/tasks/{task_id}/progress", summary="获取训练进度")
async def get_progress(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    获取训练任务进度
    """
    task = db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
    if not task:
        raise NotFoundError("训练任务不存在")
    
    return {
        "task_id": task.id,
        "status": task.status,
        "progress": task.progress,
        "started_at": task.started_at,
        "completed_at": task.completed_at
    }