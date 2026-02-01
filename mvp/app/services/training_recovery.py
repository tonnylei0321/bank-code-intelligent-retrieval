"""
Training Recovery Service - 训练失败恢复和重试服务

本服务负责处理训练任务的失败恢复、检查点管理和智能重试。

主要功能：
    - 训练检查点管理
    - 失败原因分析
    - 智能重试策略
    - 数据完整性检查
    - 自动恢复建议

技术实现：
    - 检查点自动保存和恢复
    - 失败模式识别
    - 指数退避重试
    - 资源状态检查

使用示例：
    >>> from app.services.training_recovery import TrainingRecoveryService
    >>> recovery = TrainingRecoveryService(db_session)
    >>> 
    >>> # 分析失败原因
    >>> analysis = recovery.analyze_failure(job_id=1)
    >>> 
    >>> # 尝试恢复训练
    >>> success = recovery.attempt_recovery(job_id=1)
"""

import os
import json
import shutil
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import traceback

import torch
import psutil
from sqlalchemy.orm import Session
from loguru import logger

from app.models.training_job import TrainingJob
from app.models.dataset import Dataset


class FailureType(Enum):
    """失败类型枚举"""
    UNKNOWN = "unknown"
    OUT_OF_MEMORY = "out_of_memory"
    DISK_FULL = "disk_full"
    MODEL_LOADING_ERROR = "model_loading_error"
    DATA_LOADING_ERROR = "data_loading_error"
    CUDA_ERROR = "cuda_error"
    NETWORK_ERROR = "network_error"
    PERMISSION_ERROR = "permission_error"
    CONFIGURATION_ERROR = "configuration_error"
    TRAINING_DIVERGENCE = "training_divergence"
    CHECKPOINT_CORRUPTION = "checkpoint_corruption"


class RecoveryStrategy(Enum):
    """恢复策略枚举"""
    RETRY_SAME = "retry_same"
    REDUCE_BATCH_SIZE = "reduce_batch_size"
    REDUCE_MODEL_SIZE = "reduce_model_size"
    CLEAR_CACHE = "clear_cache"
    RESTART_FROM_CHECKPOINT = "restart_from_checkpoint"
    RECONFIGURE_PARAMETERS = "reconfigure_parameters"
    MANUAL_INTERVENTION = "manual_intervention"


