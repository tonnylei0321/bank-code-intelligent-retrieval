"""
训练数据生成API - 大模型数据泛化服务

提供API接口用于生成银行实体识别的训练数据
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.core.deps import get_db, get_current_admin_user
from app.services.training_data_generator import TrainingDataGenerator
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/training-data", tags=["Training Data Generation"])


@router.post("/generate")
async def generate_training_data(
    background_tasks: BackgroundTasks,
    limit: Optional[int] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    生成银行实体识别训练数据
    
    使用大模型将标准银行数据泛化为小模型训练样本
    
    Args:
        limit: 限制处理的银行数量（用于测试，默认处理所有）
        
    Returns:
        任务状态和预期完成时间
    """
    try:
        logger.info(f"Admin {current_user.username} requested training data generation")
        
        # 创建数据生成器
        generator = TrainingDataGenerator()
        
        # 后台任务生成数据
        background_tasks.add_task(
            _generate_dataset_task,
            generator,
            limit
        )
        
        return {
            "success": True,
            "message": "训练数据生成任务已启动",
            "details": {
                "limit": limit or "无限制",
                "estimated_time": "预计10-30分钟",
                "output_file": "data/bank_ner_training_data.json"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to start training data generation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"启动训练数据生成失败: {str(e)}"
        )


@router.post("/generate-sample")
async def generate_sample_data(
    bank_name: str,
    bank_code: str,
    current_user: User = Depends(get_current_admin_user)
):
    """
    为单个银行生成样本数据（用于测试）
    
    Args:
        bank_name: 银行名称
        bank_code: 联行号
        
    Returns:
        生成的训练样本
    """
    try:
        generator = TrainingDataGenerator()
        
        bank_record = {
            "bank_name": bank_name,
            "bank_code": bank_code
        }
        
        variations = generator.generate_bank_variations(bank_record)
        
        return {
            "success": True,
            "original_bank": bank_record,
            "generated_variations": variations,
            "count": len(variations)
        }
        
    except Exception as e:
        logger.error(f"Failed to generate sample data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"生成样本数据失败: {str(e)}"
        )


async def _generate_dataset_task(generator: TrainingDataGenerator, limit: Optional[int]):
    """
    后台任务：生成完整的训练数据集
    """
    try:
        logger.info(f"Starting dataset generation task with limit={limit}")
        
        # 生成训练数据
        training_data = generator.generate_comprehensive_dataset(limit=limit)
        
        # 保存到文件
        generator.save_training_dataset(training_data)
        
        logger.info(f"Dataset generation task completed: {len(training_data)} samples")
        
    except Exception as e:
        logger.error(f"Dataset generation task failed: {e}")


@router.get("/status")
async def get_generation_status(
    current_user: User = Depends(get_current_admin_user)
):
    """
    获取训练数据生成状态
    """
    try:
        import os
        
        data_file = "data/bank_ner_training_data.json"
        report_file = "data/bank_ner_training_data_report.txt"
        
        status = {
            "data_file_exists": os.path.exists(data_file),
            "report_file_exists": os.path.exists(report_file),
            "data_file_size": None,
            "last_modified": None
        }
        
        if status["data_file_exists"]:
            stat = os.stat(data_file)
            status["data_file_size"] = f"{stat.st_size / 1024 / 1024:.2f} MB"
            status["last_modified"] = stat.st_mtime
        
        # 读取报告内容
        if status["report_file_exists"]:
            with open(report_file, 'r', encoding='utf-8') as f:
                status["report_content"] = f.read()
        
        return {
            "success": True,
            "status": status
        }
        
    except Exception as e:
        logger.error(f"Failed to get generation status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取状态失败: {str(e)}"
        )