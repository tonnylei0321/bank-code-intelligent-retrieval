"""
Sample Sets API - 样本集管理API

提供样本集的CRUD操作和样本管理功能。

端点列表：
    - GET /api/v1/sample-sets: 获取所有样本集
    - GET /api/v1/sample-sets/dataset/{dataset_id}: 获取指定数据集的样本集列表
    - GET /api/v1/sample-sets/{sample_set_id}: 获取样本集详情
    - POST /api/v1/sample-sets: 创建样本集
    - PUT /api/v1/sample-sets/{sample_set_id}: 更新样本集
    - DELETE /api/v1/sample-sets/{sample_set_id}: 删除样本集
    - DELETE /api/v1/sample-sets/batch: 批量删除样本集
    - GET /api/v1/sample-sets/{sample_set_id}/samples: 获取样本集的样本列表
    - GET /api/v1/sample-sets/{sample_set_id}/stats: 获取样本集统计信息
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.deps import get_current_user, get_current_admin_user, get_db
from app.models.user import User
from app.models.sample_set import SampleSet
from app.models.qa_pair import QAPair
from app.models.dataset import Dataset
from app.core.logging import logger

router = APIRouter(prefix="/api/v1/sample-sets", tags=["sample-sets"])


@router.get("/dataset/{dataset_id}")
async def get_sample_sets_by_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取指定数据集的所有样本集
    
    Args:
        dataset_id: 数据集ID
        current_user: 当前用户
        db: 数据库会话
    
    Returns:
        样本集列表
    """
    try:
        # 检查数据集是否存在
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"数据集 {dataset_id} 不存在"
            )
        
        # 获取样本集列表
        sample_sets = db.query(SampleSet)\
            .filter(SampleSet.dataset_id == dataset_id)\
            .order_by(SampleSet.created_at.desc())\
            .all()
        
        return [sample_set.to_dict() for sample_set in sample_sets]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取数据集 {dataset_id} 的样本集失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取样本集列表失败"
        )


@router.get("/{sample_set_id}")
async def get_sample_set(
    sample_set_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取样本集详情
    
    Args:
        sample_set_id: 样本集ID
        current_user: 当前用户
        db: 数据库会话
    
    Returns:
        样本集详情
    """
    try:
        sample_set = db.query(SampleSet).filter(SampleSet.id == sample_set_id).first()
        if not sample_set:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"样本集 {sample_set_id} 不存在"
            )
        
        return sample_set.to_dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取样本集 {sample_set_id} 失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取样本集详情失败"
        )


@router.post("")
async def create_sample_set(
    request: dict,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    创建样本集
    
    Args:
        request: 创建请求
        current_user: 当前管理员用户
        db: 数据库会话
    
    Returns:
        创建的样本集
    """
    try:
        # 检查数据集是否存在
        dataset_id = request.get("dataset_id")
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"数据集 {dataset_id} 不存在"
            )
        
        # 创建样本集
        sample_set = SampleSet(
            name=request.get("name"),
            dataset_id=dataset_id,
            generation_task_id=request.get("generation_task_id"),
            description=request.get("description"),
            generation_config=request.get("generation_config"),
            status=request.get("status", "generating"),
            created_by=current_user.id
        )
        
        db.add(sample_set)
        db.commit()
        db.refresh(sample_set)
        
        logger.info(f"用户 {current_user.username} 创建了样本集 {sample_set.id}")
        
        return sample_set.to_dict()
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"创建样本集失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建样本集失败"
        )


@router.put("/{sample_set_id}")
async def update_sample_set(
    sample_set_id: int,
    request: dict,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    更新样本集
    
    Args:
        sample_set_id: 样本集ID
        request: 更新请求
        current_user: 当前管理员用户
        db: 数据库会话
    
    Returns:
        更新后的样本集
    """
    try:
        sample_set = db.query(SampleSet).filter(SampleSet.id == sample_set_id).first()
        if not sample_set:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"样本集 {sample_set_id} 不存在"
            )
        
        # 更新字段
        if "name" in request:
            sample_set.name = request["name"]
        if "description" in request:
            sample_set.description = request["description"]
        if "status" in request:
            sample_set.status = request["status"]
            if request["status"] == "completed":
                sample_set.completed_at = datetime.utcnow()
        
        # 更新统计信息
        if "total_samples" in request:
            sample_set.total_samples = request["total_samples"]
        if "train_samples" in request:
            sample_set.train_samples = request["train_samples"]
        if "val_samples" in request:
            sample_set.val_samples = request["val_samples"]
        if "test_samples" in request:
            sample_set.test_samples = request["test_samples"]
        
        db.commit()
        db.refresh(sample_set)
        
        logger.info(f"用户 {current_user.username} 更新了样本集 {sample_set_id}")
        
        return sample_set.to_dict()
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新样本集 {sample_set_id} 失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新样本集失败"
        )


@router.delete("/{sample_set_id}")
async def delete_sample_set(
    sample_set_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    删除样本集（包括其所有样本）
    
    Args:
        sample_set_id: 样本集ID
        current_user: 当前管理员用户
        db: 数据库会话
    
    Returns:
        删除结果
    """
    try:
        sample_set = db.query(SampleSet).filter(SampleSet.id == sample_set_id).first()
        if not sample_set:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"样本集 {sample_set_id} 不存在"
            )
        
        # 获取样本数量
        sample_count = db.query(QAPair).filter(QAPair.sample_set_id == sample_set_id).count()
        
        # 删除样本集（级联删除所有样本）
        db.delete(sample_set)
        db.commit()
        
        logger.info(f"用户 {current_user.username} 删除了样本集 {sample_set_id}（包含 {sample_count} 个样本）")
        
        return {
            "message": "样本集删除成功",
            "deleted_samples": sample_count
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除样本集 {sample_set_id} 失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除样本集失败"
        )


