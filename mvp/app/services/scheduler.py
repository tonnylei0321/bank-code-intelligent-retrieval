"""
定时任务调度器

功能：
- 每天凌晨3:00自动加载银行数据到RAG系统（已修改为RAG导入）
- 支持手动触发
- 任务执行日志
- 支持停止自动任务
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
from app.services.rag_service import RAGService


class BankDataScheduler:
    """银行数据定时调度器 - 已修改为RAG导入模式"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.last_run: Optional[datetime] = None
        self.last_result: Optional[dict] = None
        self.auto_task_enabled = False  # 默认关闭自动任务
        self.rag_mode = True  # 启用RAG模式
    
    def start(self, enable_auto_task: bool = False):
        """
        启动调度器
        
        Args:
            enable_auto_task: 是否启用自动任务（默认关闭）
        """
        if self.is_running:
            logger.warning("调度器已经在运行")
            return
        
        self.auto_task_enabled = enable_auto_task
        
        if self.auto_task_enabled:
            # 添加定时任务：每天凌晨3:00执行（导入到RAG）
            self.scheduler.add_job(
                self.load_bank_data_to_rag_job,
                trigger=CronTrigger(hour=3, minute=0),
                id='bank_data_rag_loader',
                name='银行数据自动加载到RAG',
                replace_existing=True
            )
            logger.info("银行数据调度器已启动 - 每天凌晨3:00自动加载数据到RAG系统")
        else:
            logger.info("银行数据调度器已启动 - 自动任务已禁用")
        
        self.scheduler.start()
        self.is_running = True
    
    def stop(self):
        """停止调度器"""
        if not self.is_running:
            return
        
        self.scheduler.shutdown()
        self.is_running = False
        self.auto_task_enabled = False
        logger.info("银行数据调度器已停止")
    
    def enable_auto_task(self):
        """启用自动任务"""
        if not self.is_running:
            logger.error("调度器未运行，无法启用自动任务")
            return False
        
        if self.auto_task_enabled:
            logger.info("自动任务已经启用")
            return True
        
        try:
            self.scheduler.add_job(
                self.load_bank_data_to_rag_job,
                trigger=CronTrigger(hour=3, minute=0),
                id='bank_data_rag_loader',
                name='银行数据自动加载到RAG',
                replace_existing=True
            )
            self.auto_task_enabled = True
            logger.info("自动任务已启用 - 每天凌晨3:00自动加载数据到RAG系统")
            return True
        except Exception as e:
            logger.error(f"启用自动任务失败: {e}")
            return False
    
    def disable_auto_task(self):
        """禁用自动任务"""
        if not self.auto_task_enabled:
            logger.info("自动任务已经禁用")
            return True
        
        try:
            if self.scheduler.get_job('bank_data_rag_loader'):
                self.scheduler.remove_job('bank_data_rag_loader')
            self.auto_task_enabled = False
            logger.info("自动任务已禁用")
            return True
        except Exception as e:
            logger.error(f"禁用自动任务失败: {e}")
            return False
    
    async def load_bank_data_to_rag_job(self):
        """定时任务：加载银行数据到RAG系统"""
        logger.info("开始执行定时任务：加载银行数据到RAG系统")
        
        db = SessionLocal()
        try:
            # 使用RAG服务从文件直接加载
            rag_service = RAGService(db)
            
            # 默认银行数据文件路径
            bank_data_file = "../data/T_BANK_LINE_NO_ICBC_ALL.unl"
            
            # 加载到RAG系统
            success = await rag_service.load_from_file(bank_data_file, force_rebuild=True)
            
            self.last_run = datetime.now()
            
            if success:
                result = {
                    "success": True,
                    "message": "银行数据已成功加载到RAG系统",
                    "file_path": bank_data_file,
                    "timestamp": datetime.now().isoformat(),
                    "mode": "RAG"
                }
                logger.info("银行数据RAG加载成功")
            else:
                result = {
                    "success": False,
                    "message": "银行数据RAG加载失败",
                    "file_path": bank_data_file,
                    "timestamp": datetime.now().isoformat(),
                    "mode": "RAG"
                }
                logger.error("银行数据RAG加载失败")
            
            self.last_result = result
        
        except Exception as e:
            logger.error(f"定时任务执行失败: {e}")
            self.last_result = {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "mode": "RAG"
            }
        
        finally:
            db.close()
    
    async def load_bank_data_job(self):
        """定时任务：加载银行数据（旧版本，保留兼容性）"""
        logger.info("开始执行定时任务：加载银行数据")
        
        db = SessionLocal()
        try:
            if self.rag_mode:
                # 使用RAG模式
                await self.load_bank_data_to_rag_job()
            else:
                # 使用传统数据库模式
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
    
    def trigger_now(self, use_rag: bool = True) -> dict:
        """
        手动触发数据加载
        
        Args:
            use_rag: 是否使用RAG模式（默认True）
        """
        logger.info(f"手动触发银行数据加载 - RAG模式: {use_rag}")
        
        db = SessionLocal()
        try:
            if use_rag:
                # 使用RAG模式
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                rag_service = RAGService(db)
                bank_data_file = "../data/T_BANK_LINE_NO_ICBC_ALL.unl"
                
                success = loop.run_until_complete(
                    rag_service.load_from_file(bank_data_file, force_rebuild=True)
                )
                loop.close()
                
                self.last_run = datetime.now()
                
                if success:
                    result = {
                        "success": True,
                        "message": "银行数据已成功手动加载到RAG系统",
                        "file_path": bank_data_file,
                        "timestamp": datetime.now().isoformat(),
                        "mode": "RAG"
                    }
                else:
                    result = {
                        "success": False,
                        "message": "银行数据RAG手动加载失败",
                        "file_path": bank_data_file,
                        "timestamp": datetime.now().isoformat(),
                        "mode": "RAG"
                    }
            else:
                # 使用传统数据库模式
                loader = BankDataLoader(db)
                result = loader.check_and_load_if_exists()
                result["mode"] = "Database"
            
            self.last_result = result
            return result
        
        except Exception as e:
            logger.error(f"手动加载失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "mode": "RAG" if use_rag else "Database"
            }
        
        finally:
            db.close()
    
    def get_status(self) -> dict:
        """获取调度器状态"""
        next_run = None
        if self.is_running and self.auto_task_enabled and self.scheduler.get_job('bank_data_rag_loader'):
            next_run_time = self.scheduler.get_job('bank_data_rag_loader').next_run_time
            if next_run_time:
                next_run = next_run_time.isoformat()
        
        return {
            "is_running": self.is_running,
            "auto_task_enabled": self.auto_task_enabled,
            "rag_mode": self.rag_mode,
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


def start_scheduler(enable_auto_task: bool = False):
    """
    启动调度器
    
    Args:
        enable_auto_task: 是否启用自动任务（默认关闭）
    """
    scheduler = get_scheduler()
    scheduler.start(enable_auto_task=enable_auto_task)


def stop_scheduler():
    """停止调度器"""
    scheduler = get_scheduler()
    scheduler.stop()
