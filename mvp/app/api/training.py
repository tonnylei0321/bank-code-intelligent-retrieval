"""
Training API Endpoints - 训练任务API端点

本模块提供模型训练相关的API端点。

端点列表：
    - POST /api/v1/training/start: 启动新的训练任务（仅管理员）
    - POST /api/v1/training/optimize: 获取智能优化的训练参数
    - GET /api/v1/training/{job_id}: 获取训练任务详情
    - POST /api/v1/training/{job_id}/stop: 停止运行中的训练任务（仅管理员）
    - GET /api/v1/training/jobs: 列出训练任务（支持筛选和分页）

训练流程：
    1. 管理员提交训练配置（数据集、模型参数、LoRA参数）
    2. 系统创建训练任务记录
    3. 启动训练进程（使用ModelTrainer服务）
    4. 实时更新训练进度和指标
    5. 训练完成后保存模型权重

权限要求：
    - 启动训练：仅管理员
    - 停止训练：仅管理员
    - 查看训练任务：所有认证用户

使用示例：
    >>> # 获取优化参数
    >>> response = requests.post(
    ...     "http://localhost:8000/api/v1/training/optimize",
    ...     json={
    ...         "dataset_id": 1,
    ...         "model_name": "Qwen/Qwen2.5-0.5B",
    ...         "target_training_time_hours": 24.0
    ...     },
    ...     headers={"Authorization": f"Bearer {token}"}
    ... )
    >>> optimized_params = response.json()
    >>> 
    >>> # 启动训练（使用优化参数）
    >>> response = requests.post(
    ...     "http://localhost:8000/api/v1/training/start",
    ...     json={
    ...         "dataset_id": 1,
    ...         "model_name": "Qwen/Qwen2.5-0.5B",
    ...         "use_optimized_params": True,
    ...         "target_training_time_hours": 24.0
    ...     },
    ...     headers={"Authorization": f"Bearer {admin_token}"}
    ... )
    >>> job_id = response.json()["id"]
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from loguru import logger

from app.core.database import get_db
from app.core.deps import get_current_user, get_current_admin_user
from app.core.permissions import require_admin
from app.models.user import User
from app.models.training_job import TrainingJob
from app.models.dataset import Dataset
from app.services.model_trainer import ModelTrainer, TrainingError
from app.services.training_optimizer import optimize_training_parameters_for_job
from app.services.training_queue_manager import TrainingQueueManager
from app.services.training_monitor import TrainingMonitor
from app.services.training_recovery import TrainingRecoveryService


router = APIRouter(prefix="/api/v1/training", tags=["training"])


# Request/Response schemas
class TrainingOptimizeRequest(BaseModel):
    """Request schema for optimizing training parameters"""
    dataset_id: int = Field(..., description="Dataset ID to optimize for")
    model_name: str = Field(default="Qwen/Qwen2.5-0.5B", description="Base model name")
    target_training_time_hours: float = Field(default=24.0, gt=0, le=168, description="Target training time in hours")


class TrainingOptimizeResponse(BaseModel):
    """Response schema for optimized training parameters"""
    # 基础参数
    epochs: int
    batch_size: int
    learning_rate: float
    
    # LoRA参数
    lora_r: int
    lora_alpha: int
    lora_dropout: float
    
    # 优化参数
    gradient_accumulation_steps: int
    warmup_steps: int
    weight_decay: float
    max_grad_norm: float
    
    # 预估信息
    estimated_training_time_hours: float
    estimated_memory_usage_gb: float
    
    # 优化说明
    optimization_notes: List[str]


class TrainingStartRequest(BaseModel):
    """Request schema for starting training"""
    dataset_id: int = Field(..., description="Dataset ID to train on")
    model_name: str = Field(default="Qwen/Qwen2.5-0.5B", description="Base model name")
    
    # 智能优化选项
    use_optimized_params: bool = Field(default=True, description="Use intelligent parameter optimization")
    target_training_time_hours: float = Field(default=24.0, gt=0, le=168, description="Target training time in hours")
    
    # 手动参数（当use_optimized_params=False时使用）
    epochs: Optional[int] = Field(default=None, ge=1, le=20, description="Number of training epochs")
    batch_size: Optional[int] = Field(default=None, ge=1, le=64, description="Training batch size")
    learning_rate: Optional[float] = Field(default=None, gt=0, description="Learning rate")
    lora_r: Optional[int] = Field(default=None, ge=1, le=128, description="LoRA rank")
    lora_alpha: Optional[int] = Field(default=None, ge=1, le=256, description="LoRA alpha")
    lora_dropout: Optional[float] = Field(default=None, ge=0, le=0.5, description="LoRA dropout")


class TrainingJobResponse(BaseModel):
    """Response schema for training job"""
    id: int
    dataset_id: int
    created_by: int
    status: str
    model_name: str
    epochs: int
    batch_size: int
    learning_rate: float
    lora_r: int
    lora_alpha: int
    lora_dropout: float
    current_epoch: int
    total_steps: int
    current_step: int
    progress_percentage: float
    train_loss: Optional[float]
    val_loss: Optional[float]
    val_accuracy: Optional[float]
    model_path: Optional[str]
    error_message: Optional[str]
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    updated_at: str


class TrainingJobListResponse(BaseModel):
    """Response schema for training job list"""
    jobs: List[TrainingJobResponse]
    total: int


class DeleteResponse(BaseModel):
    """Response schema for delete operations"""
    success: bool
    message: str


class BatchDeleteRequest(BaseModel):
    """Request schema for batch delete operations"""
    job_ids: List[int] = Field(..., description="List of training job IDs to delete")


class BatchDeleteResponse(BaseModel):
    """Response schema for batch delete operations"""
    success: bool
    message: str
    deleted_jobs: List[int]
    deleted_count: int


@router.post("/optimize", response_model=TrainingOptimizeResponse)
async def optimize_training_parameters(
    request: TrainingOptimizeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get optimized training parameters for a dataset and model
    
    This endpoint analyzes the dataset and hardware constraints to recommend
    optimal training parameters for the best balance of training time, 
    memory usage, and model performance.
    
    Args:
        request: Optimization request with dataset_id, model_name, and target time
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Optimized training parameters with explanations
    
    Raises:
        HTTPException: If dataset not found or optimization fails
    """
    try:
        # Validate dataset exists
        dataset = db.query(Dataset).filter(Dataset.id == request.dataset_id).first()
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset {request.dataset_id} not found"
            )
        
        # Check if dataset has QA pairs
        from app.models.qa_pair import QAPair
        qa_count = db.query(QAPair).filter(
            QAPair.dataset_id == request.dataset_id
        ).count()
        
        if qa_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dataset {request.dataset_id} has no QA pairs. Generate QA pairs first."
            )
        
        logger.info(f"Optimizing training parameters for dataset {request.dataset_id}, model {request.model_name}")
        
        # Get optimized parameters
        optimized_params = optimize_training_parameters_for_job(
            db=db,
            model_name=request.model_name,
            dataset_id=request.dataset_id,
            target_hours=request.target_training_time_hours
        )
        
        logger.info(f"Parameter optimization completed for user {current_user.id}")
        
        return TrainingOptimizeResponse(**optimized_params)
        
    except Exception as e:
        logger.error(f"Parameter optimization failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Parameter optimization failed: {str(e)}"
        )