@router.post("/batch-delete")
async def batch_delete_sample_sets(
    request: dict,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    批量删除样本集
    
    Args:
        request: 包含sample_set_ids的请求
        current_user: 当前管理员用户
        db: 数据库会话
    
    Returns:
        删除结果
    """
    try:
        sample_set_ids = request.get("sample_set_ids", [])
        if not sample_set_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请提供要删除的样本集ID列表"
            )
        
        # 统计删除的样本数
        total_samples = 0
        deleted_count = 0
        
        for sample_set_id in sample_set_ids:
            sample_set = db.query(SampleSet).filter(SampleSet.id == sample_set_id).first()
            if sample_set:
                sample_count = db.query(QAPair).filter(QAPair.sample_set_id == sample_set_id).count()
                total_samples += sample_count
                db.delete(sample_set)
                deleted_count += 1
        
        db.commit()
        
        logger.info(f"用户 {current_user.username} 批量删除了 {deleted_count} 个样本集（包含 {total_samples} 个样本）")
        
        return {
            "message": f"成功删除 {deleted_count} 个样本集",
            "deleted_sample_sets": deleted_count,
            "deleted_samples": total_samples
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"批量删除样本集失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="批量删除样本集失败"
        )


@router.get("/{sample_set_id}/samples")
async def get_sample_set_samples(
    sample_set_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    question_type: Optional[str] = Query(None),
    split_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取样本集的样本列表
    
    Args:
        sample_set_id: 样本集ID
        skip: 跳过的记录数
        limit: 返回的最大记录数
        question_type: 问题类型过滤
        split_type: 数据集划分类型过滤
        current_user: 当前用户
        db: 数据库会话
    
    Returns:
        样本列表
    """
    try:
        # 检查样本集是否存在
        sample_set = db.query(SampleSet).filter(SampleSet.id == sample_set_id).first()
        if not sample_set:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"样本集 {sample_set_id} 不存在"
            )
        
        # 构建查询
        query = db.query(QAPair).filter(QAPair.sample_set_id == sample_set_id)
        
        # 应用过滤
        if question_type:
            query = query.filter(QAPair.question_type == question_type)
        if split_type:
            query = query.filter(QAPair.split_type == split_type)
        
        # 获取总数
        total = query.count()
        
        # 分页
        samples = query.order_by(QAPair.id).offset(skip).limit(limit).all()
        
        return {
            "total": total,
            "samples": [sample.to_dict() for sample in samples]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取样本集 {sample_set_id} 的样本失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取样本列表失败"
        )


@router.get("/{sample_set_id}/stats")
async def get_sample_set_stats(
    sample_set_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取样本集统计信息
    
    Args:
        sample_set_id: 样本集ID
        current_user: 当前用户
        db: 数据库会话
    
    Returns:
        统计信息
    """
    try:
        sample_set = db.query(SampleSet).filter(SampleSet.id == sample_set_id).first()
        if not sample_set:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"样本集 {sample_set_id} 不存在"
            )
        
        # 统计各类型样本数
        stats = {
            "sample_set_id": sample_set_id,
            "total_samples": sample_set.total_samples,
            "train_samples": sample_set.train_samples,
            "val_samples": sample_set.val_samples,
            "test_samples": sample_set.test_samples,
            "by_question_type": {},
            "by_split_type": {}
        }
        
        # 按问题类型统计
        for q_type in ['exact', 'fuzzy', 'reverse', 'natural']:
            count = db.query(QAPair)\
                .filter(QAPair.sample_set_id == sample_set_id)\
                .filter(QAPair.question_type == q_type)\
                .count()
            stats["by_question_type"][q_type] = count
        
        # 按数据集划分统计
        for s_type in ['train', 'val', 'test']:
            count = db.query(QAPair)\
                .filter(QAPair.sample_set_id == sample_set_id)\
                .filter(QAPair.split_type == s_type)\
                .count()
            stats["by_split_type"][s_type] = count
        
        return stats
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取样本集 {sample_set_id} 统计信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取统计信息失败"
        )
