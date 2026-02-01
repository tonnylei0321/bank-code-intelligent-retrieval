#!/usr/bin/env python3
"""
智能训练参数优化器
根据数据集大小、模型类型、硬件限制等因素自动计算最优训练参数
"""

import math
import psutil
import torch
from typing import Dict, Any, Tuple, List
from loguru import logger
from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.models.qa_pair import QAPair


class TrainingOptimizer:
    """
    智能训练参数优化器
    
    根据以下因素自动调优训练参数：
    1. 数据集大小和质量
    2. 模型类型和参数量
    3. 硬件资源限制（内存、GPU）
    4. 训练目标和时间约束
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.device = self._detect_device()
        self.memory_info = self._get_memory_info()
        
        # 模型规格配置
        self.model_specs = {
            "Qwen/Qwen2.5-0.5B": {
                "params": 0.5e9,
                "memory_base": 2.0,  # GB
                "memory_per_batch": 0.1,  # GB per batch item
                "recommended_lr": 2e-4,
                "max_batch_size": 32
            },
            "Qwen/Qwen2.5-1.5B": {
                "params": 1.5e9,
                "memory_base": 6.0,  # GB
                "memory_per_batch": 0.3,  # GB per batch item
                "recommended_lr": 1e-4,
                "max_batch_size": 16
            },
            "Qwen/Qwen2.5-3B": {
                "params": 3e9,
                "memory_base": 12.0,  # GB
                "memory_per_batch": 0.6,  # GB per batch item
                "recommended_lr": 5e-5,
                "max_batch_size": 8
            }
        }
    
    def _detect_device(self) -> str:
        """检测可用设备"""
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"
    
    def _get_memory_info(self) -> Dict[str, float]:
        """获取内存信息"""
        memory = psutil.virtual_memory()
        info = {
            "total_gb": memory.total / (1024**3),
            "available_gb": memory.available / (1024**3),
            "used_percent": memory.percent
        }
        
        # GPU/MPS内存信息
        if self.device == "cuda":
            gpu_memory = torch.cuda.get_device_properties(0).total_memory
            info["gpu_total_gb"] = gpu_memory / (1024**3)
            info["gpu_available_gb"] = info["gpu_total_gb"] * 0.8  # 保守估计
        elif self.device == "mps":
            # MPS内存限制（macOS）
            info["gpu_total_gb"] = 8.29  # MPS典型限制
            info["gpu_available_gb"] = 6.0   # 保守估计
        
        return info
    
    def _analyze_dataset(self, dataset_id: int) -> Dict[str, Any]:
        """分析数据集特征"""
        # 获取数据集信息
        dataset = self.db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        # 统计QA对数量和类型
        qa_pairs = self.db.query(QAPair).filter(QAPair.dataset_id == dataset_id).all()
        
        total_samples = len(qa_pairs)
        question_types = {}
        avg_question_length = 0
        avg_answer_length = 0
        
        for qa in qa_pairs:
            # 统计问题类型
            q_type = qa.question_type or "unknown"
            question_types[q_type] = question_types.get(q_type, 0) + 1
            
            # 计算平均长度
            if qa.question:
                avg_question_length += len(qa.question)
            if qa.answer:
                avg_answer_length += len(qa.answer)
        
        if total_samples > 0:
            avg_question_length /= total_samples
            avg_answer_length /= total_samples
        
        return {
            "total_samples": total_samples,
            "question_types": question_types,
            "avg_question_length": avg_question_length,
            "avg_answer_length": avg_answer_length,
            "avg_total_length": avg_question_length + avg_answer_length,
            "complexity_score": self._calculate_complexity_score(question_types, avg_question_length + avg_answer_length)
        }
    
    def _calculate_complexity_score(self, question_types: Dict[str, int], avg_length: float) -> float:
        """计算数据集复杂度评分 (0-1)"""
        # 基于问题类型多样性
        type_diversity = len(question_types) / max(len(question_types), 3)  # 最多3种类型
        
        # 基于平均长度
        length_complexity = min(avg_length / 200, 1.0)  # 200字符为基准
        
        # 综合评分
        return (type_diversity * 0.4 + length_complexity * 0.6)
    
    def optimize_training_parameters(
        self, 
        model_name: str, 
        dataset_id: int,
        target_training_time_hours: float = 24.0,  # 目标训练时间
        memory_safety_factor: float = 0.8  # 内存安全系数
    ) -> Dict[str, Any]:
        """
        智能优化训练参数
        
        Args:
            model_name: 模型名称
            dataset_id: 数据集ID
            target_training_time_hours: 目标训练时间（小时）
            memory_safety_factor: 内存安全系数 (0-1)
        
        Returns:
            优化后的训练参数字典
        """
        logger.info(f"开始优化训练参数: 模型={model_name}, 数据集={dataset_id}")
        
        # 1. 分析数据集
        dataset_info = self._analyze_dataset(dataset_id)
        logger.info(f"数据集分析: {dataset_info['total_samples']}样本, 复杂度={dataset_info['complexity_score']:.2f}")
        
        # 2. 获取模型规格
        if model_name not in self.model_specs:
            logger.warning(f"未知模型 {model_name}, 使用默认配置")
            model_spec = self.model_specs["Qwen/Qwen2.5-0.5B"]
        else:
            model_spec = self.model_specs[model_name]
        
        # 3. 计算最优batch_size
        optimal_batch_size = self._calculate_optimal_batch_size(
            model_spec, dataset_info, memory_safety_factor
        )
        
        # 4. 计算最优epochs
        optimal_epochs = self._calculate_optimal_epochs(
            dataset_info, target_training_time_hours, optimal_batch_size
        )
        
        # 5. 计算最优学习率
        optimal_lr = self._calculate_optimal_learning_rate(
            model_spec, dataset_info, optimal_batch_size
        )
        
        # 6. 计算LoRA参数
        lora_params = self._calculate_optimal_lora_params(
            model_spec, dataset_info
        )
        
        # 7. 计算其他优化参数
        other_params = self._calculate_other_params(
            dataset_info, optimal_batch_size, optimal_epochs
        )
        
        # 8. 组装最终参数
        optimized_params = {
            # 基础参数
            "epochs": optimal_epochs,
            "batch_size": optimal_batch_size,
            "learning_rate": optimal_lr,
            
            # LoRA参数
            "lora_r": lora_params["r"],
            "lora_alpha": lora_params["alpha"],
            "lora_dropout": lora_params["dropout"],
            
            # 优化参数
            "gradient_accumulation_steps": other_params["gradient_accumulation_steps"],
            "warmup_steps": other_params["warmup_steps"],
            "weight_decay": other_params["weight_decay"],
            "max_grad_norm": other_params["max_grad_norm"],
            
            # 预估信息
            "estimated_training_time_hours": self._estimate_training_time(
                dataset_info["total_samples"], optimal_batch_size, optimal_epochs
            ),
            "estimated_memory_usage_gb": self._estimate_memory_usage(
                model_spec, optimal_batch_size
            ),
            
            # 优化说明
            "optimization_notes": self._generate_optimization_notes(
                dataset_info, model_spec, optimal_batch_size, optimal_epochs
            )
        }
        
        logger.info(f"参数优化完成: batch_size={optimal_batch_size}, epochs={optimal_epochs}, lr={optimal_lr}")
        return optimized_params
    
    def _calculate_optimal_batch_size(
        self, 
        model_spec: Dict[str, Any], 
        dataset_info: Dict[str, Any],
        memory_safety_factor: float
    ) -> int:
        """计算最优batch_size"""
        # 基于内存限制计算最大batch_size
        available_memory = self.memory_info.get("gpu_available_gb", 4.0) * memory_safety_factor
        memory_per_batch = model_spec["memory_per_batch"]
        memory_base = model_spec["memory_base"]
        
        max_batch_by_memory = int((available_memory - memory_base) / memory_per_batch)
        max_batch_by_model = model_spec["max_batch_size"]
        
        # 取较小值
        max_batch_size = min(max_batch_by_memory, max_batch_by_model)
        
        # 基于数据集大小调整
        total_samples = dataset_info["total_samples"]
        
        if total_samples < 1000:
            # 小数据集，使用较小batch_size避免过拟合
            optimal_batch = min(max_batch_size, 4)
        elif total_samples < 10000:
            # 中等数据集
            optimal_batch = min(max_batch_size, 8)
        else:
            # 大数据集，可以使用较大batch_size
            optimal_batch = max_batch_size
        
        # 确保至少为1
        return max(1, optimal_batch)
    
    def _calculate_optimal_epochs(
        self, 
        dataset_info: Dict[str, Any], 
        target_hours: float,
        batch_size: int
    ) -> int:
        """计算最优epochs数"""
        total_samples = dataset_info["total_samples"]
        complexity_score = dataset_info["complexity_score"]
        
        # 基于数据集大小的基础epochs
        if total_samples < 1000:
            base_epochs = 5  # 小数据集需要更多epochs
        elif total_samples < 10000:
            base_epochs = 3  # 中等数据集
        else:
            base_epochs = 2  # 大数据集，避免过拟合
        
        # 基于复杂度调整
        complexity_factor = 1 + complexity_score * 0.5  # 复杂数据需要更多训练
        adjusted_epochs = int(base_epochs * complexity_factor)
        
        # 基于时间约束调整
        estimated_time_per_epoch = self._estimate_time_per_epoch(total_samples, batch_size)
        max_epochs_by_time = int(target_hours / estimated_time_per_epoch) if estimated_time_per_epoch > 0 else adjusted_epochs
        
        # 取较小值，但至少1个epoch
        optimal_epochs = max(1, min(adjusted_epochs, max_epochs_by_time))
        
        return optimal_epochs
    
    def _calculate_optimal_learning_rate(
        self, 
        model_spec: Dict[str, Any], 
        dataset_info: Dict[str, Any],
        batch_size: int
    ) -> float:
        """计算最优学习率"""
        base_lr = model_spec["recommended_lr"]
        total_samples = dataset_info["total_samples"]
        
        # 基于batch_size调整学习率（线性缩放规则）
        batch_factor = math.sqrt(batch_size / 8)  # 以batch_size=8为基准
        
        # 基于数据集大小调整
        if total_samples < 1000:
            size_factor = 0.5  # 小数据集使用较小学习率
        elif total_samples < 10000:
            size_factor = 0.8  # 中等数据集
        else:
            size_factor = 1.0  # 大数据集
        
        # 基于设备类型调整
        device_factor = 0.8 if self.device == "mps" else 1.0  # MPS稍微保守一些
        
        optimal_lr = base_lr * batch_factor * size_factor * device_factor
        
        # 确保在合理范围内
        return max(1e-5, min(1e-3, optimal_lr))
    
    def _calculate_optimal_lora_params(
        self, 
        model_spec: Dict[str, Any], 
        dataset_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """计算最优LoRA参数"""
        total_samples = dataset_info["total_samples"]
        complexity_score = dataset_info["complexity_score"]
        
        # 基于数据集大小和复杂度调整LoRA参数
        if total_samples < 1000:
            # 小数据集，使用较小的LoRA参数避免过拟合
            base_r = 4
            base_alpha = 8
        elif total_samples < 10000:
            # 中等数据集
            base_r = 8
            base_alpha = 16
        else:
            # 大数据集，可以使用较大的LoRA参数
            base_r = 16
            base_alpha = 32
        
        # 基于复杂度微调
        complexity_factor = 1 + complexity_score * 0.5
        optimal_r = int(base_r * complexity_factor)
        optimal_alpha = int(base_alpha * complexity_factor)
        
        # 确保在合理范围内
        optimal_r = max(4, min(64, optimal_r))
        optimal_alpha = max(8, min(128, optimal_alpha))
        
        # dropout基于数据集大小调整
        if total_samples < 1000:
            dropout = 0.1  # 小数据集需要更多正则化
        else:
            dropout = 0.05  # 大数据集可以减少dropout
        
        return {
            "r": optimal_r,
            "alpha": optimal_alpha,
            "dropout": dropout
        }
    
    def _calculate_other_params(
        self, 
        dataset_info: Dict[str, Any], 
        batch_size: int,
        epochs: int
    ) -> Dict[str, Any]:
        """计算其他优化参数"""
        total_samples = dataset_info["total_samples"]
        
        # 梯度累积步数（用于模拟更大的batch_size）
        if batch_size < 8:
            gradient_accumulation_steps = 8 // batch_size
        else:
            gradient_accumulation_steps = 1
        
        # 预热步数
        steps_per_epoch = total_samples // batch_size
        total_steps = steps_per_epoch * epochs
        warmup_steps = min(100, total_steps // 10)  # 10%的步数用于预热，最多100步
        
        # 权重衰减
        weight_decay = 0.01 if total_samples > 1000 else 0.001
        
        # 梯度裁剪
        max_grad_norm = 1.0
        
        return {
            "gradient_accumulation_steps": gradient_accumulation_steps,
            "warmup_steps": warmup_steps,
            "weight_decay": weight_decay,
            "max_grad_norm": max_grad_norm
        }
    
    def _estimate_training_time(self, total_samples: int, batch_size: int, epochs: int) -> float:
        """估算训练时间（小时）"""
        steps_per_epoch = total_samples // batch_size
        total_steps = steps_per_epoch * epochs
        
        # 基于设备类型估算每步时间
        if self.device == "cuda":
            seconds_per_step = 0.5  # GPU较快
        elif self.device == "mps":
            seconds_per_step = 1.0  # MPS中等
        else:
            seconds_per_step = 3.0  # CPU较慢
        
        total_seconds = total_steps * seconds_per_step
        return total_seconds / 3600  # 转换为小时
    
    def _estimate_memory_usage(self, model_spec: Dict[str, Any], batch_size: int) -> float:
        """估算内存使用量（GB）"""
        base_memory = model_spec["memory_base"]
        batch_memory = model_spec["memory_per_batch"] * batch_size
        return base_memory + batch_memory
    
    def _estimate_time_per_epoch(self, total_samples: int, batch_size: int) -> float:
        """估算每个epoch的时间（小时）"""
        steps_per_epoch = total_samples // batch_size
        
        if self.device == "cuda":
            seconds_per_step = 0.5
        elif self.device == "mps":
            seconds_per_step = 1.0
        else:
            seconds_per_step = 3.0
        
        epoch_seconds = steps_per_epoch * seconds_per_step
        return epoch_seconds / 3600
    
    def _generate_optimization_notes(
        self, 
        dataset_info: Dict[str, Any], 
        model_spec: Dict[str, Any],
        batch_size: int, 
        epochs: int
    ) -> List[str]:
        """生成优化说明"""
        notes = []
        
        total_samples = dataset_info["total_samples"]
        
        # 数据集大小相关建议
        if total_samples < 1000:
            notes.append("小数据集：使用较多epochs和较小batch_size，增加正则化")
        elif total_samples > 50000:
            notes.append("大数据集：使用较少epochs避免过拟合，可以使用较大batch_size")
        
        # 内存相关建议
        estimated_memory = self._estimate_memory_usage(model_spec, batch_size)
        available_memory = self.memory_info.get("gpu_available_gb", 4.0)
        
        if estimated_memory > available_memory * 0.9:
            notes.append("内存使用接近上限，建议减少batch_size或使用梯度累积")
        
        # 设备相关建议
        if self.device == "mps":
            notes.append("MPS设备：已优化内存使用，禁用多进程数据加载")
        elif self.device == "cpu":
            notes.append("CPU训练：速度较慢，建议使用较小的模型和数据集")
        
        # 训练时间建议
        estimated_time = self._estimate_training_time(total_samples, batch_size, epochs)
        if estimated_time > 48:
            notes.append(f"预计训练时间较长({estimated_time:.1f}小时)，建议减少epochs或数据量")
        
        return notes


def optimize_training_parameters_for_job(
    db: Session,
    model_name: str,
    dataset_id: int,
    target_hours: float = 24.0
) -> Dict[str, Any]:
    """
    为训练任务优化参数的便捷函数
    
    Args:
        db: 数据库会话
        model_name: 模型名称
        dataset_id: 数据集ID
        target_hours: 目标训练时间（小时）
    
    Returns:
        优化后的参数字典
    """
    optimizer = TrainingOptimizer(db)
    return optimizer.optimize_training_parameters(
        model_name=model_name,
        dataset_id=dataset_id,
        target_training_time_hours=target_hours
    )