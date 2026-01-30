"""
银行数据管理API

功能：
- 手动触发数据加载
- 查看加载状态
- 查看数据统计
- 智能生成训练样本
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import tempfile

from app.core.deps import get_current_admin_user, get_current_user, get_db
from app.models.user import User
from app.models.dataset import Dataset
from app.models.qa_pair import QAPair
from app.services.bank_data_loader import BankDataLoader
from app.services.scheduler import get_scheduler
from app.services.smart_sample_generator import SmartSampleGenerator
from app.core.logging import logger

router = APIRouter(prefix="/api/v1/bank-data", tags=["bank-data"])


class LoadResponse(BaseModel):
    """数据加载响应"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class SmartGenerationRequest(BaseModel):
    """智能生成请求"""
    samples_per_bank: int = 7
    use_llm: bool = True
    llm_model: str = "Qwen/Qwen2.5-7B-Instruct"


class SmartGenerationResponse(BaseModel):
    """智能生成响应"""
    success: bool
    message: str
    dataset_id: Optional[int] = None
    total_banks: int = 0
    total_samples: int = 0
    samples_per_bank: int = 0



@router.post("/load", response_model=LoadResponse, status_code=status.HTTP_200_OK)
async def load_bank_data(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    手动触发银行数据加载（仅管理员）
    
    从data/T_BANK_LINE_NO_ICBC_ALL.unl文件加载银行联行号数据
    """
    try:
        logger.info(f"管理员 {current_user.username} 触发手动数据加载")
        
        loader = BankDataLoader(db)
        result = loader.check_and_load_if_exists()
        
        if result.get('success'):
            return LoadResponse(
                success=True,
                message=f"数据加载成功 - 新增: {result.get('new_records', 0)}, 更新: {result.get('updated_records', 0)}",
                data=result
            )
        else:
            return LoadResponse(
                success=False,
                message=result.get('message', '数据加载失败'),
                data=result
            )
    
    except Exception as e:
        logger.error(f"数据加载失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"数据加载失败: {str(e)}"
        )


@router.get("/statistics", status_code=status.HTTP_200_OK)
async def get_statistics(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    获取银行数据统计信息（仅管理员）
    
    返回：
    - 总记录数
    - 各数据集统计
    - 最后加载时间
    """
    try:
        loader = BankDataLoader(db)
        stats = loader.get_load_statistics()
        
        return {
            "success": True,
            "data": stats
        }
    
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计信息失败: {str(e)}"
        )


@router.get("/scheduler/status", status_code=status.HTTP_200_OK)
async def get_scheduler_status(
    current_user: User = Depends(get_current_admin_user)
):
    """
    获取定时任务状态（仅管理员）
    
    返回：
    - 是否运行中
    - 上次执行时间
    - 下次执行时间
    - 上次执行结果
    """
    try:
        scheduler = get_scheduler()
        status_info = scheduler.get_status()
        
        return {
            "success": True,
            "data": status_info
        }
    
    except Exception as e:
        logger.error(f"获取调度器状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取调度器状态失败: {str(e)}"
        )


@router.post("/scheduler/trigger", status_code=status.HTTP_200_OK)
async def trigger_scheduler(
    current_user: User = Depends(get_current_admin_user)
):
    """
    手动触发定时任务（仅管理员）
    
    立即执行一次数据加载任务
    """
    try:
        logger.info(f"管理员 {current_user.username} 手动触发定时任务")
        
        scheduler = get_scheduler()
        result = scheduler.trigger_now()
        
        if result.get('success'):
            return {
                "success": True,
                "message": "任务执行成功",
                "data": result
            }
        else:
            return {
                "success": False,
                "message": result.get('message', '任务执行失败'),
                "data": result
            }
    
    except Exception as e:
        logger.error(f"触发任务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"触发任务失败: {str(e)}"
        )



