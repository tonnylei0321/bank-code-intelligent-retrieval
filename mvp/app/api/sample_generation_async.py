"""
异步样本生成API
支持后台任务和实时进度跟踪
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, List
import uuid
from datetime import datetime
import asyncio
import random

from app.core.deps import get_current_admin_user, get_db
from app.models.user import User
from app.core.logging import logger

router = APIRouter(prefix="/api/v1/sample-generation", tags=["sample-generation-async"])

# 全局任务存储（生产环境应使用Redis）
generation_tasks: Dict[str, Dict] = {}


def split_sample_set(
    db: Session,
    sample_set_id: int,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    random_seed: int = 42
) -> Dict:
    """
    划分样本集中的问答对为训练集/验证集/测试集
    
    Args:
        db: 数据库会话
        sample_set_id: 样本集ID
        train_ratio: 训练集比例
        val_ratio: 验证集比例
        test_ratio: 测试集比例
        random_seed: 随机种子
    
    Returns:
        划分结果字典
    """
    from app.models.qa_pair import QAPair
    
    # 验证比例
    total_ratio = train_ratio + val_ratio + test_ratio
    if abs(total_ratio - 1.0) > 0.001:
        raise ValueError(f"Split ratios must sum to 1.0, got {total_ratio}")
    
    # 获取样本集中的所有问答对
    qa_pairs = db.query(QAPair).filter(
        QAPair.sample_set_id == sample_set_id
    ).all()
    
    if not qa_pairs:
        logger.warning(f"No QA pairs found for sample set {sample_set_id}")
        return {
            "train_count": 0,
            "val_count": 0,
            "test_count": 0
        }
    
    logger.info(f"Splitting sample set {sample_set_id} - Total QA pairs: {len(qa_pairs)}")
    
    # 按问题类型分组
    qa_by_type = {}
    for qa in qa_pairs:
        if qa.question_type not in qa_by_type:
            qa_by_type[qa.question_type] = []
        qa_by_type[qa.question_type].append(qa)
    
    # 设置随机种子
    if random_seed is not None:
        random.seed(random_seed)
    
    # 分别划分每种问题类型
    train_count = 0
    val_count = 0
    test_count = 0
    
    for question_type, type_qa_pairs in qa_by_type.items():
        # 随机打乱
        random.shuffle(type_qa_pairs)
        
        # 计算划分索引
        total = len(type_qa_pairs)
        train_end = int(total * train_ratio)
        val_end = train_end + int(total * val_ratio)
        
        # 分配split_type
        for i, qa in enumerate(type_qa_pairs):
            if i < train_end:
                qa.split_type = "train"
                train_count += 1
            elif i < val_end:
                qa.split_type = "val"
                val_count += 1
            else:
                qa.split_type = "test"
                test_count += 1
    
    # 提交更改
    db.commit()
    
    logger.info(
        f"Sample set split completed - "
        f"Train: {train_count}, Val: {val_count}, Test: {test_count}"
    )
    
    return {
        "train_count": train_count,
        "val_count": val_count,
        "test_count": test_count
    }


@router.post("/start")
async def start_generation_task(
    request: dict,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    启动异步样本生成任务
    
    立即返回任务ID，生成在后台进行
    """
    # 生成任务ID
    task_id = str(uuid.uuid4())
    
    # 创建任务记录
    task = {
        "task_id": task_id,
        "dataset_id": request.get("dataset_id"),
        "status": "pending",
        "progress": 0,
        "current_step": "初始化任务",
        "processed_count": 0,
        "total_count": 0,
        "generated_samples": 0,
        "error_count": 0,
        "start_time": datetime.now().isoformat(),
        "logs": [],
        "user_id": current_user.id,
        "request_params": request
    }
    
    generation_tasks[task_id] = task
    
    # 添加后台任务
    background_tasks.add_task(
        run_generation_task,
        task_id=task_id,
        request=request,
        user_id=current_user.id
    )
    
    logger.info(f"Started generation task {task_id} for user {current_user.username}")
    
    return {
        "task_id": task_id,
        "status": "pending",
        "message": "任务已创建，正在后台执行"
    }


