"""
银行数据管理API

功能：
- 手动触发数据加载
- 查看加载状态
- 查看数据统计
- 智能生成训练样本
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import os
import tempfile
import threading
import time
import uuid

from app.core.deps import get_current_admin_user, get_current_user, get_db
from app.models.user import User
from app.models.dataset import Dataset
from app.models.qa_pair import QAPair
from app.services.bank_data_loader import BankDataLoader
from app.services.scheduler import get_scheduler
from app.services.smart_sample_generator import SmartSampleGenerator
from app.core.logging import logger

router = APIRouter(prefix="/api/v1/bank-data", tags=["bank-data"])

# 全局进度存储
generation_progress = {}


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
    task_id: Optional[str] = None  # 添加任务ID字段



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
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    generation_method: str = Form("rule"),  # 生成方式：llm 或 rule
    llm_name: str = Form("qwen"),           # LLM名称：qwen, deepseek, chatglm
    data_amount: str = Form("limited"),     # 数据量：full 或 limited
    sample_count: int = Form(1000),         # 指定条数（当data_amount=limited时）
    samples_per_bank: int = Form(7),        # 每个银行生成样本数
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    上传银行数据文件并智能生成训练样本（异步）
    
    Args:
        file: .unl 格式的银行数据文件
        generation_method: 生成方式 ("llm" 使用大模型, "rule" 使用规则)
        llm_name: LLM名称 ("qwen", "deepseek", "chatglm")
        data_amount: 数据量 ("full" 全量数据, "limited" 指定条数)
        sample_count: 指定条数（当data_amount=limited时）
        samples_per_bank: 每个银行生成的样本数量（默认7个）
    
    Returns:
        任务ID，用于查询进度
    """
    try:
        logger.info(f"用户 {current_user.username} 上传文件并请求智能生成训练样本")
        logger.info(f"参数: method={generation_method}, llm={llm_name}, amount={data_amount}, count={sample_count}, samples_per_bank={samples_per_bank}")
        
        # 验证文件格式
        if not file.filename.endswith('.unl'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="仅支持 .unl 格式文件"
            )
        
        # 验证参数
        if generation_method not in ['llm', 'rule']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="generation_method 必须是 'llm' 或 'rule'"
            )
        
        if generation_method == 'llm' and llm_name not in ['qwen', 'deepseek', 'chatglm']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="llm_name 必须是 'qwen', 'deepseek' 或 'chatglm'"
            )
        
        if data_amount not in ['full', 'limited']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="data_amount 必须是 'full' 或 'limited'"
            )
        
        if data_amount == 'limited' and (sample_count < 100 or sample_count > 50000):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="sample_count 必须在 100-50000 之间"
            )
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 初始化进度信息
        generation_progress[task_id] = {
            "status": "starting",
            "progress_percentage": 0,
            "processed_banks": 0,
            "total_banks": 0,
            "generated_samples": 0,
            "failed_banks": 0,
            "start_time": datetime.utcnow().isoformat(),
            "dataset_id": None,
            "error": None,
            "generation_method": generation_method,
            "llm_name": llm_name if generation_method == 'llm' else None,
            "data_amount": data_amount,
            "sample_count": sample_count if data_amount == 'limited' else None
        }
        
        # 保存上传的文件到临时位置
        with tempfile.NamedTemporaryFile(delete=False, suffix='.unl') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        # 启动后台任务
        background_tasks.add_task(
            process_generation_task,
            task_id,
            tmp_file_path,
            file.filename,
            len(content),
            generation_method,
            llm_name,
            data_amount,
            sample_count,
            samples_per_bank,
            current_user.id
        )
        
        return SmartGenerationResponse(
            success=True,
            message=f"智能生成任务已启动",
            dataset_id=None,  # 将在任务完成后设置
            total_banks=0,    # 将在解析后更新
            total_samples=0,  # 将在生成后更新
            samples_per_bank=samples_per_bank,
            task_id=task_id   # 添加任务ID
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动智能生成任务失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动任务失败: {str(e)}"
        )


