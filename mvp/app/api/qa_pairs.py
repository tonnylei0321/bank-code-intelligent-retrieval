"""
QA Pairs API Endpoints - 问答对生成和管理API端点

本模块提供问答对生成和管理相关的API端点。

端点列表：
    - POST /api/v1/qa-pairs/generate: 生成问答对（仅管理员）
    - GET /api/v1/qa-pairs/{dataset_id}/stats: 获取问答对统计信息
    - GET /api/v1/qa-pairs/{dataset_id}: 获取问答对列表（支持筛选和分页）
    - DELETE /api/v1/qa-pairs/{dataset_id}: 删除数据集的所有问答对（仅管理员）
    - GET /api/v1/qa-pairs/{dataset_id}/export: 导出问答对（仅管理员）

生成流程：
    1. 管理员选择数据集并配置生成参数
    2. 系统遍历数据集中的所有银行代码记录
    3. 使用大模型API为每条记录生成4种类型的问题
    4. 自动划分为训练集/验证集/测试集
    5. 保存到数据库
    6. 返回生成统计信息

问题类型：
    - exact: 精确匹配问题（如：工商银行的联行号是什么？）
    - fuzzy: 模糊匹配问题（如：工行的代码是多少？）
    - reverse: 反向查询问题（如：102100099996是哪个银行？）
    - natural: 自然语言问题（如：我想查询工商银行的联行号）

权限要求：
    - 生成问答对：仅管理员
    - 删除问答对：仅管理员
    - 导出问答对：仅管理员
    - 查看问答对：所有认证用户

使用示例：
    >>> # 生成问答对
    >>> response = requests.post(
    ...     "http://localhost:8000/api/v1/qa-pairs/generate",
    ...     json={
    ...         "dataset_id": 1,
    ...         "question_types": ["exact", "fuzzy", "reverse", "natural"],
    ...         "train_ratio": 0.8,
    ...         "val_ratio": 0.1,
    ...         "test_ratio": 0.1
    ...     },
    ...     headers={"Authorization": f"Bearer {admin_token}"}
    ... )
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.deps import get_current_user, get_current_admin_user, get_db
from app.core.permissions import require_admin
from app.models.user import User
from app.models.qa_pair import QAPair
from app.schemas.qa_pair import (
    QAPairResponse,
    GenerationRequest,
    GenerationResult,
    QAPairStats
)
from app.services.qa_generator import QAGenerator, QAGenerationError
from app.core.logging import logger

router = APIRouter(prefix="/api/v1/qa-pairs", tags=["qa-pairs"])


@router.post("/generate", response_model=GenerationResult, status_code=status.HTTP_201_CREATED)
@require_admin
async def generate_qa_pairs(
    request: GenerationRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Generate QA pairs for a dataset (admin only)
    为数据集生成问答对（仅管理员）
    
    This endpoint:
    1. Generates QA pairs for all valid bank code records in the dataset
    2. Automatically splits the generated pairs into train/val/test sets
    3. Returns generation statistics
    
    Requires admin role.
    
    Args:
        request: Generation request with dataset_id, question_types, and split ratios
        current_user: Current admin user
        db: Database session
    
    Returns:
        Generation result with statistics
    
    Raises:
        HTTPException: If dataset not found, validation fails, or generation fails
    """
    try:
        # Validate split ratios
        total_ratio = request.train_ratio + request.val_ratio + request.test_ratio
        if abs(total_ratio - 1.0) > 0.001:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Split ratios must sum to 1.0, got {total_ratio}"
            )
        
        # Create QA generator
        generator = QAGenerator(db=db)
        
        logger.info(
            f"Starting QA pair generation for dataset {request.dataset_id} "
            f"by user {current_user.username}"
        )
        
        # Generate QA pairs
        gen_results = generator.generate_for_dataset(
            dataset_id=request.dataset_id,
            question_types=request.question_types
        )
        
        # Split dataset
        split_results = generator.split_dataset(
            dataset_id=request.dataset_id,
            train_ratio=request.train_ratio,
            val_ratio=request.val_ratio,
            test_ratio=request.test_ratio,
            random_seed=42  # Fixed seed for reproducibility
        )
        
        # Get statistics
        stats = generator.get_generation_stats(dataset_id=request.dataset_id)
        
        logger.info(
            f"QA pair generation completed for dataset {request.dataset_id} - "
            f"Total: {stats['total_qa_pairs']}, "
            f"Train: {split_results['train_count']}, "
            f"Val: {split_results['val_count']}, "
            f"Test: {split_results['test_count']}"
        )
        
        # Prepare error messages
        errors = []
        if gen_results['failed'] > 0:
            errors.append(
                f"{gen_results['failed']} QA pairs failed to generate. "
                f"Check logs for details."
            )
            for failed_record in gen_results['failed_records'][:5]:  # Show first 5
                errors.append(
                    f"Record {failed_record['record_id']} ({failed_record['bank_name']}): "
                    f"{len(failed_record['failures'])} failures"
                )
        
        return GenerationResult(
            dataset_id=request.dataset_id,
            total_generated=stats['total_qa_pairs'],
            train_count=split_results['train_count'],
            val_count=split_results['val_count'],
            test_count=split_results['test_count'],
            question_type_counts=stats['by_question_type'],
            errors=errors
        )
    
    except QAGenerationError as e:
        logger.error(f"QA generation error for dataset {request.dataset_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.exception(f"Unexpected error generating QA pairs for dataset {request.dataset_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate QA pairs"
        )


@router.get("/{dataset_id}/stats", response_model=QAPairStats)
async def get_qa_pair_stats(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get QA pair statistics for a dataset
    获取数据集的问答对统计信息
    
    Args:
        dataset_id: Dataset ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        QA pair statistics including counts by type and split
    """
    try:
        generator = QAGenerator(db=db)
        stats = generator.get_generation_stats(dataset_id=dataset_id)
        
        return QAPairStats(
            dataset_id=dataset_id,
            total_pairs=stats['total_qa_pairs'],
            train_pairs=stats['by_split_type'].get('train', 0),
            val_pairs=stats['by_split_type'].get('val', 0),
            test_pairs=stats['by_split_type'].get('test', 0),
            exact_pairs=stats['by_question_type'].get('exact', 0),
            fuzzy_pairs=stats['by_question_type'].get('fuzzy', 0),
            reverse_pairs=stats['by_question_type'].get('reverse', 0),
            natural_pairs=stats['by_question_type'].get('natural', 0)
        )
    except Exception as e:
        logger.error(f"Error getting QA pair stats for dataset {dataset_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get QA pair statistics"
        )


@router.get("/{dataset_id}", response_model=List[QAPairResponse])
async def get_qa_pairs(
    dataset_id: int,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    question_type: Optional[str] = Query(None, description="Filter by question type"),
    split_type: Optional[str] = Query(None, description="Filter by split type"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get QA pairs for a dataset with pagination and filtering
    获取数据集的问答对（支持分页和筛选）
    
    Args:
        dataset_id: Dataset ID
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return (max 1000)
        question_type: Optional filter by question type (exact, fuzzy, reverse, natural)
        split_type: Optional filter by split type (train, val, test)
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List of QA pairs
    """
    try:
        # Build query
        query = db.query(QAPair).filter(QAPair.dataset_id == dataset_id)
        
        # Apply filters
        if question_type:
            if question_type not in ['exact', 'fuzzy', 'reverse', 'natural']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid question_type: {question_type}"
                )
            query = query.filter(QAPair.question_type == question_type)
        
        if split_type:
            if split_type not in ['train', 'val', 'test']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid split_type: {split_type}"
                )
            query = query.filter(QAPair.split_type == split_type)
        
        # Apply pagination
        qa_pairs = query.order_by(QAPair.id).offset(skip).limit(limit).all()
        
        return qa_pairs
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting QA pairs for dataset {dataset_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get QA pairs"
        )


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_admin
async def delete_qa_pairs(
    dataset_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Delete all QA pairs for a dataset (admin only)
    删除数据集的所有问答对（仅管理员）
    
    This is useful for regenerating QA pairs with different parameters.
    
    Requires admin role.
    
    Args:
        dataset_id: Dataset ID
        current_user: Current admin user
        db: Database session
    
    Returns:
        No content (204)
    """
    try:
        # Count QA pairs before deletion
        count = db.query(QAPair).filter(QAPair.dataset_id == dataset_id).count()
        
        if count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No QA pairs found for dataset {dataset_id}"
            )
        
        # Delete all QA pairs for this dataset
        db.query(QAPair).filter(QAPair.dataset_id == dataset_id).delete()
        db.commit()
        
        logger.info(
            f"Deleted {count} QA pairs for dataset {dataset_id} "
            f"by user {current_user.username}"
        )
        
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting QA pairs for dataset {dataset_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete QA pairs"
        )


@router.get("/{dataset_id}/export", response_model=List[QAPairResponse])
@require_admin
async def export_qa_pairs(
    dataset_id: int,
    split_type: Optional[str] = Query(None, description="Export specific split (train, val, test)"),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Export all QA pairs for a dataset (admin only)
    导出数据集的所有问答对（仅管理员）
    
    This endpoint returns all QA pairs without pagination, useful for exporting
    training data to external systems.
    
    Requires admin role.
    
    Args:
        dataset_id: Dataset ID
        split_type: Optional filter by split type (train, val, test)
        current_user: Current admin user
        db: Database session
    
    Returns:
        List of all QA pairs
    """
    try:
        # Build query
        query = db.query(QAPair).filter(QAPair.dataset_id == dataset_id)
        
        # Apply split filter if provided
        if split_type:
            if split_type not in ['train', 'val', 'test']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid split_type: {split_type}"
                )
            query = query.filter(QAPair.split_type == split_type)
        
        # Get all QA pairs
        qa_pairs = query.order_by(QAPair.id).all()
        
        logger.info(
            f"Exported {len(qa_pairs)} QA pairs for dataset {dataset_id} "
            f"(split: {split_type or 'all'}) by user {current_user.username}"
        )
        
        return qa_pairs
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting QA pairs for dataset {dataset_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export QA pairs"
        )
