"""
数据管理API端点
"""

from typing import Any
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
import os
from datetime import datetime

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_admin_user
from app.models.user import User
from app.models.dataset import Dataset, DatasetRecord, DatasetStatus, DatasetFormat
from app.schemas.common import PaginationResponse, PaginationInfo
from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError, DataError
from app.utils.file_utils import (
    save_upload_file,
    get_file_hash,
    get_file_extension,
    generate_unique_filename,
    read_dataset_file,
    validate_bank_data_format
)

router = APIRouter()


@router.post("/upload", summary="上传数据文件")
async def upload_file(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(None),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    上传数据文件（仅管理员）
    """
    # 生成唯一文件名
    unique_filename = generate_unique_filename(file.filename, current_user.id)
    file_path = os.path.join(settings.DATA_STORAGE_PATH, unique_filename)
    
    # 保存文件
    saved_path, file_size = await save_upload_file(file, file_path)
    
    # 计算文件哈希
    file_hash = get_file_hash(saved_path)
    
    # 检查文件是否已存在
    existing_dataset = db.query(Dataset).filter(Dataset.file_hash == file_hash).first()
    if existing_dataset:
        os.remove(saved_path)
        raise ValidationError("文件已存在")
    
    # 确定文件格式
    extension = get_file_extension(file.filename)
    if extension == '.csv':
        file_format = DatasetFormat.CSV
    elif extension == '.txt':
        file_format = DatasetFormat.TXT
    elif extension in ['.xlsx', '.xls']:
        file_format = DatasetFormat.EXCEL
    else:
        os.remove(saved_path)
        raise ValidationError(f"不支持的文件格式: {extension}")
    
    # 创建数据集记录
    dataset = Dataset(
        name=name,
        description=description,
        file_path=saved_path,
        original_filename=file.filename,
        file_size=file_size,
        file_hash=file_hash,
        format=file_format,
        status=DatasetStatus.UPLOADED,
        created_by=current_user.id
    )
    
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    
    return {
        "dataset_id": dataset.id,
        "name": dataset.name,
        "file_size": dataset.file_size,
        "format": dataset.format,
        "status": dataset.status
    }


@router.get("/datasets", response_model=PaginationResponse, summary="获取数据集列表")
async def get_datasets(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    获取数据集列表
    """
    # 构建查询
    query = db.query(Dataset)
    
    # 过滤条件
    if status:
        query = query.filter(Dataset.status == status)
    
    # 获取总数
    total = query.count()
    
    # 分页查询
    offset = (page - 1) * size
    datasets = query.order_by(Dataset.created_at.desc()).offset(offset).limit(size).all()
    
    return {
        "items": datasets,
        "pagination": PaginationInfo.create(page, size, total)
    }


@router.get("/datasets/{dataset_id}", summary="获取数据集详情")
async def get_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    获取数据集详情
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise NotFoundError("数据集不存在")
    
    return dataset


@router.post("/datasets/{dataset_id}/validate", summary="验证数据集")
async def validate_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    验证数据集格式（仅管理员）
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise NotFoundError("数据集不存在")
    
    # 更新状态为验证中
    dataset.status = DatasetStatus.VALIDATING
    db.commit()
    
    try:
        # 读取数据文件
        df = read_dataset_file(dataset.file_path, dataset.format)
        
        # 验证数据格式
        is_valid, errors = validate_bank_data_format(df)
        
        # 保存验证结果
        validation_result = {
            "total_records": len(df),
            "valid_records": len(df) - len(errors) if not is_valid else len(df),
            "invalid_records": len(errors),
            "error_details": errors[:50] if errors else []  # 只保存前50个错误
        }
        
        dataset.validation_result = validation_result
        dataset.record_count = len(df)
        
        if is_valid:
            dataset.status = DatasetStatus.VALIDATED
            
            # 保存数据记录到数据库
            for index, row in df.iterrows():
                record = DatasetRecord(
                    dataset_id=dataset.id,
                    line_number=index + 1,
                    bank_name=str(row['bank_name']).strip(),
                    bank_code=str(row['bank_code']).strip(),
                    clearing_code=str(row['clearing_code']).strip(),
                    is_valid=True
                )
                db.add(record)
        else:
            dataset.status = DatasetStatus.ERROR
        
        db.commit()
        db.refresh(dataset)
        
        return {
            "dataset_id": dataset.id,
            "status": dataset.status,
            "validation_result": validation_result
        }
        
    except Exception as e:
        dataset.status = DatasetStatus.ERROR
        dataset.validation_result = {"error": str(e)}
        db.commit()
        raise DataError(f"数据验证失败: {str(e)}")


@router.get("/datasets/{dataset_id}/preview", summary="预览数据集")
async def preview_dataset(
    dataset_id: int,
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    预览数据集内容
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise NotFoundError("数据集不存在")
    
    # 查询数据记录
    records = db.query(DatasetRecord).filter(
        DatasetRecord.dataset_id == dataset_id
    ).limit(limit).all()
    
    return {
        "dataset_id": dataset.id,
        "total_records": dataset.record_count,
        "preview_records": [
            {
                "line_number": r.line_number,
                "bank_name": r.bank_name,
                "bank_code": r.bank_code,
                "clearing_code": r.clearing_code,
                "is_valid": r.is_valid
            }
            for r in records
        ]
    }


@router.delete("/datasets/{dataset_id}", summary="删除数据集")
async def delete_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    删除数据集（仅管理员）
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise NotFoundError("数据集不存在")
    
    # 删除文件
    if os.path.exists(dataset.file_path):
        os.remove(dataset.file_path)
    
    # 删除数据库记录
    db.delete(dataset)
    db.commit()
    
    return {"message": "数据集删除成功"}