async def run_generation_task(task_id: str, request: dict, user_id: int):
    """
    后台执行样本生成任务
    """
    from app.core.database import SessionLocal
    from app.services.qa_generator import QAGenerator
    from app.services.teacher_model import TeacherModelAPI
    from app.models.sample_set import SampleSet
    
    db = SessionLocal()
    task = generation_tasks[task_id]
    sample_set = None
    
    try:
        # 更新状态为运行中
        task["status"] = "running"
        task["current_step"] = "准备生成环境"
        task["progress"] = 5
        task["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 任务开始执行")
        
        # 获取数据集信息
        from app.models.dataset import Dataset
        dataset = db.query(Dataset).filter(Dataset.id == request["dataset_id"]).first()
        if not dataset:
            raise Exception(f"数据集 {request['dataset_id']} 不存在")
        
        task["total_count"] = dataset.total_records or 0
        task["current_step"] = f"加载数据集: {dataset.filename}"
        task["progress"] = 10
        task["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 数据集: {dataset.filename}, 记录数: {task['total_count']}")
        
        # 创建样本集记录
        sample_set_name = f"{dataset.filename} - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        sample_set = SampleSet(
            name=sample_set_name,
            dataset_id=request["dataset_id"],
            generation_task_id=task_id,
            description=request.get("description", ""),
            generation_config=request,
            status="generating",
            created_by=user_id
        )
        db.add(sample_set)
        db.commit()
        db.refresh(sample_set)
        
        task["sample_set_id"] = sample_set.id
        task["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 创建样本集: {sample_set_name} (ID: {sample_set.id})")
        
        # 创建生成器
        generation_type = request.get("generation_type", "llm")
        
        if generation_type == "rule":
            # 使用本地规则生成器
            teacher_api = TeacherModelAPI(provider="local")
            task["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 使用规则生成器")
        else:
            # 使用LLM生成器
            llm_provider = request.get("llm_provider", "qwen")
            teacher_api = TeacherModelAPI(provider=llm_provider)
            task["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 使用 {llm_provider} LLM生成器")
        
        generator = QAGenerator(db=db, teacher_api=teacher_api)
        
        task["current_step"] = "开始生成样本"
        task["progress"] = 15
        task["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 使用 {request.get('llm_provider', 'qwen')} 生成器")
        
        # 生成QA对
        question_types = request.get("question_types", ["exact", "fuzzy"])
        max_records = request.get("custom_count") if request.get("record_count_strategy") == "custom" else None
        
        # 分批生成，更新进度
        gen_results = await generate_with_progress(
            generator=generator,
            dataset_id=request["dataset_id"],
            sample_set_id=sample_set.id,
            question_types=question_types,
            max_records=max_records,
            task=task
        )
        
        task["current_step"] = "划分数据集"
        task["progress"] = 85
        task["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 成功生成 {gen_results['successful']} 个样本")
        
        # 划分数据集 - 只划分这个样本集的样本
        split_results = split_sample_set(
            db=db,
            sample_set_id=sample_set.id,
            train_ratio=request.get("train_ratio", 0.8),
            val_ratio=request.get("val_ratio", 0.1),
            test_ratio=request.get("test_ratio", 0.1),
            random_seed=42
        )
        
        # 更新样本集统计信息
        sample_set.total_samples = gen_results["successful"]
        sample_set.train_samples = split_results["train_count"]
        sample_set.val_samples = split_results["val_count"]
        sample_set.test_samples = split_results["test_count"]
        sample_set.status = "completed"
        sample_set.completed_at = datetime.now()
        db.commit()
        
        task["current_step"] = "完成"
        task["progress"] = 100
        task["status"] = "completed"
        task["generated_samples"] = gen_results["successful"]
        task["error_count"] = gen_results["failed"]
        task["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 任务完成！")
        task["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 训练集: {split_results['train_count']}, 验证集: {split_results['val_count']}, 测试集: {split_results['test_count']}")
        
        # 保存结果
        task["result"] = {
            "sample_set_id": sample_set.id,
            "total_generated": gen_results["successful"],
            "train_count": split_results["train_count"],
            "val_count": split_results["val_count"],
            "test_count": split_results["test_count"],
            "failed_count": gen_results["failed"]
        }
        
    except Exception as e:
        logger.exception(f"Generation task {task_id} failed")
        task["status"] = "failed"
        task["current_step"] = "失败"
        task["error_message"] = str(e)
        task["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 错误: {str(e)}")
        
        # 更新样本集状态为失败
        if sample_set:
            sample_set.status = "failed"
            db.commit()
        
    finally:
        db.close()