@router.post("/start", response_model=TrainingJobResponse, status_code=status.HTTP_201_CREATED)
async def start_training(
    request: TrainingStartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start a new training job with intelligent parameter optimization
    
    All authenticated users can start training jobs.
    所有已认证用户都可以启动训练任务。
    
    Args:
        request: Training configuration
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Created training job
    
    Raises:
        HTTPException: If dataset not found or validation fails
    """
    try:
        # Validate dataset exists
        dataset = db.query(Dataset).filter(Dataset.id == request.dataset_id).first()
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset {request.dataset_id} not found"
            )
        
        # Check if dataset has QA pairs
        from app.models.qa_pair import QAPair
        qa_count = db.query(QAPair).filter(
            QAPair.dataset_id == request.dataset_id
        ).count()
        
        if qa_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dataset {request.dataset_id} has no QA pairs. Generate QA pairs first."
            )
        
        # Determine training parameters
        if request.use_optimized_params:
            logger.info(f"Using intelligent parameter optimization for dataset {request.dataset_id}")
            
            # Get optimized parameters
            optimized_params = optimize_training_parameters_for_job(
                db=db,
                model_name=request.model_name,
                dataset_id=request.dataset_id,
                target_hours=request.target_training_time_hours
            )
            
            # Use optimized parameters
            epochs = optimized_params["epochs"]
            batch_size = optimized_params["batch_size"]
            learning_rate = optimized_params["learning_rate"]
            lora_r = optimized_params["lora_r"]
            lora_alpha = optimized_params["lora_alpha"]
            lora_dropout = optimized_params["lora_dropout"]
            
            logger.info(f"Optimized parameters: epochs={epochs}, batch_size={batch_size}, lr={learning_rate}")
            
        else:
            logger.info("Using manual parameters")
            
            # Use manual parameters with defaults
            epochs = request.epochs or 3
            batch_size = request.batch_size or 8
            learning_rate = request.learning_rate or 2e-4
            lora_r = request.lora_r or 16
            lora_alpha = request.lora_alpha or 32
            lora_dropout = request.lora_dropout or 0.05
        
        # Create training job
        job = TrainingJob(
            dataset_id=request.dataset_id,
            created_by=current_user.id,
            status="pending",
            model_name=request.model_name,
            epochs=epochs,
            batch_size=batch_size,
            learning_rate=learning_rate,
            lora_r=lora_r,
            lora_alpha=lora_alpha,
            lora_dropout=lora_dropout
        )
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        logger.info(f"Training job {job.id} created by user {current_user.id} with {'optimized' if request.use_optimized_params else 'manual'} parameters")
        
        # Start training in background thread
        import threading
        from app.core.database import SessionLocal
        
        def train_in_background(job_id: int):
            """Run training in a separate thread with its own database session"""
            db_thread = SessionLocal()
            try:
                trainer = ModelTrainer(db=db_thread)
                trainer.train_model(job_id)
            except TrainingError as e:
                logger.error(f"Training failed for job {job_id}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in training job {job_id}: {e}")
            finally:
                db_thread.close()
        
        # Start training thread
        training_thread = threading.Thread(
            target=train_in_background,
            args=(job.id,),
            daemon=True
        )
        training_thread.start()
        logger.info(f"Training thread started for job {job.id}")
        
        return TrainingJobResponse(**job.to_dict())
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start training: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start training: {str(e)}"
        )


@router.get("/jobs", response_model=TrainingJobListResponse)
async def list_training_jobs(
    dataset_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List training jobs
    
    Args:
        dataset_id: Filter by dataset ID (optional)
        status: Filter by status (optional)
        limit: Maximum number of jobs to return
        offset: Number of jobs to skip
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List of training jobs
    """
    query = db.query(TrainingJob)
    
    # Apply filters
    if dataset_id:
        query = query.filter(TrainingJob.dataset_id == dataset_id)
    
    if status:
        query = query.filter(TrainingJob.status == status)
    
    # Get total count
    total = query.count()
    
    # Get jobs with pagination
    jobs = query.order_by(TrainingJob.created_at.desc()).limit(limit).offset(offset).all()
    
    return TrainingJobListResponse(
        jobs=[TrainingJobResponse(**job.to_dict()) for job in jobs],
        total=total
    )


@router.get("/{job_id}", response_model=TrainingJobResponse)
async def get_training_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get training job details
    
    Args:
        job_id: Training job ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Training job details
    
    Raises:
        HTTPException: If job not found
    """
    job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training job {job_id} not found"
        )
    
    return TrainingJobResponse(**job.to_dict())


@router.post("/{job_id}/stop", response_model=dict)
async def stop_training_job(
    job_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Stop a running training job
    
    Only administrators can stop training jobs.
    
    Args:
        job_id: Training job ID
        current_user: Current authenticated admin user
        db: Database session
    
    Returns:
        Stop result
    
    Raises:
        HTTPException: If job not found or not running
    """
    try:
        trainer = ModelTrainer(db=db)
        result = trainer.stop_training(job_id)
        
        logger.info(f"Training job {job_id} stopped by user {current_user.id}")
        
        return result
    
    except TrainingError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to stop training job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop training: {str(e)}"
        )


