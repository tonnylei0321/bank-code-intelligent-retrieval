"""
Evaluation API Endpoints - 评估API端点

本模块提供模型评估相关的API端点。

端点列表：
    - POST /api/v1/evaluation/start: 启动模型评估（仅管理员）
    - GET /api/v1/evaluation/{eval_id}: 获取评估详情
    - GET /api/v1/evaluation/{eval_id}/report: 获取评估报告
    - GET /api/v1/evaluation/jobs/{training_job_id}/evaluations: 列出训练任务的所有评估
    - GET /api/v1/evaluation/list: 列出所有评估

评估流程：
    1. 管理员选择已完成的训练任务
    2. 系统加载训练好的模型
    3. 在测试集上运行推理
    4. 计算各项评估指标
    5. 生成详细的评估报告（Markdown格式）

评估指标：
    - 准确性：accuracy, precision, recall, F1 score
    - 分场景准确率：exact/fuzzy/reverse/natural_match_accuracy
    - 响应时间：avg/p95/p99_response_time
    - 鲁棒性：typo_tolerance, abbreviation_accuracy

权限要求：
    - 启动评估：仅管理员
    - 查看评估结果：所有认证用户

使用示例：
    >>> # 启动评估
    >>> response = requests.post(
    ...     "http://localhost:8000/api/v1/evaluation/start",
    ...     json={"training_job_id": 1, "evaluation_type": "model"},
    ...     headers={"Authorization": f"Bearer {admin_token}"}
    ... )
    >>> eval_id = response.json()["id"]
    >>> 
    >>> # 下载评估报告
    >>> response = requests.get(
    ...     f"http://localhost:8000/api/v1/evaluation/{eval_id}/report",
    ...     headers={"Authorization": f"Bearer {token}"}
    ... )
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from loguru import logger

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_admin
from app.models.user import User
from app.models.evaluation import Evaluation
from app.models.training_job import TrainingJob
from app.services.model_evaluator import ModelEvaluator, EvaluationError


router = APIRouter(prefix="/api/v1/evaluation", tags=["evaluation"])


# Request/Response schemas
class EvaluationStartRequest(BaseModel):
    """Request schema for starting evaluation"""
    training_job_id: int = Field(..., description="Training job ID to evaluate")
    evaluation_type: str = Field(default="model", description="Evaluation type: 'model' or 'baseline'")


class EvaluationResponse(BaseModel):
    """Response schema for evaluation"""
    id: int
    training_job_id: int
    evaluation_type: str
    metrics: Dict[str, Any]
    error_cases: Optional[List[Dict[str, str]]]
    report_path: Optional[str]
    evaluated_at: str


class EvaluationListResponse(BaseModel):
    """Response schema for evaluation list"""
    evaluations: List[EvaluationResponse]
    total: int


@router.post("/start", response_model=EvaluationResponse, status_code=status.HTTP_201_CREATED)
async def start_evaluation(
    request: EvaluationStartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start model evaluation
    
    All authenticated users can start evaluations.
    所有已认证用户都可以启动评估。
    
    Args:
        request: Evaluation configuration
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Evaluation results
    
    Raises:
        HTTPException: If training job not found or validation fails
    """
    try:
        # Validate training job exists
        job = db.query(TrainingJob).filter(TrainingJob.id == request.training_job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Training job {request.training_job_id} not found"
            )
        
        # Check if training job is completed
        if job.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Training job {request.training_job_id} is not completed (status: {job.status})"
            )
        
        # Check if model exists
        if not job.model_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Training job {request.training_job_id} has no saved model"
            )
        
        logger.info(f"Starting evaluation for training job {request.training_job_id} by user {current_user.id}")
        
        # Run evaluation
        evaluator = ModelEvaluator(db=db)
        result = evaluator.evaluate_model(
            training_job_id=request.training_job_id,
            evaluation_type=request.evaluation_type
        )
        
        # Load evaluation from database
        evaluation = db.query(Evaluation).filter(Evaluation.id == result["evaluation_id"]).first()
        
        logger.info(f"Evaluation {evaluation.id} completed successfully")
        
        return EvaluationResponse(**evaluation.to_dict())
    
    except HTTPException:
        raise
    except EvaluationError as e:
        logger.error(f"Evaluation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to start evaluation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start evaluation: {str(e)}"
        )


@router.get("/{eval_id}", response_model=EvaluationResponse)
async def get_evaluation(
    eval_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get evaluation details
    
    Args:
        eval_id: Evaluation ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Evaluation details
    
    Raises:
        HTTPException: If evaluation not found
    """
    evaluation = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
    
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation {eval_id} not found"
        )
    
    return EvaluationResponse(**evaluation.to_dict())


@router.get("/{eval_id}/report")
async def get_evaluation_report(
    eval_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get evaluation report
    
    Args:
        eval_id: Evaluation ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Evaluation report file or report content
    
    Raises:
        HTTPException: If evaluation not found or report not generated
    """
    evaluation = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
    
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation {eval_id} not found"
        )
    
    # Generate report if not exists
    if not evaluation.report_path:
        try:
            logger.info(f"Generating report for evaluation {eval_id}")
            evaluator = ModelEvaluator(db=db)
            report_path = evaluator.generate_report(eval_id)
            
            # Refresh evaluation to get updated report_path
            db.refresh(evaluation)
        except EvaluationError as e:
            logger.error(f"Failed to generate report: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate report: {str(e)}"
            )
    
    # Check if report file exists
    import os
    if not os.path.exists(evaluation.report_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report file not found: {evaluation.report_path}"
        )
    
    # Return report file
    return FileResponse(
        path=evaluation.report_path,
        media_type="text/markdown",
        filename=f"evaluation_{eval_id}_report.md"
    )


@router.get("/jobs/{training_job_id}/evaluations", response_model=EvaluationListResponse)
async def list_evaluations_by_job(
    training_job_id: int,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List evaluations for a training job
    
    Args:
        training_job_id: Training job ID
        limit: Maximum number of evaluations to return
        offset: Number of evaluations to skip
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List of evaluations
    """
    # Validate training job exists
    job = db.query(TrainingJob).filter(TrainingJob.id == training_job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training job {training_job_id} not found"
        )
    
    # Query evaluations
    query = db.query(Evaluation).filter(Evaluation.training_job_id == training_job_id)
    
    # Get total count
    total = query.count()
    
    # Get evaluations with pagination
    evaluations = query.order_by(Evaluation.evaluated_at.desc()).limit(limit).offset(offset).all()
    
    return EvaluationListResponse(
        evaluations=[EvaluationResponse(**eval.to_dict()) for eval in evaluations],
        total=total
    )


@router.get("/list", response_model=EvaluationListResponse)
async def list_all_evaluations(
    evaluation_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all evaluations
    
    Args:
        evaluation_type: Filter by evaluation type (optional)
        limit: Maximum number of evaluations to return
        offset: Number of evaluations to skip
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List of evaluations
    """
    query = db.query(Evaluation)
    
    # Apply filters
    if evaluation_type:
        query = query.filter(Evaluation.evaluation_type == evaluation_type)
    
    # Get total count
    total = query.count()
    
    # Get evaluations with pagination
    evaluations = query.order_by(Evaluation.evaluated_at.desc()).limit(limit).offset(offset).all()
    
    return EvaluationListResponse(
        evaluations=[EvaluationResponse(**eval.to_dict()) for eval in evaluations],
        total=total
    )
