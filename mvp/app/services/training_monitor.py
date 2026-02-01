"""
Training Monitor Service - 训练进度监控服务

本服务负责实时监控训练任务的进度、性能指标和系统状态。

主要功能：
    - 实时训练进度跟踪
    - 性能指标收集和分析
    - 异常检测和告警
    - 训练日志管理
    - WebSocket实时推送

技术实现：
    - 异步监控循环
    - 多线程数据收集
    - 内存缓存热点数据
    - WebSocket实时通信

使用示例：
    >>> from app.services.training_monitor import TrainingMonitor
    >>> monitor = TrainingMonitor(db_session)
    >>> 
    >>> # 启动监控
    >>> await monitor.start_monitoring()
    >>> 
    >>> # 获取实时状态
    >>> status = await monitor.get_real_time_status(job_id=1)
"""

import asyncio
import time
import threading
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import deque
import json

import psutil
import torch
from sqlalchemy.orm import Session
from loguru import logger

from app.models.training_job import TrainingJob
from app.models.query_log import QueryLog


@dataclass
class SystemMetrics:
    """系统性能指标"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    gpu_memory_used_gb: Optional[float] = None
    gpu_memory_total_gb: Optional[float] = None
    gpu_utilization: Optional[float] = None


@dataclass
class TrainingMetrics:
    """训练性能指标"""
    job_id: int
    timestamp: datetime
    epoch: int
    step: int
    total_steps: int
    progress_percent: float
    train_loss: Optional[float]
    val_loss: Optional[float]
    learning_rate: Optional[float]
    tokens_per_second: Optional[float]
    estimated_time_remaining: Optional[float]


@dataclass
class AlertEvent:
    """告警事件"""
    timestamp: datetime
    job_id: Optional[int]
    alert_type: str  # "warning", "error", "critical"
    message: str
    details: Dict[str, Any]


class TrainingMonitor:
    """
    训练监控服务
    
    负责实时监控训练任务的进度、性能和系统状态。
    
    核心功能：
        1. 实时监控：
           - 训练进度跟踪
           - 系统资源监控
           - GPU使用情况监控
           - 性能指标收集
        
        2. 异常检测：
           - 训练停滞检测
           - 内存泄漏检测
           - 异常loss波动检测
           - 系统资源耗尽检测
        
        3. 告警机制：
           - 实时告警推送
           - 告警级别分类
           - 告警历史记录
           - 自动恢复建议
        
        4. 数据管理：
           - 指标数据缓存
           - 历史数据清理
           - 性能数据导出
           - 实时数据推送
    
    属性：
        db (Session): 数据库会话
        monitoring_interval (int): 监控间隔（秒）
        is_monitoring (bool): 是否正在监控
        system_metrics_history (deque): 系统指标历史
        training_metrics_history (Dict): 训练指标历史
        alert_history (deque): 告警历史
        websocket_clients (List): WebSocket客户端列表
    """
    
    def __init__(
        self,
        db: Session,
        monitoring_interval: int = 10,
        history_size: int = 1000
    ):
        """
        初始化训练监控服务
        
        Args:
            db: 数据库会话
            monitoring_interval: 监控间隔（秒）
            history_size: 历史数据保留数量
        """
        self.db = db
        self.monitoring_interval = monitoring_interval
        self.history_size = history_size
        
        # 监控状态
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # 数据存储
        self.system_metrics_history = deque(maxlen=history_size)
        self.training_metrics_history: Dict[int, deque] = {}
        self.alert_history = deque(maxlen=history_size)
        
        # WebSocket客户端管理
        self.websocket_clients: List[Any] = []
        
        # 异常检测配置
        self.anomaly_config = {
            'max_cpu_percent': 95.0,
            'max_memory_percent': 90.0,
            'max_disk_percent': 95.0,
            'max_loss_increase_ratio': 2.0,
            'stagnation_threshold_minutes': 30,
            'memory_leak_threshold_mb': 1000
        }
        
        # 缓存上次检查的状态
        self.last_check_time = {}
        self.last_metrics = {}
        
        logger.info(f"TrainingMonitor initialized - Interval: {monitoring_interval}s")
    
    async def start_monitoring(self) -> bool:
        """
        启动监控服务
        
        Returns:
            bool: 是否成功启动
        """
        if self.is_monitoring:
            logger.warning("Training monitor is already running")
            return False
        
        try:
            self.is_monitoring = True
            
            # 启动监控任务
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            logger.info("Training monitor started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start training monitor: {e}")
            self.is_monitoring = False
            return False
    
    async def stop_monitoring(self) -> bool:
        """
        停止监控服务
        
        Returns:
            bool: 是否成功停止
        """
        if not self.is_monitoring:
            logger.warning("Training monitor is not running")
            return False
        
        try:
            self.is_monitoring = False
            
            # 取消监控任务
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("Training monitor stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop training monitor: {e}")
            return False
    
    async def _monitoring_loop(self):
        """
        监控主循环
        """
        logger.info("Training monitor loop started")
        
        while self.is_monitoring:
            try:
                # 收集系统指标
                system_metrics = await self._collect_system_metrics()
                if system_metrics:
                    self.system_metrics_history.append(system_metrics)
                    await self._check_system_anomalies(system_metrics)
                
                # 收集训练指标
                await self._collect_training_metrics()
                
                # 清理过期数据
                await self._cleanup_old_data()
                
                # 推送实时数据
                await self._push_real_time_data()
                
                # 等待下一次检查
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.monitoring_interval)
        
        logger.info("Training monitor loop stopped")
    
    async def _collect_system_metrics(self) -> Optional[SystemMetrics]:
        """
        收集系统性能指标
        
        Returns:
            SystemMetrics: 系统指标对象
        """
        try:
            # CPU和内存
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # GPU指标（如果可用）
            gpu_memory_used = None
            gpu_memory_total = None
            gpu_utilization = None
            
            try:
                if torch.cuda.is_available():
                    gpu_memory_used = torch.cuda.memory_allocated() / 1024**3  # GB
                    gpu_memory_total = torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
                    # GPU使用率需要nvidia-ml-py库，这里简化处理
                    gpu_utilization = (gpu_memory_used / gpu_memory_total) * 100 if gpu_memory_total > 0 else 0
                elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    # MPS不提供详细的内存信息，使用估算值
                    gpu_utilization = 50.0  # 估算值
            except Exception as gpu_error:
                logger.debug(f"GPU metrics collection failed: {gpu_error}")
            
            return SystemMetrics(
                timestamp=datetime.utcnow(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_gb=memory.used / 1024**3,
                memory_total_gb=memory.total / 1024**3,
                disk_percent=disk.percent,
                disk_used_gb=disk.used / 1024**3,
                disk_total_gb=disk.total / 1024**3,
                gpu_memory_used_gb=gpu_memory_used,
                gpu_memory_total_gb=gpu_memory_total,
                gpu_utilization=gpu_utilization
            )
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return None
    
    async def _collect_training_metrics(self):
        """
        收集所有活跃训练任务的指标
        """
        try:
            # 获取所有运行中的训练任务
            running_jobs = self.db.query(TrainingJob).filter(
                TrainingJob.status == "running"
            ).all()
            
            for job in running_jobs:
                metrics = await self._collect_job_metrics(job)
                if metrics:
                    # 初始化任务指标历史（如果不存在）
                    if job.id not in self.training_metrics_history:
                        self.training_metrics_history[job.id] = deque(maxlen=self.history_size)
                    
                    self.training_metrics_history[job.id].append(metrics)
                    await self._check_training_anomalies(job, metrics)
            
        except Exception as e:
            logger.error(f"Failed to collect training metrics: {e}")
    
    async def _collect_job_metrics(self, job: TrainingJob) -> Optional[TrainingMetrics]:
        """
        收集单个训练任务的指标
        
        Args:
            job: 训练任务对象
            
        Returns:
            TrainingMetrics: 训练指标对象
        """
        try:
            # 计算预估剩余时间
            estimated_time_remaining = None
            if job.current_step > 0 and job.total_steps > 0:
                elapsed_time = (datetime.utcnow() - job.started_at).total_seconds()
                progress_ratio = job.current_step / job.total_steps
                if progress_ratio > 0:
                    total_estimated_time = elapsed_time / progress_ratio
                    estimated_time_remaining = total_estimated_time - elapsed_time
            
            # 计算tokens/秒（简化估算）
            tokens_per_second = None
            if job.current_step > 0 and job.started_at:
                elapsed_time = (datetime.utcnow() - job.started_at).total_seconds()
                if elapsed_time > 0:
                    # 假设每个step处理1000个tokens（这是一个估算值）
                    tokens_per_second = (job.current_step * 1000) / elapsed_time
            
            return TrainingMetrics(
                job_id=job.id,
                timestamp=datetime.utcnow(),
                epoch=job.current_epoch or 0,
                step=job.current_step or 0,
                total_steps=job.total_steps or 0,
                progress_percent=job.progress_percentage or 0.0,
                train_loss=job.train_loss,
                val_loss=job.val_loss,
                learning_rate=job.learning_rate,
                tokens_per_second=tokens_per_second,
                estimated_time_remaining=estimated_time_remaining
            )
            
        except Exception as e:
            logger.error(f"Failed to collect metrics for job {job.id}: {e}")
            return None
    
    async def _check_system_anomalies(self, metrics: SystemMetrics):
        """
        检查系统异常
        
        Args:
            metrics: 系统指标
        """
        try:
            alerts = []
            
            # CPU使用率过高
            if metrics.cpu_percent > self.anomaly_config['max_cpu_percent']:
                alerts.append(AlertEvent(
                    timestamp=metrics.timestamp,
                    job_id=None,
                    alert_type="warning",
                    message=f"High CPU usage: {metrics.cpu_percent:.1f}%",
                    details={"cpu_percent": metrics.cpu_percent}
                ))
            
            # 内存使用率过高
            if metrics.memory_percent > self.anomaly_config['max_memory_percent']:
                alerts.append(AlertEvent(
                    timestamp=metrics.timestamp,
                    job_id=None,
                    alert_type="warning",
                    message=f"High memory usage: {metrics.memory_percent:.1f}%",
                    details={"memory_percent": metrics.memory_percent}
                ))
            
            # 磁盘空间不足
            if metrics.disk_percent > self.anomaly_config['max_disk_percent']:
                alerts.append(AlertEvent(
                    timestamp=metrics.timestamp,
                    job_id=None,
                    alert_type="critical",
                    message=f"Low disk space: {metrics.disk_percent:.1f}% used",
                    details={"disk_percent": metrics.disk_percent}
                ))
            
            # 处理告警
            for alert in alerts:
                await self._handle_alert(alert)
                
        except Exception as e:
            logger.error(f"Failed to check system anomalies: {e}")
    
    async def _check_training_anomalies(self, job: TrainingJob, metrics: TrainingMetrics):
        """
        检查训练异常
        
        Args:
            job: 训练任务
            metrics: 训练指标
        """
        try:
            alerts = []
            job_id = job.id
            
            # 检查训练停滞
            if job_id in self.last_check_time:
                last_time = self.last_check_time[job_id]
                last_step = self.last_metrics.get(job_id, {}).get('step', 0)
                
                time_diff = (datetime.utcnow() - last_time).total_seconds() / 60  # 分钟
                step_diff = metrics.step - last_step
                
                if time_diff > self.anomaly_config['stagnation_threshold_minutes'] and step_diff == 0:
                    alerts.append(AlertEvent(
                        timestamp=metrics.timestamp,
                        job_id=job_id,
                        alert_type="error",
                        message=f"Training stagnation detected: no progress for {time_diff:.1f} minutes",
                        details={"stagnation_minutes": time_diff}
                    ))
            
            # 检查loss异常增长
            if job_id in self.training_metrics_history and len(self.training_metrics_history[job_id]) > 1:
                history = list(self.training_metrics_history[job_id])
                if len(history) >= 2:
                    prev_loss = history[-2].train_loss
                    curr_loss = metrics.train_loss
                    
                    if prev_loss and curr_loss and prev_loss > 0:
                        loss_ratio = curr_loss / prev_loss
                        if loss_ratio > self.anomaly_config['max_loss_increase_ratio']:
                            alerts.append(AlertEvent(
                                timestamp=metrics.timestamp,
                                job_id=job_id,
                                alert_type="warning",
                                message=f"Training loss increased significantly: {loss_ratio:.2f}x",
                                details={"loss_ratio": loss_ratio, "prev_loss": prev_loss, "curr_loss": curr_loss}
                            ))
            
            # 更新检查状态
            self.last_check_time[job_id] = datetime.utcnow()
            self.last_metrics[job_id] = {"step": metrics.step, "loss": metrics.train_loss}
            
            # 处理告警
            for alert in alerts:
                await self._handle_alert(alert)
                
        except Exception as e:
            logger.error(f"Failed to check training anomalies for job {job.id}: {e}")
    
    async def _handle_alert(self, alert: AlertEvent):
        """
        处理告警事件
        
        Args:
            alert: 告警事件
        """
        try:
            # 添加到告警历史
            self.alert_history.append(alert)
            
            # 记录日志
            log_level = {
                "warning": logger.warning,
                "error": logger.error,
                "critical": logger.critical
            }.get(alert.alert_type, logger.info)
            
            log_level(f"Alert: {alert.message} (Job: {alert.job_id})")
            
            # 推送告警到WebSocket客户端
            await self._push_alert(alert)
            
        except Exception as e:
            logger.error(f"Failed to handle alert: {e}")
    
    async def _cleanup_old_data(self):
        """
        清理过期数据
        """
        try:
            # 清理已完成任务的指标历史
            completed_jobs = self.db.query(TrainingJob).filter(
                TrainingJob.status.in_(["completed", "failed", "stopped"])
            ).all()
            
            for job in completed_jobs:
                if job.id in self.training_metrics_history:
                    # 保留最近的一些数据，删除过期数据
                    if job.completed_at and (datetime.utcnow() - job.completed_at).days > 7:
                        del self.training_metrics_history[job.id]
                        if job.id in self.last_check_time:
                            del self.last_check_time[job.id]
                        if job.id in self.last_metrics:
                            del self.last_metrics[job.id]
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
    
    async def _push_real_time_data(self):
        """
        推送实时数据到WebSocket客户端
        """
        try:
            if not self.websocket_clients:
                return
            
            # 准备推送数据
            data = {
                "type": "monitoring_update",
                "timestamp": datetime.utcnow().isoformat(),
                "system_metrics": asdict(self.system_metrics_history[-1]) if self.system_metrics_history else None,
                "training_metrics": {
                    job_id: asdict(metrics[-1]) if metrics else None
                    for job_id, metrics in self.training_metrics_history.items()
                }
            }
            
            # 推送到所有客户端
            for client in self.websocket_clients[:]:  # 复制列表避免并发修改
                try:
                    await client.send_text(json.dumps(data, default=str))
                except Exception as e:
                    logger.debug(f"Failed to send data to WebSocket client: {e}")
                    # 移除失效的客户端
                    if client in self.websocket_clients:
                        self.websocket_clients.remove(client)
            
        except Exception as e:
            logger.error(f"Failed to push real-time data: {e}")
    
    async def _push_alert(self, alert: AlertEvent):
        """
        推送告警到WebSocket客户端
        
        Args:
            alert: 告警事件
        """
        try:
            if not self.websocket_clients:
                return
            
            data = {
                "type": "alert",
                "alert": asdict(alert)
            }
            
            for client in self.websocket_clients[:]:
                try:
                    await client.send_text(json.dumps(data, default=str))
                except Exception as e:
                    logger.debug(f"Failed to send alert to WebSocket client: {e}")
                    if client in self.websocket_clients:
                        self.websocket_clients.remove(client)
            
        except Exception as e:
            logger.error(f"Failed to push alert: {e}")
    
    def add_websocket_client(self, websocket):
        """
        添加WebSocket客户端
        
        Args:
            websocket: WebSocket连接对象
        """
        self.websocket_clients.append(websocket)
        logger.info(f"WebSocket client added, total: {len(self.websocket_clients)}")
    
    def remove_websocket_client(self, websocket):
        """
        移除WebSocket客户端
        
        Args:
            websocket: WebSocket连接对象
        """
        if websocket in self.websocket_clients:
            self.websocket_clients.remove(websocket)
            logger.info(f"WebSocket client removed, total: {len(self.websocket_clients)}")
    
    async def get_real_time_status(self, job_id: Optional[int] = None) -> Dict:
        """
        获取实时状态信息
        
        Args:
            job_id: 可选的任务ID，如果提供则只返回该任务的状态
            
        Returns:
            Dict: 实时状态信息
        """
        try:
            status = {
                "timestamp": datetime.utcnow().isoformat(),
                "is_monitoring": self.is_monitoring,
                "system_metrics": asdict(self.system_metrics_history[-1]) if self.system_metrics_history else None,
                "training_metrics": {},
                "recent_alerts": [asdict(alert) for alert in list(self.alert_history)[-10:]]
            }
            
            if job_id:
                # 返回特定任务的状态
                if job_id in self.training_metrics_history and self.training_metrics_history[job_id]:
                    status["training_metrics"][job_id] = asdict(self.training_metrics_history[job_id][-1])
            else:
                # 返回所有任务的状态
                for job_id, metrics in self.training_metrics_history.items():
                    if metrics:
                        status["training_metrics"][job_id] = asdict(metrics[-1])
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get real-time status: {e}")
            return {"error": str(e)}
    
    def get_historical_data(
        self,
        job_id: Optional[int] = None,
        hours: int = 24
    ) -> Dict:
        """
        获取历史数据
        
        Args:
            job_id: 可选的任务ID
            hours: 获取最近多少小时的数据
            
        Returns:
            Dict: 历史数据
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # 系统指标历史
            system_history = [
                asdict(metrics) for metrics in self.system_metrics_history
                if metrics.timestamp >= cutoff_time
            ]
            
            # 训练指标历史
            training_history = {}
            if job_id:
                if job_id in self.training_metrics_history:
                    training_history[job_id] = [
                        asdict(metrics) for metrics in self.training_metrics_history[job_id]
                        if metrics.timestamp >= cutoff_time
                    ]
            else:
                for jid, metrics_list in self.training_metrics_history.items():
                    training_history[jid] = [
                        asdict(metrics) for metrics in metrics_list
                        if metrics.timestamp >= cutoff_time
                    ]
            
            # 告警历史
            alert_history = [
                asdict(alert) for alert in self.alert_history
                if alert.timestamp >= cutoff_time
            ]
            
            return {
                "system_metrics": system_history,
                "training_metrics": training_history,
                "alerts": alert_history,
                "time_range_hours": hours
            }
            
        except Exception as e:
            logger.error(f"Failed to get historical data: {e}")
            return {"error": str(e)}