@router.post("/batch/delete")
async def delete_training_jobs_batch_post(
    request: BatchDeleteRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Delete multiple training jobs (POST method)
    
    Only administrators can delete training jobs.
    Only completed, failed, or stopped jobs can be deleted.
    
    Args:
        request: Batch delete request containing job IDs
        current_user: Current authenticated admin user
        db: Database session
    
    Returns:
        Batch delete result
    
    Raises:
        HTTPException: If any job cannot be deleted
    """
    try:
        job_ids = request.job_ids
        
        if not job_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No job IDs provided"
            )
        
        # Get all jobs
        jobs = db.query(TrainingJob).filter(TrainingJob.id.in_(job_ids)).all()
        
        if len(jobs) != len(job_ids):
            found_ids = {job.id for job in jobs}
            missing_ids = set(job_ids) - found_ids
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Training jobs not found: {list(missing_ids)}"
            )
        
        # Check if all jobs can be deleted
        running_jobs = [job.id for job in jobs if job.status in ['running', 'pending']]
        if running_jobs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete running or pending training jobs: {running_jobs}. Stop them first."
            )
        
        deleted_count = 0
        deleted_jobs = []
        
        for job in jobs:
            try:
                # Delete associated model files if they exist
                if job.model_path:
                    import shutil
                    from pathlib import Path
                    model_path = Path(job.model_path)
                    if model_path.exists():
                        try:
                            if model_path.is_dir():
                                shutil.rmtree(model_path)
                            else:
                                model_path.unlink()
                            logger.info(f"Deleted model files for job {job.id}: {model_path}")
                        except Exception as e:
                            logger.warning(f"Failed to delete model files for job {job.id}: {e}")
                
                # Delete the job from database
                db.delete(job)
                deleted_jobs.append(job.id)
                deleted_count += 1
                
            except Exception as e:
                logger.error(f"Failed to delete training job {job.id}: {e}")
                # Continue with other jobs
        
        db.commit()
        
        logger.info(f"Batch deleted {deleted_count} training jobs by user {current_user.id}: {deleted_jobs}")
        
        return {
            "success": True,
            "message": f"Successfully deleted {deleted_count} training jobs",
            "deleted_jobs": deleted_jobs,
            "deleted_count": deleted_count
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to batch delete training jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch delete training jobs: {str(e)}"
        )


@router.get("/test")
async def test_endpoint():
    """Test endpoint"""
    return {"message": "Test successful"}


@router.get("/health")
async def health_check():
    """Health check endpoint - no auth required"""
    return {"status": "healthy", "service": "training"}


@router.post("/{job_id}/delete")
async def delete_training_job_alt(
    job_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Delete a training job (alternative endpoint)
    
    Only administrators can delete training jobs.
    Only completed, failed, or stopped jobs can be deleted.
    
    Args:
        job_id: Training job ID
        current_user: Current authenticated admin user
        db: Database session
    
    Returns:
        Delete result
    
    Raises:
        HTTPException: If job not found or cannot be deleted
    """
    try:
        # Get the job
        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Training job {job_id} not found"
            )
        
        # Check if job can be deleted (not running)
        if job.status in ['running', 'pending']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete running or pending training job. Stop it first."
            )
        
        # Delete associated model files if they exist
        if job.model_path:
            import shutil
            from pathlib import Path
            model_path = Path(job.model_path)
            if model_path.exists():
                try:
                    if model_path.is_dir():
                        shutil.rmtree(model_path)
                    else:
                        model_path.unlink()
                    logger.info(f"Deleted model files for job {job_id}: {model_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete model files for job {job_id}: {e}")
        
        # Delete the job from database
        db.delete(job)
        db.commit()
        
        logger.info(f"Training job {job_id} deleted by user {current_user.id}")
        
        return {
            "success": True,
            "message": f"Training job {job_id} deleted successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete training job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete training job: {str(e)}"
        )


