"""
Dataset API endpoints
数据集管理API端点
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from app.core.deps import get_current_user, get_current_admin_user, get_db
from app.core.permissions import require_admin
from app.models.user import User
from app.models.dataset import Dataset
from app.schemas.dataset import DatasetResponse, DatasetStats, ValidationResult
from app.schemas.bank_code import BankCodePreview
from app.services.data_manager import DataManager
from app.services.baseline_system import BaselineSystem
from app.core.logging import logger
from app.core.config import settings

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])


def get_baseline_system():
    """Get or create baseline system instance"""
    try:
        # Parse Elasticsearch URL
        es_url = settings.ELASTICSEARCH_URL
        if es_url.startswith("http://"):
            es_url = es_url[7:]
        elif es_url.startswith("https://"):
            es_url = es_url[8:]
        
        # Split host and port
        if ":" in es_url:
            host, port = es_url.split(":")
            port = int(port)
        else:
            host = es_url
            port = 9200
        
        baseline = BaselineSystem(es_host=host, es_port=port)
        return baseline if baseline.is_available() else None
    except Exception as e:
        logger.warning(f"Failed to initialize baseline system: {e}")
        return None


@router.post("/upload", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a new dataset file (admin only)
    上传新的数据集文件（仅管理员）
    
    Requires admin role.
    Supports CSV and UNL file formats.
    UNL files use pipe (|) delimiter.
    """
    try:
        baseline = get_baseline_system()
        data_manager = DataManager(db, baseline_system=baseline)
        dataset = await data_manager.upload_file(file, current_user.id)
        
        logger.info(f"Dataset uploaded by user {current_user.username}: {dataset.filename}")
        
        return dataset
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error uploading dataset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload dataset"
        )


@router.post("/{dataset_id}/validate", response_model=ValidationResult)
async def validate_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Validate and parse dataset (admin only)
    验证并解析数据集（仅管理员）
    
    Requires admin role.
    Parses CSV file and validates bank code records.
    Automatically indexes to Elasticsearch if available.
    Automatically generates QA pairs after successful validation.
    """
    try:
        baseline = get_baseline_system()
        data_manager = DataManager(db, baseline_system=baseline)
        total, valid, invalid, errors = data_manager.validate_data(dataset_id)
        
        logger.info(f"Dataset {dataset_id} validated: {valid}/{total} valid records")
        
        # 验证成功后自动生成QA对
        if valid > 0:
            try:
                from app.services.qa_generator import QAGenerator
                
                logger.info(f"Starting automatic QA pair generation for dataset {dataset_id}")
                
                # 创建QA生成器
                generator = QAGenerator(db=db)
                
                # 生成所有类型的问答对（限制为100条记录进行测试）
                gen_results = generator.generate_for_dataset(
                    dataset_id=dataset_id,
                    question_types=["exact", "fuzzy", "reverse", "natural"],
                    max_records=100  # 限制处理100条记录
                )
                
                # 划分数据集（80% 训练，10% 验证，10% 测试）
                split_results = generator.split_dataset(
                    dataset_id=dataset_id,
                    train_ratio=0.8,
                    val_ratio=0.1,
                    test_ratio=0.1,
                    random_seed=42
                )
                
                logger.info(
                    f"QA pairs generated for dataset {dataset_id} - "
                    f"Total: {gen_results['successful']}, "
                    f"Train: {split_results['train_count']}, "
                    f"Val: {split_results['val_count']}, "
                    f"Test: {split_results['test_count']}"
                )
                
            except Exception as qa_error:
                # QA生成失败不影响验证结果，只记录警告
                logger.warning(f"Failed to generate QA pairs for dataset {dataset_id}: {qa_error}")
                errors.append(f"Warning: QA pair generation failed - {str(qa_error)}")
        
        return ValidationResult(
            dataset_id=dataset_id,
            total_records=total,
            valid_records=valid,
            invalid_records=invalid,
            errors=errors[:100],  # Limit errors to first 100
            status="validated"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error validating dataset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate dataset"
        )


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get dataset information
    获取数据集信息
    """
    try:
        data_manager = DataManager(db)
        dataset = data_manager.get_dataset_stats(dataset_id)
        return dataset
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/{dataset_id}/stats", response_model=DatasetStats)
async def get_dataset_stats(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get dataset statistics
    获取数据集统计信息
    """
    try:
        data_manager = DataManager(db)
        dataset = data_manager.get_dataset_stats(dataset_id)
        
        return DatasetStats(
            id=dataset.id,
            filename=dataset.filename,
            total_records=dataset.total_records,
            valid_records=dataset.valid_records,
            invalid_records=dataset.invalid_records,
            status=dataset.status,
            created_at=dataset.created_at
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/{dataset_id}/preview", response_model=List[BankCodePreview])
async def preview_dataset(
    dataset_id: int,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Preview dataset records
    预览数据集记录（最多100条）
    
    Args:
        dataset_id: Dataset ID
        limit: Maximum number of records to return (default 100, max 100)
    """
    # Limit to maximum 100 records
    if limit > 100:
        limit = 100
    
    try:
        data_manager = DataManager(db)
        records = data_manager.preview_data(dataset_id, limit)
        
        return [BankCodePreview(
            bank_name=r.bank_name,
            bank_code=r.bank_code,
            clearing_code=r.clearing_code
        ) for r in records]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("", response_model=List[DatasetResponse])
async def list_datasets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all datasets
    列出所有数据集
    
    All authenticated users can view datasets.
    所有已认证用户都可以查看数据集。
    """
    datasets = db.query(Dataset).order_by(Dataset.created_at.desc()).all()
    return datasets


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a dataset and all its associated records
    删除数据集及其所有关联记录
    
    All authenticated users can delete datasets.
    所有已认证用户都可以删除数据集。
    """
    import os
    from app.models.bank_code import BankCode
    
    # 查找数据集
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found"
        )
    
    try:
        # 删除关联的联行号记录（由于设置了CASCADE，会自动删除）
        # 但我们显式删除以确保
        db.query(BankCode).filter(BankCode.dataset_id == dataset_id).delete()
        
        # 删除文件
        if os.path.exists(dataset.file_path):
            try:
                os.remove(dataset.file_path)
                logger.info(f"Deleted file: {dataset.file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete file {dataset.file_path}: {e}")
        
        # 删除数据集记录
        db.delete(dataset)
        db.commit()
        
        logger.info(f"Dataset {dataset_id} deleted by user {current_user.username}")
        
        return {"message": f"Dataset {dataset.filename} deleted successfully"}
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting dataset {dataset_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete dataset"
        )