@router.post("/upload-and-generate", response_model=SmartGenerationResponse)
async def upload_and_generate_training_data(
    file: UploadFile = File(...),
    samples_per_bank: int = 7,
    use_llm: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    上传银行数据文件并智能生成训练样本
    
    Args:
        file: .unl 格式的银行数据文件
        samples_per_bank: 每个银行生成的样本数量（默认7个）
        use_llm: 是否使用LLM生成多样化问法（默认True）
    
    Returns:
        生成结果，包括数据集ID和统计信息
    """
    try:
        logger.info(f"用户 {current_user.username} 上传文件并请求智能生成训练样本")
        logger.info(f"参数: samples_per_bank={samples_per_bank}, use_llm={use_llm}")
        
        # 验证文件格式
        if not file.filename.endswith('.unl'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="仅支持 .unl 格式文件"
            )
        
        # 保存上传的文件到临时位置
        with tempfile.NamedTemporaryFile(delete=False, suffix='.unl') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # 1. 解析 .unl 文件
            logger.info("解析 .unl 文件...")
            bank_records = parse_unl_file(tmp_file_path)
            logger.info(f"解析完成，共 {len(bank_records)} 条银行记录")
            
            if len(bank_records) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="文件中没有有效的银行记录"
                )
            
            # 2. 生成训练样本
            logger.info("开始生成训练样本...")
            
            if use_llm:
                # 使用 LLM 生成
                generator = SmartSampleGenerator()
                try:
                    generator.load_model()
                    training_samples = generator.batch_generate(
                        bank_records,
                        samples_per_bank=samples_per_bank
                    )
                finally:
                    # 确保卸载模型释放内存
                    generator.unload_model()
            else:
                # 使用规则生成
                generator = SmartSampleGenerator()
                training_samples = []
                for record in bank_records:
                    samples = generator.generate_samples_rule_based(
                        record["name"],
                        record["code"],
                        samples_per_bank
                    )
                    training_samples.extend(samples)
            
            logger.info(f"生成完成，共 {len(training_samples)} 个训练样本")
            
            # 3. 创建数据集
            dataset = Dataset(
                filename=f"智能生成-{file.filename}",
                file_path=tmp_file_path,
                file_size=len(file_content),
                total_records=len(bank_records),
                valid_records=len(bank_records),
                invalid_records=0,
                status="validated",
                uploaded_by=current_user.id
            )
            db.add(dataset)
            db.flush()
            
            # 4. 保存训练样本到数据库
            logger.info("保存训练样本到数据库...")
            for sample in training_samples:
                qa_pair = QAPair(
                    dataset_id=dataset.id,
                    question=sample["question"],
                    answer=sample["answer"],
                    bank_name=sample.get("bank_name"),
                    bank_code=sample.get("bank_code")
                )
                db.add(qa_pair)
            
            db.commit()
            logger.info(f"数据集创建成功，ID: {dataset.id}")
            
            return SmartGenerationResponse(
                success=True,
                message=f"成功生成训练数据集",
                dataset_id=dataset.id,
                total_banks=len(bank_records),
                total_samples=len(training_samples),
                samples_per_bank=samples_per_bank
            )
            
        finally:
            # 清理临时文件
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"智能生成训练样本失败: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成失败: {str(e)}"
        )


def parse_unl_file(file_path: str) -> List[Dict[str, str]]:
    """
    解析 .unl 文件
    
    格式: 联行号|银行名称|其他字段...
    
    Args:
        file_path: 文件路径
    
    Returns:
        银行记录列表 [{"code": "...", "name": "..."}, ...]
    """
    bank_records = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                # 按 | 分割
                parts = line.split('|')
                
                if len(parts) < 2:
                    logger.warning(f"第 {line_num} 行格式不正确，跳过: {line[:50]}")
                    continue
                
                bank_code = parts[0].strip()
                bank_name = parts[1].strip()
                
                # 验证联行号（应该是12位数字）
                if not bank_code or len(bank_code) != 12 or not bank_code.isdigit():
                    logger.warning(f"第 {line_num} 行联行号格式不正确，跳过: {bank_code}")
                    continue
                
                # 验证银行名称
                if not bank_name:
                    logger.warning(f"第 {line_num} 行银行名称为空，跳过")
                    continue
                
                bank_records.append({
                    "code": bank_code,
                    "name": bank_name
                })
        
        logger.info(f"成功解析 {len(bank_records)} 条银行记录")
        return bank_records
        
    except Exception as e:
        logger.error(f"解析文件失败: {e}")
        raise


@router.get("/generation-status/{dataset_id}")
async def get_generation_status(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取数据集生成状态
    
    Args:
        dataset_id: 数据集ID
    
    Returns:
        数据集详细信息和样本统计
    """
    try:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="数据集不存在"
            )
        
        # 获取样本统计
        total_samples = db.query(QAPair).filter(QAPair.dataset_id == dataset_id).count()
        
        # 获取样本示例
        sample_examples = db.query(QAPair).filter(
            QAPair.dataset_id == dataset_id
        ).limit(5).all()
        
        return {
            "success": True,
            "dataset": {
                "id": dataset.id,
                "name": dataset.name,
                "description": dataset.description,
                "status": dataset.status,
                "total_samples": total_samples,
                "created_at": dataset.created_at.isoformat() if dataset.created_at else None
            },
            "sample_examples": [
                {
                    "question": sample.question,
                    "answer": sample.answer
                }
                for sample in sample_examples
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取生成状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取状态失败: {str(e)}"
        )