@router.delete("/{job_id}")
async def delete_training_job(
    job_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Delete a training job
    
    Only administrators can delete training jobs.
    Only completed, failed, or stopped jobs can be deleted.
    
    Args:
        job_id: Training job ID
        current_user: Current authenticated admin user
        db: Database session
    
    Returns:
        Delete result
    
    Raises:
        HTTPException: If job not found or cannot be deleted
    """
    try:
        # Get the job
        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Training job {job_id} not found"
            )
        
        # Check if job can be deleted (not running)
        if job.status in ['running', 'pending']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete running or pending training job. Stop it first."
            )
        
        # Delete associated model files if they exist
        if job.model_path:
            import shutil
            from pathlib import Path
            model_path = Path(job.model_path)
            if model_path.exists():
                try:
                    if model_path.is_dir():
                        shutil.rmtree(model_path)
                    else:
                        model_path.unlink()
                    logger.info(f"Deleted model files for job {job_id}: {model_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete model files for job {job_id}: {e}")
        
        # Delete the job from database
        db.delete(job)
        db.commit()
        
        logger.info(f"Training job {job_id} deleted by user {current_user.id}")
        
        return {
            "success": True,
            "message": f"Training job {job_id} deleted successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete training job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete training job: {str(e)}"
        )


@router.post("/batch/delete")
async def delete_training_jobs_batch_alt(
    request: BatchDeleteRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Delete multiple training jobs (alternative endpoint)
    
    Only administrators can delete training jobs.
    Only completed, failed, or stopped jobs can be deleted.
    
    Args:
        request: Batch delete request containing job IDs
        current_user: Current authenticated admin user
        db: Database session
    
    Returns:
        Batch delete result
    
    Raises:
        HTTPException: If any job cannot be deleted
    """
    try:
        job_ids = request.job_ids
        
        if not job_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No job IDs provided"
            )
        
        # Get all jobs
        jobs = db.query(TrainingJob).filter(TrainingJob.id.in_(job_ids)).all()
        
        if len(jobs) != len(job_ids):
            found_ids = {job.id for job in jobs}
            missing_ids = set(job_ids) - found_ids
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Training jobs not found: {list(missing_ids)}"
            )
        
        # Check if all jobs can be deleted
        running_jobs = [job.id for job in jobs if job.status in ['running', 'pending']]
        if running_jobs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete running or pending training jobs: {running_jobs}. Stop them first."
            )
        
        deleted_count = 0
        deleted_jobs = []
        
        for job in jobs:
            try:
                # Delete associated model files if they exist
                if job.model_path:
                    import shutil
                    from pathlib import Path
                    model_path = Path(job.model_path)
                    if model_path.exists():
                        try:
                            if model_path.is_dir():
                                shutil.rmtree(model_path)
                            else:
                                model_path.unlink()
                            logger.info(f"Deleted model files for job {job.id}: {model_path}")
                        except Exception as e:
                            logger.warning(f"Failed to delete model files for job {job.id}: {e}")
                
                # Delete the job from database
                db.delete(job)
                deleted_jobs.append(job.id)
                deleted_count += 1
                
            except Exception as e:
                logger.error(f"Failed to delete training job {job.id}: {e}")
                # Continue with other jobs
        
        db.commit()
        
        logger.info(f"Batch deleted {deleted_count} training jobs by user {current_user.id}: {deleted_jobs}")
        
        return {
            "success": True,
            "message": f"Successfully deleted {deleted_count} training jobs",
            "deleted_jobs": deleted_jobs,
            "deleted_count": deleted_count
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to batch delete training jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch delete training jobs: {str(e)}"
        )


