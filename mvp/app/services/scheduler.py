"""
定时任务调度器

功能：
- 每天凌晨3:00自动加载银行数据
- 支持手动触发
- 任务执行日志
"""

import asyncio
from datetime import datetime, time
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import SessionLocal
from app.services.bank_data_loader import BankDataLoader


class BankDataScheduler:
    """银行数据定时调度器"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.last_run: Optional[datetime] = None
        self.last_result: Optional[dict] = None
    
    def start(self):
        """启动调度器"""
        if self.is_running:
            logger.warning("调度器已经在运行")
            return
        
        # 添加定时任务：每天凌晨3:00执行
        self.scheduler.add_job(
            self.load_bank_data_job,
            trigger=CronTrigger(hour=3, minute=0),
            id='bank_data_loader',
            name='银行数据自动加载',
            replace_existing=True
        )
        
        self.scheduler.start()
        self.is_running = True
        logger.info("银行数据调度器已启动 - 每天凌晨3:00自动加载数据")
    
    def stop(self):
        """停止调度器"""
        if not self.is_running:
            return
        
        self.scheduler.shutdown()
        self.is_running = False
        logger.info("银行数据调度器已停止")
    
    async def load_bank_data_job(self):
        """定时任务：加载银行数据"""
        logger.info("开始执行定时任务：加载银行数据")
        
        db = SessionLocal()
        try:
            loader = BankDataLoader(db)
            result = loader.check_and_load_if_exists()
            
            self.last_run = datetime.now()
            self.last_result = result
            
            if result.get('success'):
                logger.info(
                    f"银行数据加载成功 - "
                    f"新增: {result.get('new_records', 0)}, "
                    f"更新: {result.get('updated_records', 0)}"
                )
            else:
                logger.warning(f"银行数据加载失败: {result.get('message', 'Unknown error')}")
        
        except Exception as e:
            logger.error(f"定时任务执行失败: {e}")
            self.last_result = {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        
        finally:
            db.close()
    
    def trigger_now(self) -> dict:
        """手动触发数据加载"""
        logger.info("手动触发银行数据加载")
        
        db = SessionLocal()
        try:
            loader = BankDataLoader(db)
            result = loader.check_and_load_if_exists()
            
            self.last_run = datetime.now()
            self.last_result = result
            
            return result
        
        except Exception as e:
            logger.error(f"手动加载失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        
        finally:
            db.close()
    
    def get_status(self) -> dict:
        """获取调度器状态"""
        next_run = None
        if self.is_running and self.scheduler.get_job('bank_data_loader'):
            next_run_time = self.scheduler.get_job('bank_data_loader').next_run_time
            if next_run_time:
                next_run = next_run_time.isoformat()
        
        return {
            "is_running": self.is_running,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": next_run,
            "last_result": self.last_result
        }


# 全局调度器实例
_scheduler: Optional[BankDataScheduler] = None


def get_scheduler() -> BankDataScheduler:
    """获取全局调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = BankDataScheduler()
    return _scheduler


def start_scheduler():
    """启动调度器"""
    scheduler = get_scheduler()
    scheduler.start()


def stop_scheduler():
    """停止调度器"""
    scheduler = get_scheduler()
    scheduler.stop()
