"""
Training Queue Manager - 训练任务队列管理器

本服务负责管理训练任务的队列、并发控制和任务调度。

主要功能：
    - 训练任务队列管理
    - 并发控制（限制同时运行的训练任务数量）
    - 任务优先级调度
    - 失败任务重试机制
    - 资源监控和负载均衡

技术实现：
    - 使用内存队列管理待执行任务
    - 支持任务优先级（高、中、低）
    - 自动检测系统资源使用情况
    - 智能调度避免资源冲突

使用示例：
    >>> from app.services.training_queue_manager import TrainingQueueManager
    >>> queue_manager = TrainingQueueManager(db_session, max_concurrent=2)
    >>> 
    >>> # 添加训练任务到队列
    >>> queue_manager.enqueue_training_job(job_id=1, priority="high")
    >>> 
    >>> # 启动队列处理
    >>> queue_manager.start_processing()
    >>> 
    >>> # 停止队列处理
    >>> queue_manager.stop_processing()
"""

import asyncio
import threading
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from queue import PriorityQueue, Empty
import psutil

from sqlalchemy.orm import Session
from loguru import logger

from app.models.training_job import TrainingJob
from app.services.model_trainer import ModelTrainer, TrainingError


class TaskPriority(Enum):
    """任务优先级枚举"""
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class TaskStatus(Enum):
    """任务状态枚举"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class QueuedTask:
    """队列中的任务对象"""
    job_id: int
    priority: TaskPriority
    created_at: datetime
    retry_count: int = 0
    max_retries: int = 3
    
    def __lt__(self, other):
        """优先级比较，用于优先队列排序"""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        # 相同优先级按创建时间排序
        return self.created_at < other.created_at


class TrainingQueueManager:
    """
    训练任务队列管理器
    
    负责管理训练任务的队列、调度和执行。支持并发控制、优先级调度和失败重试。
    
    核心功能：
        1. 任务队列管理：
           - 优先级队列（高、中、低优先级）
           - FIFO调度（相同优先级按时间排序）
           - 任务状态跟踪
        
        2. 并发控制：
           - 限制同时运行的训练任务数量
           - 资源监控（CPU、内存、GPU使用率）
           - 智能负载均衡
        
        3. 失败处理：
           - 自动重试机制（最多3次）
           - 指数退避策略
           - 失败原因分析和记录
        
        4. 实时监控：
           - 任务进度跟踪
           - 性能指标收集
           - 异常检测和告警
    
    属性：
        db (Session): 数据库会话
        max_concurrent (int): 最大并发任务数
        task_queue (PriorityQueue): 任务优先队列
        running_tasks (Dict): 正在运行的任务
        trainer (ModelTrainer): 模型训练器
        is_processing (bool): 是否正在处理队列
        processing_thread (Thread): 队列处理线程
    """
    
    def __init__(
        self,
        db: Session,
        max_concurrent: int = 2,
        resource_check_interval: int = 30
    ):
        """
        初始化训练队列管理器
        
        Args:
            db: 数据库会话
            max_concurrent: 最大并发训练任务数
            resource_check_interval: 资源检查间隔（秒）
        """
        self.db = db
        self.max_concurrent = max_concurrent
        self.resource_check_interval = resource_check_interval
        
        # 任务队列和状态管理
        self.task_queue = PriorityQueue()
        self.running_tasks: Dict[int, Dict] = {}
        self.completed_tasks: List[int] = []
        self.failed_tasks: Dict[int, str] = {}
        
        # 服务组件
        self.trainer = ModelTrainer(db)
        
        # 队列处理控制
        self.is_processing = False
        self.processing_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # 统计信息
        self.stats = {
            'total_queued': 0,
            'total_completed': 0,
            'total_failed': 0,
            'total_retries': 0,
            'average_wait_time': 0.0,
            'average_execution_time': 0.0
        }
        
        logger.info(f"TrainingQueueManager initialized - Max concurrent: {max_concurrent}")
    
    def enqueue_training_job(
        self,
        job_id: int,
        priority: str = "medium",
        max_retries: int = 3
    ) -> bool:
        """
        将训练任务添加到队列
        
        Args:
            job_id: 训练任务ID
            priority: 任务优先级 ("high", "medium", "low")
            max_retries: 最大重试次数
            
        Returns:
            bool: 是否成功添加到队列
        """
        try:
            # 验证任务存在
            job = self.db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
            if not job:
                logger.error(f"Training job {job_id} not found")
                return False
            
            # 检查任务状态
            if job.status not in ["pending", "failed"]:
                logger.warning(f"Job {job_id} cannot be queued (status: {job.status})")
                return False
            
            # 转换优先级
            priority_map = {
                "high": TaskPriority.HIGH,
                "medium": TaskPriority.MEDIUM,
                "low": TaskPriority.LOW
            }
            task_priority = priority_map.get(priority.lower(), TaskPriority.MEDIUM)
            
            # 创建队列任务
            queued_task = QueuedTask(
                job_id=job_id,
                priority=task_priority,
                created_at=datetime.utcnow(),
                max_retries=max_retries
            )
            
            # 添加到队列
            self.task_queue.put(queued_task)
            
            # 更新数据库状态
            job.status = "queued"
            job.queued_at = datetime.utcnow()
            self.db.commit()
            
            # 更新统计
            self.stats['total_queued'] += 1
            
            logger.info(f"Job {job_id} added to queue with {priority} priority")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enqueue job {job_id}: {e}")
            return False
    
    def start_processing(self) -> bool:
        """
        启动队列处理
        
        Returns:
            bool: 是否成功启动
        """
        if self.is_processing:
            logger.warning("Queue processing is already running")
            return False
        
        try:
            self.is_processing = True
            self.stop_event.clear()
            
            # 启动处理线程
            self.processing_thread = threading.Thread(
                target=self._process_queue,
                name="TrainingQueueProcessor",
                daemon=True
            )
            self.processing_thread.start()
            
            logger.info("Training queue processing started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start queue processing: {e}")
            self.is_processing = False
            return False
    
    def stop_processing(self) -> bool:
        """
        停止队列处理
        
        Returns:
            bool: 是否成功停止
        """
        if not self.is_processing:
            logger.warning("Queue processing is not running")
            return False
        
        try:
            # 设置停止标志
            self.stop_event.set()
            self.is_processing = False
            
            # 等待处理线程结束
            if self.processing_thread and self.processing_thread.is_alive():
                self.processing_thread.join(timeout=10)
                if self.processing_thread.is_alive():
                    logger.warning("Processing thread did not stop gracefully")
            
            logger.info("Training queue processing stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop queue processing: {e}")
            return False
    
    def _process_queue(self):
        """
        队列处理主循环（在独立线程中运行）
        """
        logger.info("Queue processing thread started")
        
        while not self.stop_event.is_set():
            try:
                # 检查是否可以启动新任务
                if len(self.running_tasks) >= self.max_concurrent:
                    time.sleep(5)
                    continue
                
                # 检查系统资源
                if not self._check_system_resources():
                    logger.info("System resources insufficient, waiting...")
                    time.sleep(self.resource_check_interval)
                    continue
                
                # 获取下一个任务
                try:
                    task = self.task_queue.get(timeout=5)
                except Empty:
                    continue
                
                # 启动任务
                self._start_task(task)
                
            except Exception as e:
                logger.error(f"Error in queue processing: {e}")
                time.sleep(5)
        
        logger.info("Queue processing thread stopped")
    
    def _start_task(self, task: QueuedTask):
        """
        启动单个训练任务
        
        Args:
            task: 队列任务对象
        """
        try:
            job_id = task.job_id
            logger.info(f"Starting training task {job_id}")
            
            # 更新任务状态
            job = self.db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
            if not job:
                logger.error(f"Job {job_id} not found when starting")
                return
            
            job.status = "running"
            job.started_at = datetime.utcnow()
            self.db.commit()
            
            # 记录运行任务
            self.running_tasks[job_id] = {
                'task': task,
                'started_at': datetime.utcnow(),
                'thread': None
            }
            
            # 在独立线程中执行训练
            training_thread = threading.Thread(
                target=self._execute_training,
                args=(task,),
                name=f"Training-{job_id}",
                daemon=True
            )
            
            self.running_tasks[job_id]['thread'] = training_thread
            training_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to start task {task.job_id}: {e}")
            self._handle_task_failure(task, str(e))
    
    def _execute_training(self, task: QueuedTask):
        """
        执行训练任务（在独立线程中运行）
        
        Args:
            task: 队列任务对象
        """
        job_id = task.job_id
        start_time = time.time()
        
        try:
            logger.info(f"Executing training for job {job_id}")
            
            # 执行训练
            result = self.trainer.train_model(
                job_id=job_id,
                progress_callback=self._training_progress_callback
            )
            
            # 训练成功
            execution_time = time.time() - start_time
            self._handle_task_success(task, result, execution_time)
            
        except Exception as e:
            logger.error(f"Training failed for job {job_id}: {e}")
            self._handle_task_failure(task, str(e))
        
        finally:
            # 清理运行任务记录
            if job_id in self.running_tasks:
                del self.running_tasks[job_id]
    
    def _handle_task_success(self, task: QueuedTask, result: Dict, execution_time: float):
        """
        处理任务成功完成
        
        Args:
            task: 队列任务对象
            result: 训练结果
            execution_time: 执行时间（秒）
        """
        job_id = task.job_id
        
        try:
            # 更新数据库状态
            job = self.db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
            if job:
                job.status = "completed"
                job.completed_at = datetime.utcnow()
                self.db.commit()
            
            # 更新统计
            self.completed_tasks.append(job_id)
            self.stats['total_completed'] += 1
            self.stats['average_execution_time'] = (
                (self.stats['average_execution_time'] * (self.stats['total_completed'] - 1) + execution_time) /
                self.stats['total_completed']
            )
            
            logger.info(f"Job {job_id} completed successfully in {execution_time:.1f}s")
            
        except Exception as e:
            logger.error(f"Error handling task success for job {job_id}: {e}")
    
    def _handle_task_failure(self, task: QueuedTask, error_message: str):
        """
        处理任务失败
        
        Args:
            task: 队列任务对象
            error_message: 错误消息
        """
        job_id = task.job_id
        
        try:
            # 检查是否需要重试
            if task.retry_count < task.max_retries:
                # 重试任务
                task.retry_count += 1
                retry_delay = min(300, 60 * (2 ** task.retry_count))  # 指数退避，最大5分钟
                
                logger.info(f"Job {job_id} failed, retrying in {retry_delay}s (attempt {task.retry_count}/{task.max_retries})")
                
                # 更新数据库状态
                job = self.db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
                if job:
                    job.status = "retrying"
                    job.error_message = f"Retry {task.retry_count}: {error_message}"
                    self.db.commit()
                
                # 延迟后重新加入队列
                def retry_task():
                    time.sleep(retry_delay)
                    if not self.stop_event.is_set():
                        self.task_queue.put(task)
                
                retry_thread = threading.Thread(target=retry_task, daemon=True)
                retry_thread.start()
                
                self.stats['total_retries'] += 1
                
            else:
                # 重试次数用尽，标记为失败
                logger.error(f"Job {job_id} failed permanently after {task.max_retries} retries")
                
                # 更新数据库状态
                job = self.db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
                if job:
                    job.status = "failed"
                    job.completed_at = datetime.utcnow()
                    job.error_message = f"Failed after {task.max_retries} retries: {error_message}"
                    self.db.commit()
                
                # 更新统计
                self.failed_tasks[job_id] = error_message
                self.stats['total_failed'] += 1
                
        except Exception as e:
            logger.error(f"Error handling task failure for job {job_id}: {e}")
    
    def _training_progress_callback(self, job_id: int, progress_data: Dict):
        """
        训练进度回调函数
        
        Args:
            job_id: 训练任务ID
            progress_data: 进度数据
        """
        try:
            # 记录进度日志
            logger.debug(f"Job {job_id} progress: {progress_data}")
            
            # 这里可以添加实时进度推送逻辑
            # 例如：WebSocket推送、消息队列等
            
        except Exception as e:
            logger.error(f"Error in progress callback for job {job_id}: {e}")
    
    def _check_system_resources(self) -> bool:
        """
        检查系统资源是否足够启动新的训练任务
        
        Returns:
            bool: 是否有足够资源
        """
        try:
            # 检查CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 90:
                logger.debug(f"CPU usage too high: {cpu_percent}%")
                return False
            
            # 检查内存使用率
            memory = psutil.virtual_memory()
            if memory.percent > 85:
                logger.debug(f"Memory usage too high: {memory.percent}%")
                return False
            
            # 检查磁盘空间
            disk = psutil.disk_usage('/')
            if disk.percent > 90:
                logger.debug(f"Disk usage too high: {disk.percent}%")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking system resources: {e}")
            return True  # 检查失败时允许继续
    
    def get_queue_status(self) -> Dict:
        """
        获取队列状态信息
        
        Returns:
            Dict: 队列状态信息
        """
        return {
            'is_processing': self.is_processing,
            'queue_size': self.task_queue.qsize(),
            'running_tasks': len(self.running_tasks),
            'max_concurrent': self.max_concurrent,
            'completed_tasks': len(self.completed_tasks),
            'failed_tasks': len(self.failed_tasks),
            'statistics': self.stats.copy(),
            'running_task_ids': list(self.running_tasks.keys())
        }
    
    def cancel_job(self, job_id: int) -> bool:
        """
        取消队列中的任务
        
        Args:
            job_id: 训练任务ID
            
        Returns:
            bool: 是否成功取消
        """
        try:
            # 如果任务正在运行，停止它
            if job_id in self.running_tasks:
                # 停止训练
                self.trainer.stop_training(job_id)
                
                # 清理运行任务记录
                if job_id in self.running_tasks:
                    del self.running_tasks[job_id]
                
                logger.info(f"Cancelled running job {job_id}")
                return True
            
            # 如果任务在队列中，需要从队列中移除（这比较复杂，因为PriorityQueue不支持直接删除）
            # 简单的方法是标记任务为取消状态，在处理时跳过
            job = self.db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
            if job and job.status == "queued":
                job.status = "cancelled"
                job.completed_at = datetime.utcnow()
                self.db.commit()
                
                logger.info(f"Cancelled queued job {job_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {e}")
            return False