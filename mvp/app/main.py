"""
FastAPI application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.core.logging import setup_logging, logger
from app.core.rate_limiter import RateLimiter, RateLimitMiddleware
from app.core.exceptions import register_exception_handlers
from app.api import auth, admin, datasets, qa_pairs, training, evaluation, query, logs, training_data, bank_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    - Startup: Initialize database, logging, etc.
    - Shutdown: Cleanup resources
    """
    # Startup
    logger.info("Starting application...")
    setup_logging()
    init_db()
    logger.info("Database initialized")
    
    # Fix zombie training jobs (jobs stuck in 'running' state after restart)
    from app.core.database import SessionLocal
    from app.models.training_job import TrainingJob
    from datetime import datetime
    
    db = SessionLocal()
    try:
        zombie_jobs = db.query(TrainingJob).filter(
            TrainingJob.status == "running"
        ).all()
        
        if zombie_jobs:
            logger.warning(f"Found {len(zombie_jobs)} zombie training jobs, marking as failed")
            for job in zombie_jobs:
                job.status = "failed"
                job.error_message = "Training interrupted by server restart"
                job.completed_at = datetime.utcnow()
            db.commit()
            logger.info(f"Fixed {len(zombie_jobs)} zombie training jobs")
    except Exception as e:
        logger.error(f"Failed to fix zombie jobs: {e}")
    finally:
        db.close()
    
    # 启动银行数据定时调度器
    from app.services.scheduler import start_scheduler
    try:
        start_scheduler()
        logger.info("银行数据定时调度器已启动")
    except Exception as e:
        logger.error(f"启动调度器失败: {e}")
    
    logger.info(f"Application started: {settings.APP_NAME} v{settings.APP_VERSION}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    # 停止调度器
    from app.services.scheduler import stop_scheduler
    try:
        stop_scheduler()
        logger.info("银行数据定时调度器已停止")
    except Exception as e:
        logger.error(f"停止调度器失败: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="联行号检索模型训练验证系统 - MVP",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure rate limiting
rate_limiter = RateLimiter(requests_per_minute=settings.API_RATE_LIMIT)
app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)

# Register exception handlers
register_exception_handlers(app)

# Include routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(datasets.router)
app.include_router(qa_pairs.router)
app.include_router(training.router)
app.include_router(evaluation.router)
app.include_router(query.router)
app.include_router(logs.router)
app.include_router(training_data.router)
app.include_router(bank_data.router)


@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