async def generate_with_progress(generator, dataset_id: int, sample_set_id: int, question_types: List[str], max_records: int, task: dict):
    """
    带进度更新的生成函数
    """
    from app.models.bank_code import BankCode
    from app.models.qa_pair import QAPair
    
    # 获取要处理的记录
    query = generator.db.query(BankCode).filter(
        BankCode.dataset_id == dataset_id,
        BankCode.is_valid == 1
    )
    if max_records:
        query = query.limit(max_records)
    
    records = query.all()
    total = len(records)
    
    successful = 0
    failed = 0
    failed_records = []
    
    # 分批处理
    batch_size = 10
    for i in range(0, total, batch_size):
        batch = records[i:i+batch_size]
        
        for record in batch:
            try:
                # 为每条记录生成QA对
                for q_type in question_types:
                    # 使用teacher_api生成问答对
                    qa_result = generator.teacher_api.generate_qa_pair(record, q_type)
                    
                    if qa_result:
                        question, answer = qa_result
                        
                        # 创建问答对记录
                        qa_pair = QAPair(
                            dataset_id=dataset_id,
                            sample_set_id=sample_set_id,
                            source_record_id=record.id,
                            question=question,
                            answer=answer,
                            question_type=q_type,
                            split_type="train",  # 默认为训练集，后续会重新划分
                            generated_at=datetime.now()
                        )
                        
                        generator.db.add(qa_pair)
                        successful += 1
                    else:
                        failed += 1
                        failed_records.append({
                            "record_id": record.id,
                            "bank_name": record.bank_name,
                            "question_type": q_type,
                            "reason": "生成失败"
                        })
                        
            except Exception as e:
                failed += 1
                failed_records.append({
                    "record_id": record.id,
                    "bank_name": record.bank_name,
                    "question_type": q_type,
                    "reason": str(e)
                })
                logger.error(f"Failed to generate QA for record {record.id}: {e}")
        
        # 提交批次
        try:
            generator.db.commit()
        except Exception as e:
            generator.db.rollback()
            logger.error(f"批次提交失败: {e}")
        
        # 更新进度
        processed = min(i + batch_size, total)
        progress = 15 + int((processed / total) * 70)  # 15-85%
        
        task["processed_count"] = processed
        task["generated_samples"] = successful
        task["error_count"] = failed
        task["progress"] = progress
        task["current_step"] = f"生成中 ({processed}/{total})"
        task["logs"].append(
            f"[{datetime.now().strftime('%H:%M:%S')}] "
            f"已处理 {processed}/{total} 条记录，生成 {successful} 个样本"
        )
        
        # 让出控制权，允许其他任务执行
        await asyncio.sleep(0.1)
    
    return {
        "successful": successful,
        "failed": failed,
        "failed_records": failed_records
    }


@router.get("/status/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """
    获取任务状态和进度
    """
    if task_id not in generation_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = generation_tasks[task_id]
    
    # 只返回最近的日志
    recent_logs = task["logs"][-50:] if len(task["logs"]) > 50 else task["logs"]
    
    return {
        "task_id": task_id,
        "status": task["status"],
        "progress": task["progress"],
        "current_step": task["current_step"],
        "processed_count": task["processed_count"],
        "total_count": task["total_count"],
        "generated_samples": task["generated_samples"],
        "error_count": task["error_count"],
        "start_time": task["start_time"],
        "logs": recent_logs,
        "result": task.get("result"),
        "error_message": task.get("error_message")
    }


@router.get("/tasks")
async def list_tasks(
    current_user: User = Depends(get_current_admin_user)
):
    """
    列出所有任务
    """
    # 只返回当前用户的任务
    user_tasks = [
        {
            "task_id": task_id,
            "dataset_id": task["dataset_id"],
            "status": task["status"],
            "progress": task["progress"],
            "generated_samples": task["generated_samples"],
            "start_time": task["start_time"]
        }
        for task_id, task in generation_tasks.items()
        if task["user_id"] == current_user.id
    ]
    
    # 按时间倒序
    user_tasks.sort(key=lambda x: x["start_time"], reverse=True)
    
    return {"tasks": user_tasks}


@router.delete("/tasks/{task_id}")
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """
    取消任务
    """
    if task_id not in generation_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = generation_tasks[task_id]
    
    if task["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作此任务")
    
    if task["status"] in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="任务已结束，无法取消")
    
    task["status"] = "cancelled"
    task["current_step"] = "已取消"
    task["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 任务被用户取消")
    
    return {"message": "任务已取消"}