@router.delete("/batch")
async def delete_training_jobs_batch(
    request: BatchDeleteRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Delete multiple training jobs
    
    Only administrators can delete training jobs.
    Only completed, failed, or stopped jobs can be deleted.
    
    Args:
        request: Batch delete request containing job IDs
        current_user: Current authenticated admin user
        db: Database session
    
    Returns:
        Batch delete result
    
    Raises:
        HTTPException: If any job cannot be deleted
    """
    try:
        job_ids = request.job_ids
        
        if not job_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No job IDs provided"
            )
        
        # Get all jobs
        jobs = db.query(TrainingJob).filter(TrainingJob.id.in_(job_ids)).all()
        
        if len(jobs) != len(job_ids):
            found_ids = {job.id for job in jobs}
            missing_ids = set(job_ids) - found_ids
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Training jobs not found: {list(missing_ids)}"
            )
        
        # Check if all jobs can be deleted
        running_jobs = [job.id for job in jobs if job.status in ['running', 'pending']]
        if running_jobs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete running or pending training jobs: {running_jobs}. Stop them first."
            )
        
        deleted_count = 0
        deleted_jobs = []
        
        for job in jobs:
            try:
                # Delete associated model files if they exist
                if job.model_path:
                    import shutil
                    from pathlib import Path
                    model_path = Path(job.model_path)
                    if model_path.exists():
                        try:
                            if model_path.is_dir():
                                shutil.rmtree(model_path)
                            else:
                                model_path.unlink()
                            logger.info(f"Deleted model files for job {job.id}: {model_path}")
                        except Exception as e:
                            logger.warning(f"Failed to delete model files for job {job.id}: {e}")
                
                # Delete the job from database
                db.delete(job)
                deleted_jobs.append(job.id)
                deleted_count += 1
                
            except Exception as e:
                logger.error(f"Failed to delete training job {job.id}: {e}")
                # Continue with other jobs
        
        db.commit()
        
        logger.info(f"Batch deleted {deleted_count} training jobs by user {current_user.id}: {deleted_jobs}")
        
        return {
            "success": True,
            "message": f"Successfully deleted {deleted_count} training jobs",
            "deleted_jobs": deleted_jobs,
            "deleted_count": deleted_count
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to batch delete training jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch delete training jobs: {str(e)}"
        )

# 全局队列管理器和监控服务实例
_queue_manager = None
_training_monitor = None
_recovery_service = None

def get_queue_manager(db: Session = Depends(get_db)) -> TrainingQueueManager:
    """获取训练队列管理器实例"""
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = TrainingQueueManager(db, max_concurrent=2)
        # 启动队列处理
        _queue_manager.start_processing()
    return _queue_manager

def get_training_monitor(db: Session = Depends(get_db)) -> TrainingMonitor:
    """获取训练监控服务实例"""
    global _training_monitor
    if _training_monitor is None:
        _training_monitor = TrainingMonitor(db)
        # 启动监控（异步）
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(_training_monitor.start_monitoring())
        except RuntimeError:
            # 如果没有运行的事件循环，稍后启动
            pass
    return _training_monitor

def get_recovery_service(db: Session = Depends(get_db)) -> TrainingRecoveryService:
    """获取训练恢复服务实例"""
    global _recovery_service
    if _recovery_service is None:
        _recovery_service = TrainingRecoveryService(db)
    return _recovery_service


# 队列管理端点
@router.post("/queue/enqueue/{job_id}")
async def enqueue_training_job(
    job_id: int,
    priority: str = "medium",
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    queue_manager: TrainingQueueManager = Depends(get_queue_manager)
):
    """
    将训练任务添加到队列
    
    Args:
        job_id: 训练任务ID
        priority: 任务优先级 ("high", "medium", "low")
        current_user: 当前管理员用户
        db: 数据库会话
        queue_manager: 队列管理器
    
    Returns:
        队列操作结果
    """
    try:
        success = queue_manager.enqueue_training_job(job_id, priority)
        
        if success:
            return {
                "success": True,
                "message": f"Job {job_id} added to queue with {priority} priority",
                "job_id": job_id,
                "priority": priority
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to enqueue job {job_id}"
            )
    
    except Exception as e:
        logger.error(f"Failed to enqueue job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enqueue training job: {str(e)}"
        )


@router.get("/queue/status")
async def get_queue_status(
    current_user: User = Depends(get_current_user),
    queue_manager: TrainingQueueManager = Depends(get_queue_manager)
):
    """
    获取训练队列状态
    
    Args:
        current_user: 当前用户
        queue_manager: 队列管理器
    
    Returns:
        队列状态信息
    """
    try:
        status_info = queue_manager.get_queue_status()
        return status_info
    
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get queue status: {str(e)}"
        )


@router.post("/queue/cancel/{job_id}")
async def cancel_queued_job(
    job_id: int,
    current_user: User = Depends(get_current_admin_user),
    queue_manager: TrainingQueueManager = Depends(get_queue_manager)
):
    """
    取消队列中的训练任务
    
    Args:
        job_id: 训练任务ID
        current_user: 当前管理员用户
        queue_manager: 队列管理器
    
    Returns:
        取消操作结果
    """
    try:
        success = queue_manager.cancel_job(job_id)
        
        if success:
            return {
                "success": True,
                "message": f"Job {job_id} cancelled successfully",
                "job_id": job_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to cancel job {job_id} (not found or not cancellable)"
            )
    
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel training job: {str(e)}"
        )


# 监控端点
@router.get("/monitor/status")
async def get_monitoring_status(
    current_user: User = Depends(get_current_user),
    training_monitor: TrainingMonitor = Depends(get_training_monitor)
):
    """
    获取训练监控状态
    
    Args:
        current_user: 当前用户
        training_monitor: 训练监控服务
    
    Returns:
        监控状态信息
    """
    try:
        status_info = await training_monitor.get_real_time_status()
        return status_info
    
    except Exception as e:
        logger.error(f"Failed to get monitoring status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get monitoring status: {str(e)}"
        )


@router.get("/monitor/job/{job_id}")
async def get_job_monitoring_status(
    job_id: int,
    current_user: User = Depends(get_current_user),
    training_monitor: TrainingMonitor = Depends(get_training_monitor)
):
    """
    获取特定训练任务的监控状态
    
    Args:
        job_id: 训练任务ID
        current_user: 当前用户
        training_monitor: 训练监控服务
    
    Returns:
        任务监控状态信息
    """
    try:
        status_info = await training_monitor.get_real_time_status(job_id)
        return status_info
    
    except Exception as e:
        logger.error(f"Failed to get job monitoring status for {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job monitoring status: {str(e)}"
        )


@router.get("/monitor/history")
async def get_monitoring_history(
    hours: int = 24,
    job_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    training_monitor: TrainingMonitor = Depends(get_training_monitor)
):
    """
    获取训练监控历史数据
    
    Args:
        hours: 获取最近多少小时的数据
        job_id: 可选的任务ID筛选
        current_user: 当前用户
        training_monitor: 训练监控服务
    
    Returns:
        历史监控数据
    """
    try:
        history_data = training_monitor.get_historical_data(job_id, hours)
        return history_data
    
    except Exception as e:
        logger.error(f"Failed to get monitoring history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get monitoring history: {str(e)}"
        )


# 恢复和重试端点
@router.post("/recovery/analyze/{job_id}")
async def analyze_training_failure(
    job_id: int,
    current_user: User = Depends(get_current_admin_user),
    recovery_service: TrainingRecoveryService = Depends(get_recovery_service)
):
    """
    分析训练失败原因
    
    Args:
        job_id: 训练任务ID
        current_user: 当前管理员用户
        recovery_service: 训练恢复服务
    
    Returns:
        失败分析结果
    """
    try:
        analysis = recovery_service.analyze_failure(job_id)
        return analysis
    
    except Exception as e:
        logger.error(f"Failed to analyze failure for job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze training failure: {str(e)}"
        )


@router.post("/recovery/attempt/{job_id}")
async def attempt_training_recovery(
    job_id: int,
    strategy: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    recovery_service: TrainingRecoveryService = Depends(get_recovery_service)
):
    """
    尝试恢复训练任务
    
    Args:
        job_id: 训练任务ID
        strategy: 可选的恢复策略
        current_user: 当前管理员用户
        recovery_service: 训练恢复服务
    
    Returns:
        恢复操作结果
    """
    try:
        result = recovery_service.attempt_recovery(job_id, strategy)
        return result
    
    except Exception as e:
        logger.error(f"Failed to attempt recovery for job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to attempt training recovery: {str(e)}"
        )


# 系统管理端点
@router.post("/system/start-queue")
async def start_training_queue(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    启动训练队列处理
    
    Args:
        current_user: 当前管理员用户
        db: 数据库会话
    
    Returns:
        启动结果
    """
    try:
        queue_manager = get_queue_manager(db)
        success = queue_manager.start_processing()
        
        if success:
            return {
                "success": True,
                "message": "Training queue processing started"
            }
        else:
            return {
                "success": False,
                "message": "Training queue is already running"
            }
    
    except Exception as e:
        logger.error(f"Failed to start training queue: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start training queue: {str(e)}"
        )


@router.post("/system/stop-queue")
async def stop_training_queue(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    停止训练队列处理
    
    Args:
        current_user: 当前管理员用户
        db: 数据库会话
    
    Returns:
        停止结果
    """
    try:
        queue_manager = get_queue_manager(db)
        success = queue_manager.stop_processing()
        
        if success:
            return {
                "success": True,
                "message": "Training queue processing stopped"
            }
        else:
            return {
                "success": False,
                "message": "Training queue is not running"
            }
    
    except Exception as e:
        logger.error(f"Failed to stop training queue: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop training queue: {str(e)}"
        )


@router.post("/system/start-monitor")
async def start_training_monitor(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    启动训练监控服务
    
    Args:
        current_user: 当前管理员用户
        db: 数据库会话
    
    Returns:
        启动结果
    """
    try:
        training_monitor = get_training_monitor(db)
        success = await training_monitor.start_monitoring()
        
        if success:
            return {
                "success": True,
                "message": "Training monitoring started"
            }
        else:
            return {
                "success": False,
                "message": "Training monitoring is already running"
            }
    
    except Exception as e:
        logger.error(f"Failed to start training monitor: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start training monitor: {str(e)}"
        )


@router.post("/system/stop-monitor")
async def stop_training_monitor(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    停止训练监控服务
    
    Args:
        current_user: 当前管理员用户
        db: 数据库会话
    
    Returns:
        停止结果
    """
    try:
        training_monitor = get_training_monitor(db)
        success = await training_monitor.stop_monitoring()
        
        if success:
            return {
                "success": True,
                "message": "Training monitoring stopped"
            }
        else:
            return {
                "success": False,
                "message": "Training monitoring is not running"
            }
    
    except Exception as e:
        logger.error(f"Failed to stop training monitor: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop training monitor: {str(e)}"
        )