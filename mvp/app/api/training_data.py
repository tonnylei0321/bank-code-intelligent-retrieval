"""
训练数据生成API - 大模型数据泛化服务

提供API接口用于生成银行实体识别的训练数据
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
import logging
import json
import os
from datetime import datetime

from app.core.deps import get_db, get_current_admin_user
from app.services.training_data_generator import TrainingDataGenerator
from app.services.parallel_training_generator import ParallelTrainingGenerator, create_training_dataset
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/training-data", tags=["Training Data Generation"])

# 全局进度状态存储
_generation_progress = {}


@router.post("/generate-parallel")
async def generate_parallel_training_data(
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    generation_method: str = Form("llm"),
    data_amount: str = Form("full"),
    sample_count: int = Form(1000),
    samples_per_bank: int = Form(7),
    limit: Optional[int] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    使用并行多LLM生成大规模训练数据
    
    支持两种模式：
    1. 文件上传模式：上传.unl文件并生成训练数据
    2. 数据库模式：使用现有数据库中的银行数据
    
    Args:
        file: 可选的.unl格式银行数据文件
        generation_method: 生成方式 ("llm" 使用大模型, "rule" 使用规则)
        data_amount: 数据量 ("full" 全量数据, "limited" 指定条数)
        sample_count: 指定条数（当data_amount=limited时）
        samples_per_bank: 每个银行生成样本数
        limit: 限制处理的银行数量（用于测试，默认处理所有）
        
    Returns:
        任务状态和预期完成时间
    """
    try:
        logger.info(f"Admin {current_user.username} requested parallel training data generation")
        logger.info(f"参数: method={generation_method}, amount={data_amount}, count={sample_count}, samples_per_bank={samples_per_bank}")
        
        # 验证参数
        if generation_method not in ['llm', 'rule']:
            raise HTTPException(
                status_code=400,
                detail="generation_method 必须是 'llm' 或 'rule'"
            )
        
        if data_amount not in ['full', 'limited']:
            raise HTTPException(
                status_code=400,
                detail="data_amount 必须是 'full' 或 'limited'"
            )
        
        if data_amount == 'limited' and (sample_count < 100 or sample_count > 50000):
            raise HTTPException(
                status_code=400,
                detail="sample_count 必须在 100-50000 之间"
            )
        
        # 创建数据集
        method_name = "大模型生成" if generation_method == 'llm' else "规则生成"
        amount_name = "全量数据" if data_amount == 'full' else f"{sample_count}条数据"
        dataset_name = f"并行{method_name}-{amount_name}"
        
        if file:
            dataset_name += f"-{file.filename}"
        
        dataset_id = create_training_dataset(dataset_name)
        
        # 初始化进度状态
        task_id = f"parallel_gen_{dataset_id}_{int(datetime.now().timestamp())}"
        _generation_progress[task_id] = {
            "status": "starting",
            "progress": 0,
            "total_banks": 0,
            "processed_banks": 0,
            "generated_samples": 0,
            "failed_banks": 0,
            "start_time": datetime.now().isoformat(),
            "dataset_id": dataset_id,
            "errors": [],
            "generation_method": generation_method,
            "data_amount": data_amount,
            "sample_count": sample_count if data_amount == 'limited' else None
        }
        
        # 处理文件上传（如果有）
        tmp_file_path = None
        if file:
            # 验证文件格式
            if not file.filename.endswith('.unl'):
                raise HTTPException(
                    status_code=400,
                    detail="仅支持 .unl 格式文件"
                )
            
            # 保存上传的文件到临时位置
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.unl') as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                tmp_file_path = tmp_file.name
        
        # 后台任务生成数据
        background_tasks.add_task(
            _parallel_generation_task,
            task_id,
            dataset_id,
            generation_method,
            data_amount,
            sample_count,
            samples_per_bank,
            limit,
            tmp_file_path,
            file.filename if file else None
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "dataset_id": dataset_id,
            "message": f"并行{method_name}任务已启动",
            "details": {
                "generation_method": generation_method,
                "data_amount": data_amount,
                "sample_count": sample_count if data_amount == 'limited' else None,
                "samples_per_bank": samples_per_bank,
                "limit": limit or "无限制",
                "estimated_time": "预计10-30分钟" if generation_method == 'llm' else "预计2-5分钟",
                "llm_count": 2 if generation_method == 'llm' else 0,
                "max_workers": 8 if generation_method == 'llm' else 1
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to start parallel training data generation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"启动并行训练数据生成失败: {str(e)}"
        )


@router.get("/progress/{task_id}")
async def get_generation_progress(
    task_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """
    获取训练数据生成进度
    
    Args:
        task_id: 任务ID
        
    Returns:
        实时进度信息
    """
    try:
        if task_id not in _generation_progress:
            raise HTTPException(
                status_code=404,
                detail="任务不存在或已过期"
            )
        
        progress_data = _generation_progress[task_id].copy()
        
        # 计算进度百分比
        if progress_data["total_banks"] > 0:
            progress_data["progress_percentage"] = (
                progress_data["processed_banks"] / progress_data["total_banks"]
            ) * 100
        else:
            progress_data["progress_percentage"] = 0
        
        # 计算预估剩余时间
        if progress_data["processed_banks"] > 0 and progress_data["status"] == "running":
            start_time = datetime.fromisoformat(progress_data["start_time"])
            elapsed_seconds = (datetime.now() - start_time).total_seconds()
            avg_time_per_bank = elapsed_seconds / progress_data["processed_banks"]
            remaining_banks = progress_data["total_banks"] - progress_data["processed_banks"]
            eta_seconds = remaining_banks * avg_time_per_bank
            progress_data["eta_minutes"] = eta_seconds / 60
        else:
            progress_data["eta_minutes"] = None
        
        return {
            "success": True,
            "progress": progress_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get generation progress: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取进度失败: {str(e)}"
        )


async def _parallel_generation_task(
    task_id: str,
    dataset_id: int,
    generation_method: str,
    data_amount: str,
    sample_count: int,
    samples_per_bank: int,
    limit: Optional[int],
    tmp_file_path: Optional[str] = None,
    filename: Optional[str] = None
):
    """
    后台任务：并行生成训练数据
    """
    try:
        logger.info(f"Starting parallel generation task {task_id}")
        logger.info(f"参数: method={generation_method}, amount={data_amount}, count={sample_count}, samples_per_bank={samples_per_bank}")
        
        # 更新状态为运行中
        _generation_progress[task_id]["status"] = "running"
        
        # 如果有文件上传，先处理文件
        if tmp_file_path and filename:
            logger.info(f"任务 {task_id}: 处理上传的文件 {filename}")
            
            # 解析文件并保存银行记录
            from app.core.database import SessionLocal
            from app.models.bank_code import BankCode
            
            db = SessionLocal()
            try:
                # 解析 .unl 文件
                bank_records = parse_unl_file_from_training_data(tmp_file_path)
                logger.info(f"任务 {task_id}: 解析完成，共 {len(bank_records)} 条银行记录")
                
                if len(bank_records) == 0:
                    _generation_progress[task_id].update({
                        "status": "failed",
                        "error": "文件中没有有效的银行记录"
                    })
                    return
                
                # 根据数据量设置进行抽样
                if data_amount == 'limited' and len(bank_records) > sample_count:
                    logger.info(f"任务 {task_id}: 按银行维度随机抽取 {sample_count} 条记录")
                    import random
                    random.shuffle(bank_records)
                    bank_records = bank_records[:sample_count]
                    logger.info(f"任务 {task_id}: 抽样完成，实际使用 {len(bank_records)} 条记录")
                
                # 保存银行记录到数据库
                for record in bank_records:
                    bank_code_record = BankCode(
                        dataset_id=dataset_id,  # 设置正确的dataset_id
                        bank_name=record["name"],
                        bank_code=record["code"],
                        clearing_code=record["code"],
                        is_valid=1
                    )
                    db.add(bank_code_record)
                
                db.commit()
                logger.info(f"任务 {task_id}: 银行记录已保存到数据库")
                
            finally:
                db.close()
                # 清理临时文件
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
        
        # 创建进度回调函数
        def progress_callback(stats):
            if task_id in _generation_progress:
                _generation_progress[task_id].update({
                    "total_banks": stats["total_banks"],
                    "processed_banks": stats["processed_banks"],
                    "generated_samples": stats["generated_samples"],
                    "failed_banks": stats["failed_banks"],
                    "errors": stats.get("errors", [])
                })
        
        # 根据生成方式选择生成器
        if generation_method == 'llm':
            # 使用大模型并行生成
            logger.info(f"任务 {task_id}: 使用大模型并行生成")
            generator = ParallelTrainingGenerator(
                dataset_id, 
                progress_callback=progress_callback
            )
            
            # 运行并行生成
            generator.run_parallel_generation(limit=limit, samples_per_bank=samples_per_bank)
            
        else:
            # 使用规则生成
            logger.info(f"任务 {task_id}: 使用规则生成")
            from app.services.smart_sample_generator import SmartSampleGenerator
            from app.core.database import SessionLocal
            from app.models.bank_code import BankCode
            
            db = SessionLocal()
            try:
                # 获取银行数据
                query = db.query(BankCode).filter(BankCode.is_valid == 1)
                if limit:
                    query = query.limit(limit)
                
                banks = query.all()
                total_banks = len(banks)
                
                logger.info(f"任务 {task_id}: 规则生成开始，共 {total_banks} 个银行")
                
                # 创建规则生成器（不需要数据库参数）
                generator = SmartSampleGenerator()
                
                # 生成训练样本
                generated_samples = 0
                for i, bank in enumerate(banks):
                    try:
                        samples = generator.generate_samples_for_bank(
                            bank.bank_name, 
                            bank.bank_code,
                            samples_per_bank
                        )
                        
                        # 将生成的样本保存到数据库
                        from app.models.qa_pair import QAPair
                        for sample in samples:
                            qa_pair = QAPair(
                                dataset_id=dataset_id,
                                question=sample["question"],
                                answer=sample["answer"],
                                bank_name=sample["bank_name"],
                                bank_code=sample["bank_code"]
                            )
                            db.add(qa_pair)
                        
                        generated_samples += len(samples)
                        
                        # 更新进度
                        progress_callback({
                            "total_banks": total_banks,
                            "processed_banks": i + 1,
                            "generated_samples": generated_samples,
                            "failed_banks": 0,
                            "errors": []
                        })
                        
                    except Exception as e:
                        logger.error(f"生成银行 {bank.bank_name} 的样本失败: {e}")
                        continue
                
                logger.info(f"任务 {task_id}: 规则生成完成，共 {generated_samples} 个样本")
                
            finally:
                db.close()
        
        # 更新最终状态
        _generation_progress[task_id].update({
            "status": "completed",
            "progress": 100,
            "completed_at": datetime.now().isoformat()
        })
        
        logger.info(f"Parallel generation task {task_id} completed")
        
    except Exception as e:
        logger.error(f"Parallel generation task {task_id} failed: {e}")
        if task_id in _generation_progress:
            _generation_progress[task_id].update({
                "status": "failed",
                "error": str(e),
                "failed_at": datetime.now().isoformat()
            })


def parse_unl_file_from_training_data(file_path: str) -> List[Dict[str, str]]:
    """
    解析 .unl 文件（从training_data模块调用）
    
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


@router.post("/generate")
async def generate_training_data(
    background_tasks: BackgroundTasks,
    limit: Optional[int] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    生成银行实体识别训练数据（原有方法）
    
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