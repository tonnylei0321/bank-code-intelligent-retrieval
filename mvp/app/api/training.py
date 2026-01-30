"""
Training API Endpoints - 训练任务API端点

本模块提供模型训练相关的API端点。

端点列表：
    - POST /api/v1/training/start: 启动新的训练任务（仅管理员）
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
    >>> # 启动训练
    >>> response = requests.post(
    ...     "http://localhost:8000/api/v1/training/start",
    ...     json={
    ...         "dataset_id": 1,
    ...         "model_name": "Qwen/Qwen2.5-0.5B",
    ...         "epochs": 3,
    ...         "batch_size": 8,
    ...         "learning_rate": 2e-4
    ...     },
    ...     headers={"Authorization": f"Bearer {admin_token}"}
    ... )
    >>> job_id = response.json()["id"]
    >>> 
    >>> # 查询训练进度
    >>> response = requests.get(
    ...     f"http://localhost:8000/api/v1/training/{job_id}",
    ...     headers={"Authorization": f"Bearer {token}"}
    ... )
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


router = APIRouter(prefix="/api/v1/training", tags=["training"])


# Request/Response schemas
class TrainingStartRequest(BaseModel):
    """Request schema for starting training"""
    dataset_id: int = Field(..., description="Dataset ID to train on")
    model_name: str = Field(default="Qwen/Qwen2.5-0.5B", description="Base model name")
    epochs: int = Field(default=3, ge=1, le=20, description="Number of training epochs")
    batch_size: int = Field(default=8, ge=1, le=64, description="Training batch size")
    learning_rate: float = Field(default=2e-4, gt=0, description="Learning rate")
    lora_r: int = Field(default=16, ge=1, le=128, description="LoRA rank")
    lora_alpha: int = Field(default=32, ge=1, le=256, description="LoRA alpha")
    lora_dropout: float = Field(default=0.05, ge=0, le=0.5, description="LoRA dropout")


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


@router.post("/start", response_model=TrainingJobResponse, status_code=status.HTTP_201_CREATED)
async def start_training(
    request: TrainingStartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start a new training job
    
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
        
        # Create training job
        job = TrainingJob(
            dataset_id=request.dataset_id,
            created_by=current_user.id,
            status="pending",
            model_name=request.model_name,
            epochs=request.epochs,
            batch_size=request.batch_size,
            learning_rate=request.learning_rate,
            lora_r=request.lora_r,
            lora_alpha=request.lora_alpha,
            lora_dropout=request.lora_dropout
        )
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        logger.info(f"Training job {job.id} created by user {current_user.id}")
        
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
