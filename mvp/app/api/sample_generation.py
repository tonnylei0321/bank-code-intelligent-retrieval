"""
样本数据生成API

提供样本数据生成的完整功能，包括：
- 多种挑选策略（按银行、省行、支行）
- 灵活的记录数控制
- 多种LLM生成策略
- 异步任务处理和进度监控
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
import asyncio
import uuid
from datetime import datetime

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.dataset import Dataset
from app.services.sample_generation_service import SampleGenerationService, SampleGenerationTask

router = APIRouter(prefix="/api/sample-generation", tags=["样本生成"])

# 请求模型
class SampleSelectionStrategy(str, Enum):
    """样本挑选策略"""
    BY_BANK = "by_bank"           # 按银行挑选
    BY_PROVINCE = "by_province"   # 按省行挑选  
    BY_BRANCH = "by_branch"       # 按支行挑选
    BY_REGION = "by_region"       # 按地区挑选
    RANDOM = "random"             # 随机挑选
    ALL = "all"                   # 全部数据

class RecordCountStrategy(str, Enum):
    """记录数策略"""
    ALL = "all"                   # 全部记录
    CUSTOM = "custom"             # 自定义数量
    PERCENTAGE = "percentage"     # 按百分比

class LLMGenerationStrategy(str, Enum):
    """LLM生成策略"""
    NATURAL_LANGUAGE = "natural_language"     # 自然语言问答
    STRUCTURED_QA = "structured_qa"           # 结构化问答
    MULTI_TURN = "multi_turn"                 # 多轮对话
    SCENARIO_BASED = "scenario_based"         # 场景化问答
    KNOWLEDGE_GRAPH = "knowledge_graph"       # 知识图谱问答
    COMPARATIVE = "comparative"               # 对比分析问答
    CONTEXTUAL = "contextual"                 # 上下文关联问答

class SampleGenerationRequest(BaseModel):
    """样本生成请求"""
    dataset_id: int = Field(..., description="数据集ID")
    
    # 样本挑选策略
    selection_strategy: SampleSelectionStrategy = Field(..., description="样本挑选策略")
    selection_filters: Dict[str, Any] = Field(default={}, description="挑选过滤条件")
    
    # 记录数控制
    record_count_strategy: RecordCountStrategy = Field(..., description="记录数策略")
    custom_count: Optional[int] = Field(None, description="自定义记录数")
    percentage: Optional[float] = Field(None, description="百分比(0-100)")
    
    # LLM生成策略
    llm_strategies: List[LLMGenerationStrategy] = Field(..., description="LLM生成策略列表")
    questions_per_record: int = Field(default=3, description="每条记录生成的问题数")
    
    # 生成配置
    model_type: str = Field(default="local", description="使用的模型类型")
    temperature: float = Field(default=0.7, description="生成温度")
    max_tokens: int = Field(default=512, description="最大token数")
    
    # 任务配置
    task_name: str = Field(..., description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")

class SampleGenerationResponse(BaseModel):
    """样本生成响应"""
    task_id: str
    status: str
    message: str
    estimated_total: int
    created_at: str

class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    status: str
    progress: float
    current_step: str
    processed_count: int
    total_count: int
    generated_samples: int
    error_count: int
    start_time: str
    estimated_completion: Optional[str]
    logs: List[str]

# 全局任务管理器
task_manager = {}

@router.post("/start", response_model=SampleGenerationResponse)
async def start_sample_generation(
    request: SampleGenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """启动样本生成任务"""
    try:
        # 验证数据集
        dataset = db.query(Dataset).filter(Dataset.id == request.dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="数据集不存在")
        
        # 创建任务ID
        task_id = str(uuid.uuid4())
        
        # 初始化样本生成服务
        service = SampleGenerationService(db)
        
        # 估算总数
        estimated_total = await service.estimate_generation_count(request)
        
        # 创建任务记录
        task = SampleGenerationTask(
            task_id=task_id,
            user_id=current_user.id,
            dataset_id=request.dataset_id,
            request_config=request.dict(),
            status="pending",
            estimated_total=estimated_total
        )
        
        # 保存到全局任务管理器
        task_manager[task_id] = task
        
        # 启动后台任务
        background_tasks.add_task(
            run_sample_generation_task,
            task_id,
            request,
            db,
            current_user.id
        )
        
        return SampleGenerationResponse(
            task_id=task_id,
            status="pending",
            message="样本生成任务已启动",
            estimated_total=estimated_total,
            created_at=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动任务失败: {str(e)}")

@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """获取任务状态"""
    if task_id not in task_manager:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = task_manager[task_id]
    
    return TaskStatusResponse(
        task_id=task_id,
        status=task.status,
        progress=task.progress,
        current_step=task.current_step,
        processed_count=task.processed_count,
        total_count=task.total_count,
        generated_samples=task.generated_samples,
        error_count=task.error_count,
        start_time=task.start_time.isoformat() if task.start_time else "",
        estimated_completion=task.estimated_completion.isoformat() if task.estimated_completion else None,
        logs=task.logs[-20:]  # 返回最近20条日志
    )

@router.get("/tasks")
async def list_tasks(
    current_user: User = Depends(get_current_user)
):
    """获取用户的所有任务"""
    user_tasks = []
    for task_id, task in task_manager.items():
        if task.user_id == current_user.id:
            user_tasks.append({
                "task_id": task_id,
                "dataset_id": task.dataset_id,
                "status": task.status,
                "progress": task.progress,
                "created_at": task.start_time.isoformat() if task.start_time else "",
                "generated_samples": task.generated_samples
            })
    
    return {"tasks": user_tasks}

@router.delete("/tasks/{task_id}")
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """取消任务"""
    if task_id not in task_manager:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = task_manager[task_id]
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限操作此任务")
    
    if task.status in ["running", "pending"]:
        task.status = "cancelled"
        task.add_log("任务已被用户取消")
    
    return {"message": "任务已取消"}

@router.get("/strategies")
async def get_generation_strategies():
    """获取所有可用的生成策略"""
    return {
        "selection_strategies": [
            {"value": "by_bank", "label": "按银行挑选", "description": "根据银行名称分组挑选样本"},
            {"value": "by_province", "label": "按省行挑选", "description": "根据省份分组挑选样本"},
            {"value": "by_branch", "label": "按支行挑选", "description": "根据支行分组挑选样本"},
            {"value": "by_region", "label": "按地区挑选", "description": "根据地区分组挑选样本"},
            {"value": "random", "label": "随机挑选", "description": "随机选择样本数据"},
            {"value": "all", "label": "全部数据", "description": "使用所有可用数据"}
        ],
        "record_count_strategies": [
            {"value": "all", "label": "全部记录", "description": "使用所有符合条件的记录"},
            {"value": "custom", "label": "自定义数量", "description": "指定具体的记录数量"},
            {"value": "percentage", "label": "按百分比", "description": "按百分比选择记录"}
        ],
        "llm_strategies": [
            {"value": "natural_language", "label": "自然语言问答", "description": "生成自然流畅的问答对"},
            {"value": "structured_qa", "label": "结构化问答", "description": "生成格式化的结构化问答"},
            {"value": "multi_turn", "label": "多轮对话", "description": "生成多轮对话样本"},
            {"value": "scenario_based", "label": "场景化问答", "description": "基于具体场景的问答"},
            {"value": "knowledge_graph", "label": "知识图谱问答", "description": "基于知识关系的问答"},
            {"value": "comparative", "label": "对比分析问答", "description": "生成对比分析类问答"},
            {"value": "contextual", "label": "上下文关联问答", "description": "考虑上下文关系的问答"}
        ]
    }

async def run_sample_generation_task(
    task_id: str,
    request: SampleGenerationRequest,
    db: Session,
    user_id: int
):
    """运行样本生成任务（后台任务）"""
    task = task_manager[task_id]
    
    try:
        task.status = "running"
        task.start_time = datetime.now()
        task.add_log("开始样本生成任务")
        
        # 初始化服务
        service = SampleGenerationService(db)
        
        # 执行生成
        async for progress_update in service.generate_samples(request, task):
            # 更新任务状态
            task.progress = progress_update.get("progress", 0)
            task.current_step = progress_update.get("step", "")
            task.processed_count = progress_update.get("processed", 0)
            task.generated_samples = progress_update.get("generated", 0)
            task.error_count = progress_update.get("errors", 0)
            
            if progress_update.get("log"):
                task.add_log(progress_update["log"])
        
        task.status = "completed"
        task.progress = 100.0
        task.add_log("样本生成任务完成")
        
    except Exception as e:
        task.status = "failed"
        task.add_log(f"任务失败: {str(e)}")
        
    finally:
        task.end_time = datetime.now()