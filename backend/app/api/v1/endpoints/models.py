"""
模型管理API端点
"""

from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_admin_user
from app.models.user import User
from app.models.model import Model
from app.schemas.common import PaginationResponse, PaginationInfo
from app.core.exceptions import NotFoundError

router = APIRouter()


@router.get("", response_model=PaginationResponse, summary="获取模型列表")
async def get_models(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    model_type: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    获取模型列表
    """
    query = db.query(Model)
    
    if model_type:
        query = query.filter(Model.model_type == model_type)
    
    total = query.count()
    offset = (page - 1) * size
    models = query.order_by(Model.created_at.desc()).offset(offset).limit(size).all()
    
    return {
        "items": models,
        "pagination": PaginationInfo.create(page, size, total)
    }


@router.get("/{model_id}", summary="获取模型详情")
async def get_model(
    model_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    获取模型详情
    """
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise NotFoundError("模型不存在")
    
    return model


@router.post("/{model_id}/test", summary="测试模型")
async def test_model(
    model_id: int,
    test_data: dict,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    测试模型（仅管理员）
    """
    # TODO: 实现模型测试逻辑
    return {"message": "模型测试功能待实现"}


@router.post("/{model_id}/deploy", summary="部署模型")
async def deploy_model(
    model_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    部署模型（仅管理员）
    """
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise NotFoundError("模型不存在")
    
    # 将其他模型设为非激活状态
    db.query(Model).filter(
        Model.model_type == model.model_type,
        Model.is_active == True
    ).update({"is_active": False})
    
    # 激活当前模型
    model.is_active = True
    db.commit()
    
    return {"message": "模型部署成功", "model_id": model.id}