def process_generation_task(
    task_id: str,
    tmp_file_path: str,
    filename: str,
    file_size: int,
    generation_method: str,
    llm_name: str,
    data_amount: str,
    sample_count: int,
    samples_per_bank: int,
    user_id: int
):
    """
    处理生成任务的后台函数
    """
    from app.core.database import SessionLocal
    
    db = SessionLocal()
    
    try:
        # 更新进度：开始解析
        generation_progress[task_id].update({
            "status": "parsing",
            "progress_percentage": 5
        })
        
        # 1. 解析 .unl 文件
        logger.info(f"任务 {task_id}: 解析 .unl 文件...")
        bank_records = parse_unl_file(tmp_file_path)
        logger.info(f"任务 {task_id}: 解析完成，共 {len(bank_records)} 条银行记录")
        
        if len(bank_records) == 0:
            generation_progress[task_id].update({
                "status": "failed",
                "error": "文件中没有有效的银行记录"
            })
            return
        
        # 2. 根据数据量设置进行抽样
        if data_amount == 'limited' and len(bank_records) > sample_count:
            logger.info(f"任务 {task_id}: 按银行维度随机抽取 {sample_count} 条记录")
            
            # 按银行维度随机抽取
            import random
            random.shuffle(bank_records)
            bank_records = bank_records[:sample_count]
            
            logger.info(f"任务 {task_id}: 抽样完成，实际使用 {len(bank_records)} 条记录")
        
        # 更新进度：创建数据集
        generation_progress[task_id].update({
            "status": "creating_dataset",
            "progress_percentage": 10,
            "total_banks": len(bank_records)
        })
        
        # 3. 创建数据集
        method_name = f"大模型生成({llm_name})" if generation_method == 'llm' else "规则生成"
        amount_name = "全量数据" if data_amount == 'full' else f"{sample_count}条数据"
        
        dataset = Dataset(
            filename=f"{method_name}-{amount_name}-{filename}",
            file_path=tmp_file_path,
            file_size=file_size,
            total_records=len(bank_records),
            valid_records=len(bank_records),
            invalid_records=0,
            status="processing",
            uploaded_by=user_id
        )
        db.add(dataset)
        db.flush()
        
        # 更新进度：保存银行记录
        generation_progress[task_id].update({
            "status": "saving_banks",
            "progress_percentage": 15,
            "dataset_id": dataset.id
        })
        
        # 4. 先将银行记录保存到BankCode表
        logger.info(f"任务 {task_id}: 保存银行记录到数据库...")
        from app.models.bank_code import BankCode
        bank_code_records = []
        for record in bank_records:
            bank_code_record = BankCode(
                dataset_id=dataset.id,  # 设置正确的dataset_id
                bank_name=record["name"],
                bank_code=record["code"],
                clearing_code=record["code"],
                is_valid=1
            )
            db.add(bank_code_record)
            bank_code_records.append(bank_code_record)
        
        db.flush()
        db.commit()
        logger.info(f"任务 {task_id}: 银行记录已保存，获得ID: {[r.id for r in bank_code_records[:3]]}...")
        
        # 更新进度：开始生成
        generation_progress[task_id].update({
            "status": "generating",
            "progress_percentage": 20
        })
        
        # 5. 根据生成方式选择生成器
        if generation_method == 'llm':
            # 使用大模型并行生成
            logger.info(f"任务 {task_id}: 使用大模型并行生成训练样本...")
            from app.services.parallel_training_generator import ParallelTrainingGenerator
            
            # 定义进度回调函数
            def progress_callback(stats):
                try:
                    progress_percentage = 20 + (stats.get("processed_banks", 0) / stats.get("total_banks", 1)) * 75
                    eta_seconds = stats.get("eta_seconds", 0)
                    eta_minutes = eta_seconds / 60 if eta_seconds > 0 else None
                    
                    generation_progress[task_id].update({
                        "progress_percentage": min(95, progress_percentage),
                        "processed_banks": stats.get("processed_banks", 0),
                        "generated_samples": stats.get("generated_samples", 0),
                        "failed_banks": stats.get("failed_banks", 0),
                        "eta_minutes": eta_minutes
                    })
                except Exception as e:
                    logger.error(f"进度回调错误: {e}")
            
            # 创建并行生成器（带进度回调）
            generator = ParallelTrainingGenerator(dataset.id, progress_callback)
            
            # 根据用户选择的LLM配置生成器
            generator.configure_llm(llm_name)
            generator.set_bank_count(len(bank_records))
            
            # 准备银行数据
            banks_data = []
            for record in bank_code_records:
                banks_data.append({
                    "id": record.id,
                    "bank_name": record.bank_name,
                    "bank_code": record.bank_code
                })
            
            logger.info(f"任务 {task_id}: 准备大模型并行生成，银行数据: {len(banks_data)} 个银行")
            
            try:
                # 使用并行生成器的完整方法
                logger.info(f"任务 {task_id}: 开始调用并行生成器...")
                training_samples = generator.run_parallel_generation_with_data(
                    banks_data, 
                    samples_per_bank=samples_per_bank,
                    use_llm=True
                )
                logger.info(f"任务 {task_id}: 大模型并行生成返回结果: {len(training_samples)} 个样本")
            except Exception as e:
                logger.error(f"任务 {task_id}: 并行生成过程中发生错误: {e}", exc_info=True)
                # 不回退到规则生成，而是抛出错误
                raise e
        
        else:
            # 使用规则生成
            logger.info(f"任务 {task_id}: 使用规则生成训练样本...")
            from app.services.smart_sample_generator import SmartSampleGenerator
            
            # 定义进度回调函数
            def progress_callback(processed, total, generated_samples):
                try:
                    progress_percentage = 20 + (processed / total) * 75
                    generation_progress[task_id].update({
                        "progress_percentage": min(95, progress_percentage),
                        "processed_banks": processed,
                        "generated_samples": generated_samples
                    })
                except Exception as e:
                    logger.error(f"进度回调错误: {e}")
            
            # 创建规则生成器（不需要数据库参数）
            generator = SmartSampleGenerator()
            
            # 准备银行数据
            banks_data = []
            for record in bank_code_records:
                banks_data.append({
                    "id": record.id,
                    "bank_name": record.bank_name,
                    "bank_code": record.bank_code
                })
            
            logger.info(f"任务 {task_id}: 准备规则生成，银行数据: {len(banks_data)} 个银行")
            
            # 使用规则生成
            training_samples = []
            for i, bank_data in enumerate(banks_data):
                try:
                    samples = generator.generate_samples_for_bank(
                        bank_data["bank_name"], 
                        bank_data["bank_code"],
                        samples_per_bank,
                        llm_name  # Pass llm_name even for rule-based (will be ignored)
                    )
                    
                    # 将生成的样本保存到数据库
                    for sample in samples:
                        qa_pair = QAPair(
                            dataset_id=dataset.id,
                            question=sample["question"],
                            answer=sample["answer"],
                            bank_name=sample["bank_name"],
                            bank_code=sample["bank_code"]
                        )
                        db.add(qa_pair)
                    
                    training_samples.extend(samples)
                    
                    # 更新进度
                    progress_callback(i + 1, len(banks_data), len(training_samples))
                    
                except Exception as e:
                    logger.error(f"生成银行 {bank_data['bank_name']} 的样本失败: {e}")
                    continue
            
            logger.info(f"任务 {task_id}: 规则生成完成，共 {len(training_samples)} 个训练样本")
        
        # 6. 更新数据集状态
        dataset.status = "completed"
        dataset.total_records = len(training_samples)
        dataset.valid_records = len(training_samples)
        
        db.commit()
        logger.info(f"任务 {task_id}: 数据集创建成功，ID: {dataset.id}")
        
        # 更新进度：完成
        generation_progress[task_id].update({
            "status": "completed",
            "progress_percentage": 100,
            "generated_samples": len(training_samples),
            "end_time": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"任务 {task_id} 处理失败: {e}", exc_info=True)
        generation_progress[task_id].update({
            "status": "failed",
            "error": str(e),
            "end_time": datetime.utcnow().isoformat()
        })
        db.rollback()
    finally:
        db.close()
        # 清理临时文件
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)


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


@router.get("/generation-progress/{task_id}")
async def get_generation_progress(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    获取智能生成进度
    
    Args:
        task_id: 任务ID
    
    Returns:
        进度信息
    """
    try:
        if task_id not in generation_progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="任务不存在"
            )
        
        progress_info = generation_progress[task_id]
        
        return {
            "success": True,
            "data": {
                "task_id": task_id,
                "status": progress_info.get("status", "running"),
                "progress_percentage": progress_info.get("progress_percentage", 0),
                "processed_banks": progress_info.get("processed_banks", 0),
                "total_banks": progress_info.get("total_banks", 0),
                "generated_samples": progress_info.get("generated_samples", 0),
                "failed_banks": progress_info.get("failed_banks", 0),
                "eta_minutes": progress_info.get("eta_minutes", None),
                "dataset_id": progress_info.get("dataset_id", None),
                "error": progress_info.get("error", None),
                "start_time": progress_info.get("start_time", None),
                "end_time": progress_info.get("end_time", None)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取生成进度失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取进度失败: {str(e)}"
        )


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
