"""
系统管理API端点
"""

from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import psutil
import time

from app.core.database import get_db
from app.api.deps import get_current_admin_user
from app.models.user import User
from app.models.system import SystemConfig
from app.core.config import settings

router = APIRouter()


@router.get("/status", summary="获取系统状态")
async def get_status(
    db: Session = Depends(get_db)
) -> Any:
    """
    获取系统状态
    """
    # 检查数据库连接
    try:
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    # 检查Redis连接
    # TODO: 实现Redis连接检查
    redis_status = "unknown"
    
    return {
        "system": {
            "status": "healthy",
            "uptime": int(time.time()),
            "version": settings.VERSION
        },
        "database": {
            "status": db_status
        },
        "redis": {
            "status": redis_status
        }
    }


@router.get("/metrics", summary="获取系统指标")
async def get_metrics(
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    获取系统性能指标（仅管理员）
    """
    # 获取CPU使用率
    cpu_percent = psutil.cpu_percent(interval=1)
    
    # 获取内存使用情况
    memory = psutil.virtual_memory()
    
    # 获取磁盘使用情况
    disk = psutil.disk_usage('/')
    
    return {
        "cpu": {
            "usage_percent": cpu_percent,
            "count": psutil.cpu_count()
        },
        "memory": {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "percent": memory.percent
        },
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent
        }
    }


@router.get("/configs", summary="获取系统配置")
async def get_configs(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    获取系统配置（仅管理员）
    """
    configs = db.query(SystemConfig).all()
    
    return {
        "configs": [
            {
                "key": config.config_key,
                "value": config.config_value,
                "type": config.config_type,
                "description": config.description
            }
            for config in configs
        ]
    }


@router.put("/configs/{config_key}", summary="更新系统配置")
async def update_config(
    config_key: str,
    config_data: dict,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    更新系统配置（仅管理员）
    """
    config = db.query(SystemConfig).filter(SystemConfig.config_key == config_key).first()
    
    if not config:
        # 创建新配置
        config = SystemConfig(
            config_key=config_key,
            config_value=str(config_data.get("value")),
            config_type=config_data.get("type", "string"),
            description=config_data.get("description")
        )
        db.add(config)
    else:
        # 更新现有配置
        config.config_value = str(config_data.get("value"))
    
    db.commit()
    db.refresh(config)
    
    return {
        "key": config.config_key,
        "value": config.config_value,
        "type": config.config_type
    }