class TrainingRecoveryService:
    """
    训练恢复服务
    
    负责训练任务的失败分析、恢复策略制定和自动重试。
    
    核心功能：
        1. 失败分析：
           - 错误日志分析
           - 失败模式识别
           - 根因分析
           - 影响评估
        
        2. 检查点管理：
           - 自动检查点保存
           - 检查点完整性验证
           - 检查点恢复
           - 增量备份
        
        3. 恢复策略：
           - 智能策略选择
           - 参数自动调整
           - 资源重新分配
           - 环境重置
        
        4. 重试机制：
           - 指数退避重试
           - 最大重试限制
           - 重试条件检查
           - 重试历史记录
    
    属性：
        db (Session): 数据库会话
        models_dir (Path): 模型存储目录
        checkpoints_dir (Path): 检查点存储目录
        max_retries (int): 最大重试次数
        retry_delays (List[int]): 重试延迟序列
    """
    
    def __init__(
        self,
        db: Session,
        models_dir: str = "models",
        checkpoints_dir: str = "checkpoints",
        max_retries: int = 3
    ):
        """
        初始化训练恢复服务
        
        Args:
            db: 数据库会话
            models_dir: 模型存储目录
            checkpoints_dir: 检查点存储目录
            max_retries: 最大重试次数
        """
        self.db = db
        self.models_dir = Path(models_dir)
        self.checkpoints_dir = Path(checkpoints_dir)
        self.max_retries = max_retries
        
        # 创建目录
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        
        # 重试延迟序列（指数退避）
        self.retry_delays = [60, 300, 900]  # 1分钟, 5分钟, 15分钟
        
        # 失败模式匹配规则
        self.failure_patterns = {
            FailureType.OUT_OF_MEMORY: [
                "out of memory", "cuda out of memory", "memory error",
                "allocation failed", "insufficient memory"
            ],
            FailureType.DISK_FULL: [
                "no space left", "disk full", "insufficient disk space",
                "write failed", "disk quota exceeded"
            ],
            FailureType.MODEL_LOADING_ERROR: [
                "model loading failed", "checkpoint not found",
                "invalid model", "model format error"
            ],
            FailureType.DATA_LOADING_ERROR: [
                "data loading failed", "dataset not found",
                "invalid data format", "data corruption"
            ],
            FailureType.CUDA_ERROR: [
                "cuda error", "gpu error", "device error",
                "cuda runtime error", "cublas error"
            ],
            FailureType.NETWORK_ERROR: [
                "network error", "connection failed", "timeout",
                "download failed", "http error"
            ],
            FailureType.PERMISSION_ERROR: [
                "permission denied", "access denied", "unauthorized",
                "file not accessible", "directory not writable"
            ],
            FailureType.CONFIGURATION_ERROR: [
                "configuration error", "invalid parameter", "config error",
                "argument error", "validation error"
            ],
            FailureType.TRAINING_DIVERGENCE: [
                "loss is nan", "loss diverged", "gradient explosion",
                "training unstable", "loss increased dramatically"
            ]
        }
        
        logger.info(f"TrainingRecoveryService initialized - Max retries: {max_retries}")
    
    def analyze_failure(self, job_id: int) -> Dict[str, Any]:
        """
        分析训练失败原因
        
        Args:
            job_id: 训练任务ID
            
        Returns:
            Dict: 失败分析结果
        """
        try:
            # 获取训练任务
            job = self.db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
            if not job:
                return {"error": f"Training job {job_id} not found"}
            
            if job.status != "failed":
                return {"error": f"Job {job_id} is not in failed status"}
            
            # 分析失败类型
            failure_type = self._identify_failure_type(job)
            
            # 分析系统状态
            system_status = self._check_system_status()
            
            # 分析检查点状态
            checkpoint_status = self._check_checkpoint_status(job_id)
            
            # 生成恢复建议
            recovery_suggestions = self._generate_recovery_suggestions(
                failure_type, system_status, checkpoint_status, job
            )
            
            analysis = {
                "job_id": job_id,
                "failure_type": failure_type.value,
                "error_message": job.error_message,
                "failure_time": job.completed_at.isoformat() if job.completed_at else None,
                "system_status": system_status,
                "checkpoint_status": checkpoint_status,
                "recovery_suggestions": recovery_suggestions,
                "can_retry": self._can_retry(job),
                "retry_count": self._get_retry_count(job),
                "max_retries": self.max_retries
            }
            
            logger.info(f"Failure analysis completed for job {job_id}: {failure_type.value}")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze failure for job {job_id}: {e}")
            return {"error": str(e)}
    
    def attempt_recovery(self, job_id: int, strategy: Optional[str] = None) -> Dict[str, Any]:
        """
        尝试恢复训练任务
        
        Args:
            job_id: 训练任务ID
            strategy: 指定的恢复策略（可选）
            
        Returns:
            Dict: 恢复结果
        """
        try:
            # 分析失败原因
            analysis = self.analyze_failure(job_id)
            if "error" in analysis:
                return analysis
            
            # 检查是否可以重试
            if not analysis["can_retry"]:
                return {
                    "success": False,
                    "message": f"Job {job_id} has exceeded maximum retry attempts ({self.max_retries})"
                }
            
            # 选择恢复策略
            if strategy:
                recovery_strategy = RecoveryStrategy(strategy)
            else:
                recovery_strategy = self._select_best_strategy(analysis)
            
            # 执行恢复策略
            recovery_result = self._execute_recovery_strategy(job_id, recovery_strategy, analysis)
            
            if recovery_result["success"]:
                # 更新任务状态为待重试
                job = self.db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
                if job:
                    job.status = "pending"
                    job.error_message = None
                    job.retry_count = (job.retry_count or 0) + 1
                    self.db.commit()
                
                logger.info(f"Recovery successful for job {job_id} using strategy {recovery_strategy.value}")
            
            return {
                "success": recovery_result["success"],
                "strategy": recovery_strategy.value,
                "message": recovery_result["message"],
                "details": recovery_result.get("details", {}),
                "job_id": job_id
            }
            
        except Exception as e:
            logger.error(f"Failed to attempt recovery for job {job_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def create_checkpoint(self, job_id: int, model_state: Dict, optimizer_state: Dict, epoch: int, step: int) -> bool:
        """
        创建训练检查点
        
        Args:
            job_id: 训练任务ID
            model_state: 模型状态字典
            optimizer_state: 优化器状态字典
            epoch: 当前轮次
            step: 当前步数
            
        Returns:
            bool: 是否成功创建检查点
        """
        try:
            checkpoint_dir = self.checkpoints_dir / f"job_{job_id}"
            checkpoint_dir.mkdir(parents=True, exist_ok=True)
            
            checkpoint_path = checkpoint_dir / f"checkpoint_epoch_{epoch}_step_{step}.pt"
            
            checkpoint_data = {
                "job_id": job_id,
                "epoch": epoch,
                "step": step,
                "model_state_dict": model_state,
                "optimizer_state_dict": optimizer_state,
                "timestamp": datetime.utcnow().isoformat(),
                "pytorch_version": torch.__version__
            }
            
            # 保存检查点
            torch.save(checkpoint_data, checkpoint_path)
            
            # 创建元数据文件
            metadata = {
                "job_id": job_id,
                "epoch": epoch,
                "step": step,
                "checkpoint_path": str(checkpoint_path),
                "created_at": datetime.utcnow().isoformat(),
                "file_size": checkpoint_path.stat().st_size
            }
            
            metadata_path = checkpoint_dir / f"metadata_epoch_{epoch}_step_{step}.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # 清理旧检查点（保留最近5个）
            self._cleanup_old_checkpoints(job_id, keep_count=5)
            
            logger.info(f"Checkpoint created for job {job_id} at epoch {epoch}, step {step}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create checkpoint for job {job_id}: {e}")
            return False
    
    def restore_from_checkpoint(self, job_id: int, checkpoint_path: Optional[str] = None) -> Optional[Dict]:
        """
        从检查点恢复训练状态
        
        Args:
            job_id: 训练任务ID
            checkpoint_path: 检查点路径（可选，默认使用最新检查点）
            
        Returns:
            Dict: 检查点数据，如果失败返回None
        """
        try:
            if checkpoint_path:
                checkpoint_file = Path(checkpoint_path)
            else:
                # 查找最新检查点
                checkpoint_file = self._find_latest_checkpoint(job_id)
            
            if not checkpoint_file or not checkpoint_file.exists():
                logger.warning(f"No checkpoint found for job {job_id}")
                return None
            
            # 验证检查点完整性
            if not self._verify_checkpoint_integrity(checkpoint_file):
                logger.error(f"Checkpoint integrity check failed: {checkpoint_file}")
                return None
            
            # 加载检查点
            checkpoint_data = torch.load(checkpoint_file, map_location='cpu')
            
            logger.info(f"Checkpoint restored for job {job_id} from {checkpoint_file}")
            return checkpoint_data
            
        except Exception as e:
            logger.error(f"Failed to restore checkpoint for job {job_id}: {e}")
            return None
    
    def _identify_failure_type(self, job: TrainingJob) -> FailureType:
        """
        识别失败类型
        
        Args:
            job: 训练任务对象
            
        Returns:
            FailureType: 失败类型
        """
        if not job.error_message:
            return FailureType.UNKNOWN
        
        error_message = job.error_message.lower()
        
        for failure_type, patterns in self.failure_patterns.items():
            for pattern in patterns:
                if pattern in error_message:
                    return failure_type
        
        return FailureType.UNKNOWN
    
    def _check_system_status(self) -> Dict[str, Any]:
        """
        检查系统状态
        
        Returns:
            Dict: 系统状态信息
        """
        try:
            # CPU和内存
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # GPU状态
            gpu_available = torch.cuda.is_available()
            gpu_count = torch.cuda.device_count() if gpu_available else 0
            gpu_memory_info = {}
            
            if gpu_available:
                for i in range(gpu_count):
                    gpu_memory_info[f"gpu_{i}"] = {
                        "allocated": torch.cuda.memory_allocated(i) / 1024**3,
                        "reserved": torch.cuda.memory_reserved(i) / 1024**3,
                        "total": torch.cuda.get_device_properties(i).total_memory / 1024**3
                    }
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / 1024**3,
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / 1024**3,
                "gpu_available": gpu_available,
                "gpu_count": gpu_count,
                "gpu_memory": gpu_memory_info,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to check system status: {e}")
            return {"error": str(e)}
    
    def _check_checkpoint_status(self, job_id: int) -> Dict[str, Any]:
        """
        检查检查点状态
        
        Args:
            job_id: 训练任务ID
            
        Returns:
            Dict: 检查点状态信息
        """
        try:
            checkpoint_dir = self.checkpoints_dir / f"job_{job_id}"
            
            if not checkpoint_dir.exists():
                return {"available": False, "count": 0}
            
            # 查找所有检查点文件
            checkpoint_files = list(checkpoint_dir.glob("checkpoint_*.pt"))
            metadata_files = list(checkpoint_dir.glob("metadata_*.json"))
            
            checkpoints = []
            for checkpoint_file in checkpoint_files:
                try:
                    # 检查文件完整性
                    is_valid = self._verify_checkpoint_integrity(checkpoint_file)
                    
                    # 获取文件信息
                    stat = checkpoint_file.stat()
                    
                    checkpoints.append({
                        "path": str(checkpoint_file),
                        "size_mb": stat.st_size / 1024**2,
                        "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "is_valid": is_valid
                    })
                except Exception as e:
                    logger.warning(f"Failed to check checkpoint {checkpoint_file}: {e}")
            
            # 按创建时间排序
            checkpoints.sort(key=lambda x: x["created_at"], reverse=True)
            
            return {
                "available": len(checkpoints) > 0,
                "count": len(checkpoints),
                "checkpoints": checkpoints,
                "latest_checkpoint": checkpoints[0] if checkpoints else None
            }
            
        except Exception as e:
            logger.error(f"Failed to check checkpoint status for job {job_id}: {e}")
            return {"error": str(e)}
    
    def _generate_recovery_suggestions(
        self,
        failure_type: FailureType,
        system_status: Dict,
        checkpoint_status: Dict,
        job: TrainingJob
    ) -> List[Dict[str, Any]]:
        """
        生成恢复建议
        
        Args:
            failure_type: 失败类型
            system_status: 系统状态
            checkpoint_status: 检查点状态
            job: 训练任务
            
        Returns:
            List[Dict]: 恢复建议列表
        """
        suggestions = []
        
        # 基于失败类型的建议
        if failure_type == FailureType.OUT_OF_MEMORY:
            suggestions.append({
                "strategy": RecoveryStrategy.REDUCE_BATCH_SIZE.value,
                "description": "Reduce batch size to decrease memory usage",
                "priority": "high",
                "estimated_success_rate": 0.8
            })
            suggestions.append({
                "strategy": RecoveryStrategy.CLEAR_CACHE.value,
                "description": "Clear GPU cache and restart training",
                "priority": "medium",
                "estimated_success_rate": 0.6
            })
        
        elif failure_type == FailureType.DISK_FULL:
            suggestions.append({
                "strategy": RecoveryStrategy.MANUAL_INTERVENTION.value,
                "description": "Free up disk space before retrying",
                "priority": "critical",
                "estimated_success_rate": 0.9
            })
        
        elif failure_type == FailureType.TRAINING_DIVERGENCE:
            suggestions.append({
                "strategy": RecoveryStrategy.RECONFIGURE_PARAMETERS.value,
                "description": "Reduce learning rate and adjust training parameters",
                "priority": "high",
                "estimated_success_rate": 0.7
            })
        
        elif failure_type == FailureType.CHECKPOINT_CORRUPTION:
            if checkpoint_status.get("count", 0) > 1:
                suggestions.append({
                    "strategy": RecoveryStrategy.RESTART_FROM_CHECKPOINT.value,
                    "description": "Restart from previous valid checkpoint",
                    "priority": "high",
                    "estimated_success_rate": 0.8
                })
        
        # 基于系统状态的建议
        if system_status.get("memory_percent", 0) > 85:
            suggestions.append({
                "strategy": RecoveryStrategy.CLEAR_CACHE.value,
                "description": "System memory usage is high, clear cache before retry",
                "priority": "medium",
                "estimated_success_rate": 0.6
            })
        
        # 通用建议
        if not suggestions:
            suggestions.append({
                "strategy": RecoveryStrategy.RETRY_SAME.value,
                "description": "Retry with same configuration (transient error)",
                "priority": "low",
                "estimated_success_rate": 0.3
            })
        
        return suggestions
    
    def _can_retry(self, job: TrainingJob) -> bool:
        """
        检查是否可以重试
        
        Args:
            job: 训练任务
            
        Returns:
            bool: 是否可以重试
        """
        retry_count = job.retry_count or 0
        return retry_count < self.max_retries
    
    def _get_retry_count(self, job: TrainingJob) -> int:
        """
        获取重试次数
        
        Args:
            job: 训练任务
            
        Returns:
            int: 重试次数
        """
        return job.retry_count or 0
    
    def _select_best_strategy(self, analysis: Dict) -> RecoveryStrategy:
        """
        选择最佳恢复策略
        
        Args:
            analysis: 失败分析结果
            
        Returns:
            RecoveryStrategy: 最佳恢复策略
        """
        suggestions = analysis.get("recovery_suggestions", [])
        
        if not suggestions:
            return RecoveryStrategy.RETRY_SAME
        
        # 选择优先级最高且成功率最高的策略
        best_suggestion = max(
            suggestions,
            key=lambda x: (
                {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(x["priority"], 0),
                x.get("estimated_success_rate", 0)
            )
        )
        
        return RecoveryStrategy(best_suggestion["strategy"])
    
    def _execute_recovery_strategy(
        self,
        job_id: int,
        strategy: RecoveryStrategy,
        analysis: Dict
    ) -> Dict[str, Any]:
        """
        执行恢复策略
        
        Args:
            job_id: 训练任务ID
            strategy: 恢复策略
            analysis: 失败分析结果
            
        Returns:
            Dict: 执行结果
        """
        try:
            job = self.db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
            if not job:
                return {"success": False, "message": f"Job {job_id} not found"}
            
            if strategy == RecoveryStrategy.REDUCE_BATCH_SIZE:
                # 减少批次大小
                new_batch_size = max(1, job.batch_size // 2)
                job.batch_size = new_batch_size
                self.db.commit()
                
                return {
                    "success": True,
                    "message": f"Reduced batch size from {job.batch_size * 2} to {new_batch_size}",
                    "details": {"old_batch_size": job.batch_size * 2, "new_batch_size": new_batch_size}
                }
            
            elif strategy == RecoveryStrategy.CLEAR_CACHE:
                # 清理缓存
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    torch.mps.empty_cache()
                
                return {
                    "success": True,
                    "message": "GPU cache cleared successfully"
                }
            
            elif strategy == RecoveryStrategy.RECONFIGURE_PARAMETERS:
                # 重新配置参数
                job.learning_rate = job.learning_rate * 0.5  # 减半学习率
                job.lora_dropout = min(0.2, job.lora_dropout * 1.5)  # 增加dropout
                self.db.commit()
                
                return {
                    "success": True,
                    "message": "Training parameters reconfigured",
                    "details": {
                        "new_learning_rate": job.learning_rate,
                        "new_lora_dropout": job.lora_dropout
                    }
                }
            
            elif strategy == RecoveryStrategy.RESTART_FROM_CHECKPOINT:
                # 从检查点重启
                checkpoint_data = self.restore_from_checkpoint(job_id)
                if checkpoint_data:
                    job.current_epoch = checkpoint_data.get("epoch", 0)
                    job.current_step = checkpoint_data.get("step", 0)
                    self.db.commit()
                    
                    return {
                        "success": True,
                        "message": f"Will restart from checkpoint at epoch {job.current_epoch}",
                        "details": {"epoch": job.current_epoch, "step": job.current_step}
                    }
                else:
                    return {
                        "success": False,
                        "message": "No valid checkpoint found for recovery"
                    }
            
            elif strategy == RecoveryStrategy.RETRY_SAME:
                # 直接重试
                return {
                    "success": True,
                    "message": "Will retry with same configuration"
                }
            
            else:
                return {
                    "success": False,
                    "message": f"Recovery strategy {strategy.value} requires manual intervention"
                }
            
        except Exception as e:
            logger.error(f"Failed to execute recovery strategy {strategy.value} for job {job_id}: {e}")
            return {"success": False, "message": str(e)}
    
    def _find_latest_checkpoint(self, job_id: int) -> Optional[Path]:
        """
        查找最新的检查点文件
        
        Args:
            job_id: 训练任务ID
            
        Returns:
            Path: 最新检查点文件路径，如果不存在返回None
        """
        try:
            checkpoint_dir = self.checkpoints_dir / f"job_{job_id}"
            if not checkpoint_dir.exists():
                return None
            
            checkpoint_files = list(checkpoint_dir.glob("checkpoint_*.pt"))
            if not checkpoint_files:
                return None
            
            # 按修改时间排序，返回最新的
            latest_checkpoint = max(checkpoint_files, key=lambda p: p.stat().st_mtime)
            return latest_checkpoint
            
        except Exception as e:
            logger.error(f"Failed to find latest checkpoint for job {job_id}: {e}")
            return None
    
    def _verify_checkpoint_integrity(self, checkpoint_path: Path) -> bool:
        """
        验证检查点文件完整性
        
        Args:
            checkpoint_path: 检查点文件路径
            
        Returns:
            bool: 是否完整
        """
        try:
            # 检查文件是否存在且不为空
            if not checkpoint_path.exists() or checkpoint_path.stat().st_size == 0:
                return False
            
            # 尝试加载检查点
            checkpoint_data = torch.load(checkpoint_path, map_location='cpu')
            
            # 检查必需字段
            required_fields = ["job_id", "epoch", "step", "model_state_dict"]
            for field in required_fields:
                if field not in checkpoint_data:
                    return False
            
            return True
            
        except Exception as e:
            logger.debug(f"Checkpoint integrity check failed for {checkpoint_path}: {e}")
            return False
    
    def _cleanup_old_checkpoints(self, job_id: int, keep_count: int = 5):
        """
        清理旧的检查点文件
        
        Args:
            job_id: 训练任务ID
            keep_count: 保留的检查点数量
        """
        try:
            checkpoint_dir = self.checkpoints_dir / f"job_{job_id}"
            if not checkpoint_dir.exists():
                return
            
            # 获取所有检查点文件
            checkpoint_files = list(checkpoint_dir.glob("checkpoint_*.pt"))
            metadata_files = list(checkpoint_dir.glob("metadata_*.json"))
            
            # 按修改时间排序
            checkpoint_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            metadata_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            
            # 删除多余的检查点文件
            for checkpoint_file in checkpoint_files[keep_count:]:
                try:
                    checkpoint_file.unlink()
                    logger.debug(f"Deleted old checkpoint: {checkpoint_file}")
                except Exception as e:
                    logger.warning(f"Failed to delete checkpoint {checkpoint_file}: {e}")
            
            # 删除多余的元数据文件
            for metadata_file in metadata_files[keep_count:]:
                try:
                    metadata_file.unlink()
                    logger.debug(f"Deleted old metadata: {metadata_file}")
                except Exception as e:
                    logger.warning(f"Failed to delete metadata {metadata_file}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old checkpoints for job {job_id}: {e}")