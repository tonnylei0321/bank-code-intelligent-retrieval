"""
Model Trainer Service - 模型训练服务

本服务负责使用LoRA微调技术在Qwen基础模型上进行模型训练。

主要功能：
    - 加载Qwen系列基础模型（支持多种规格）
    - 配置LoRA参数进行高效微调
    - 从数据库加载问答对数据进行训练
    - 实时跟踪训练进度和指标
    - 保存训练好的模型权重
    - 异常检测和日志记录

技术栈：
    - transformers: HuggingFace模型加载和训练
    - peft: LoRA参数高效微调
    - torch: PyTorch深度学习框架
    - datasets: HuggingFace数据集处理

使用示例：
    >>> from app.services.model_trainer import ModelTrainer
    >>> trainer = ModelTrainer(db_session)
    >>> 
    >>> # 训练模型
    >>> results = trainer.train_model(
    ...     job_id=1,
    ...     progress_callback=lambda job_id, data: print(f"Progress: {data['progress']:.1f}%")
    ... )
    >>> 
    >>> # 停止训练
    >>> trainer.stop_training(job_id=1)

LoRA微调说明：
    LoRA (Low-Rank Adaptation) 是一种参数高效的微调方法，通过在模型的注意力层
    添加低秩矩阵来实现微调，大幅减少可训练参数数量和显存占用。
    
    典型配置：
    - lora_r: 16 (秩，控制参数量)
    - lora_alpha: 32 (缩放因子)
    - lora_dropout: 0.05 (防止过拟合)
    - target_modules: ["q_proj", "k_proj", "v_proj", "o_proj"] (目标层)
"""
import os
import gc
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset as HFDataset
from sqlalchemy.orm import Session
from loguru import logger

from app.models.training_job import TrainingJob
from app.models.qa_pair import QAPair
from app.models.dataset import Dataset


class TrainingError(Exception):
    """
    训练异常基类
    
    用于标识模型训练过程中的所有错误，包括：
    - 模型加载失败
    - LoRA配置错误
    - 数据准备失败
    - 训练过程异常
    - 模型保存失败
    """
    pass


class ModelTrainer:
    """
    模型训练器服务 - 使用LoRA进行模型微调
    
    本类负责整个模型训练流程，从模型加载、数据准备到训练执行和模型保存。
    支持GPU和CPU训练，自动检测可用设备。
    
    核心功能：
        1. 模型管理：
           - 加载HuggingFace预训练模型
           - 配置LoRA参数进行高效微调
           - 保存训练好的模型权重
        
        2. 数据处理：
           - 从数据库加载问答对数据
           - 转换为HuggingFace Dataset格式
           - 自动分词和填充
        
        3. 训练控制：
           - 支持多轮训练（epochs）
           - 实时跟踪训练进度
           - 验证集评估
           - 异常检测（loss波动监控）
        
        4. 进度跟踪：
           - 实时更新训练状态到数据库
           - 记录训练日志
           - 支持进度回调函数
           - 自动保存最佳模型
    
    属性：
        db (Session): 数据库会话对象
        models_dir (Path): 模型保存目录
        device (str): 训练设备（"cuda"或"cpu"）
    
    训练流程：
        1. 创建TrainingJob记录
        2. 调用train_model()开始训练
        3. 自动加载模型和数据
        4. 执行训练循环
        5. 保存模型和结果
    
    异常检测：
        - 监控训练loss的波动情况
        - 如果连续3个epoch的loss波动超过50%，发出警告
        - 帮助及时发现训练不稳定的情况
    """
    
    def __init__(
        self,
        db: Session,
        models_dir: str = "models"
    ):
        """
        初始化模型训练器
        
        Args:
            db (Session): SQLAlchemy数据库会话对象，用于访问训练任务和数据
            models_dir (str): 模型保存目录路径，默认为"models"
                训练好的模型将保存在此目录下的job_{job_id}子目录中
        
        说明：
            - 自动检测GPU可用性，优先使用CUDA加速
            - 如果没有GPU，自动降级到CPU训练
            - 自动创建模型保存目录（如果不存在）
            - 初始化时会记录设备信息到日志
        """
        self.db = db
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查设备可用性（优先使用GPU）
        # M1/M2/M3 Mac支持MPS (Metal Performance Shaders)加速
        if torch.cuda.is_available():
            self.device = "cuda"
            logger.info("Using CUDA GPU for training")
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            # 使用MPS加速（Apple Silicon GPU）
            self.device = "mps"
            # 启用MPS fallback以处理不支持的操作
            os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
            logger.info("Using MPS (Apple Silicon GPU) for training")
        else:
            self.device = "cpu"
            logger.info("Using CPU for training")
        
        logger.info(f"ModelTrainer initialized - Device: {self.device}")
    
    def load_base_model(
        self,
        model_name: str = "Qwen/Qwen2.5-0.5B"
    ) -> tuple:
        """
        加载基础模型和分词器
        
        从HuggingFace Hub加载预训练的Qwen模型和对应的分词器。
        
        Args:
            model_name (str): HuggingFace模型名称，默认为"Qwen/Qwen2.5-0.5B"
                支持的模型包括：
                - Qwen/Qwen2.5-0.5B (0.5B参数，适合快速实验)
                - Qwen/Qwen2.5-1.5B (1.5B参数，平衡性能和速度)
                - Qwen/Qwen2.5-3B (3B参数，更好的性能)
                - Qwen/Qwen2.5-7B (7B参数，最佳性能)
        
        Returns:
            tuple: (model, tokenizer) 元组
                - model: 加载的因果语言模型
                - tokenizer: 对应的分词器
        
        Raises:
            TrainingError: 模型加载失败时抛出
        
        技术细节：
            - 使用trust_remote_code=True允许执行模型自定义代码
            - GPU训练时使用float16精度以节省显存
            - CPU训练时使用float32精度保证稳定性
            - 自动设置pad_token（如果不存在则使用eos_token）
            - GPU训练时使用device_map="auto"自动分配设备
        """
        try:
            logger.info(f"Loading base model: {model_name}")
            
            # 加载分词器
            tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                trust_remote_code=True,
                padding_side="right"  # 右侧填充，适合因果语言模型
            )
            
            # 设置pad_token（如果不存在）
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            
            # 加载模型 - 针对MPS/GPU优化
            logger.info("Loading model with memory optimization...")
            
            # 根据设备选择合适的数据类型和配置
            if self.device == "cuda":
                # CUDA GPU: 使用float16和自动设备映射
                torch_dtype = torch.float16
                device_map = "auto"
            elif self.device == "mps":
                # MPS (Apple Silicon): 使用float32（MPS对float16支持有限）
                torch_dtype = torch.float32
                device_map = None  # MPS不支持device_map
            else:
                # CPU: 使用float32
                torch_dtype = torch.float32
                device_map = None
            
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                trust_remote_code=True,
                torch_dtype=torch_dtype,
                device_map=device_map,
                low_cpu_mem_usage=True,  # 减少CPU内存使用
                use_cache=False  # 禁用KV缓存以节省内存
            )
            
            # 如果是MPS，手动移动模型到MPS设备
            if self.device == "mps":
                model = model.to(self.device)
            
            # 设置模型为训练模式并禁用梯度检查点以外的缓存
            model.config.use_cache = False
            
            logger.info(f"Base model loaded successfully with low memory mode")
            return model, tokenizer
        
        except Exception as e:
            logger.error(f"Failed to load base model: {e}")
            raise TrainingError(f"Model loading failed: {e}")
    
    def configure_lora(
        self,
        model,
        lora_r: int = 16,
        lora_alpha: int = 32,
        lora_dropout: float = 0.05
    ):
        """
        为模型配置LoRA参数高效微调
        
        LoRA通过在模型的注意力层添加低秩矩阵来实现微调，大幅减少可训练参数数量。
        
        Args:
            model: 基础模型对象
            lora_r (int): LoRA秩（rank），控制低秩矩阵的维度
                - 较小的值（8-16）：参数更少，训练更快，但表达能力有限
                - 较大的值（32-64）：参数更多，表达能力更强，但训练较慢
                - 默认16是一个平衡的选择
            lora_alpha (int): LoRA缩放因子，控制LoRA层的影响程度
                - 通常设置为lora_r的2倍
                - 默认32（配合lora_r=16）
            lora_dropout (float): Dropout比例，用于防止过拟合
                - 范围0.0-1.0
                - 默认0.05（5%）
        
        Returns:
            model: 配置了LoRA的模型对象
        
        Raises:
            TrainingError: LoRA配置失败时抛出
        
        技术细节：
            - 任务类型：CAUSAL_LM（因果语言模型）
            - 目标模块：根据模型类型自动选择合适的注意力层
            - bias设置为"none"，不训练偏置项
            - 配置后会打印可训练参数占比
        
        支持的模型类型：
            - GPT-2: c_attn, c_proj
            - Qwen: q_proj, k_proj, v_proj, o_proj
            - LLaMA: q_proj, k_proj, v_proj, o_proj
        """
        try:
            logger.info(f"Configuring LoRA - r={lora_r}, alpha={lora_alpha}, dropout={lora_dropout}")
            
            # 根据模型类型选择目标模块
            model_type = model.config.model_type.lower()
            logger.info(f"Detected model type: {model_type}")
            
            if model_type == "gpt2":
                # GPT-2模型使用c_attn和c_proj
                target_modules = ["c_attn", "c_proj"]
            elif model_type in ["qwen", "qwen2"]:
                # Qwen模型使用q_proj, k_proj, v_proj, o_proj
                target_modules = ["q_proj", "k_proj", "v_proj", "o_proj"]
            elif model_type in ["llama", "llama2"]:
                # LLaMA模型使用q_proj, k_proj, v_proj, o_proj
                target_modules = ["q_proj", "k_proj", "v_proj", "o_proj"]
            else:
                # 默认尝试常见的注意力模块名称
                logger.warning(f"Unknown model type {model_type}, using default target modules")
                target_modules = ["c_attn", "c_proj"]  # 默认使用GPT-2风格
            
            logger.info(f"Using target modules: {target_modules}")
            
            # LoRA配置
            lora_config = LoraConfig(
                task_type=TaskType.CAUSAL_LM,  # 因果语言模型任务
                r=lora_r,  # 秩
                lora_alpha=lora_alpha,  # 缩放因子
                lora_dropout=lora_dropout,  # Dropout比例
                target_modules=target_modules,  # 根据模型类型选择的目标模块
                bias="none"  # 不训练偏置
            )
            
            # 将LoRA应用到模型
            model = get_peft_model(model, lora_config)
            
            # 打印可训练参数统计
            trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
            total_params = sum(p.numel() for p in model.parameters())
            logger.info(
                f"LoRA configured - Trainable params: {trainable_params:,} / {total_params:,} "
                f"({100 * trainable_params / total_params:.2f}%)"
            )
            
            return model
        
        except Exception as e:
            logger.error(f"Failed to configure LoRA: {e}")
            raise TrainingError(f"LoRA configuration failed: {e}")
    
    def prepare_training_data(
        self,
        dataset_id: int,
        tokenizer,
        max_length: int = 256  # 从512降低到256以节省内存
    ) -> Dict[str, HFDataset]:
        """
        从数据库准备训练数据
        
        本方法从数据库加载问答对数据，转换为HuggingFace Dataset格式，并进行分词处理。
        
        Args:
            dataset_id (int): 数据集ID
            tokenizer: 分词器对象
            max_length (int): 最大序列长度，默认512
                - 超过此长度的文本将被截断
                - 短于此长度的文本将被填充
        
        Returns:
            Dict[str, HFDataset]: 包含训练/验证/测试数据集的字典
                - "train": 训练集Dataset对象
                - "val": 验证集Dataset对象（如果存在）
                - "test": 测试集Dataset对象（如果存在）
        
        Raises:
            TrainingError: 在以下情况抛出异常：
                - 数据集中没有训练数据
                - 数据转换失败
                - 分词处理失败
        
        数据格式：
            输入格式（数据库）：
                - question: 问题文本
                - answer: 答案文本
                - split_type: 数据集划分类型（train/val/test）
            
            输出格式（分词后）：
                - input_ids: 输入token ID序列
                - attention_mask: 注意力掩码
                - 格式："Question: {question}\nAnswer: {answer}"
        
        处理流程：
            1. 从数据库加载问答对（按split_type分组）
            2. 转换为HuggingFace Dataset格式
            3. 应用分词函数（批量处理）
            4. 返回处理好的数据集字典
        """
        try:
            logger.info(f"Preparing training data for dataset {dataset_id}")
            
            # 从数据库加载问答对
            train_qa = self.db.query(QAPair).filter(
                QAPair.dataset_id == dataset_id,
                QAPair.split_type == "train"
            ).all()
            
            val_qa = self.db.query(QAPair).filter(
                QAPair.dataset_id == dataset_id,
                QAPair.split_type == "val"
            ).all()
            
            test_qa = self.db.query(QAPair).filter(
                QAPair.dataset_id == dataset_id,
                QAPair.split_type == "test"
            ).all()
            
            if not train_qa:
                raise TrainingError(f"No training data found for dataset {dataset_id}")
            
            logger.info(
                f"Loaded QA pairs - Train: {len(train_qa)}, Val: {len(val_qa)}, Test: {len(test_qa)}"
            )
            
            # 转换为HuggingFace数据集格式
            def qa_to_dict(qa_list):
                return {
                    "question": [qa.question for qa in qa_list],
                    "answer": [qa.answer for qa in qa_list]
                }
            
            train_dataset = HFDataset.from_dict(qa_to_dict(train_qa))
            val_dataset = HFDataset.from_dict(qa_to_dict(val_qa)) if val_qa else None
            test_dataset = HFDataset.from_dict(qa_to_dict(test_qa)) if test_qa else None
            
            # 定义分词函数
            def tokenize_function(examples):
                # 格式化为 "Question: {question}\nAnswer: {answer}"
                texts = [
                    f"Question: {q}\nAnswer: {a}"
                    for q, a in zip(examples["question"], examples["answer"])
                ]
                
                return tokenizer(
                    texts,
                    truncation=True,  # 截断超长文本
                    max_length=max_length,
                    padding="max_length",  # 填充到最大长度
                    return_tensors="pt"
                )
            
            # 批量分词处理
            train_dataset = train_dataset.map(
                tokenize_function,
                batched=True,
                remove_columns=["question", "answer"]  # 移除原始文本列
            )
            
            if val_dataset:
                val_dataset = val_dataset.map(
                    tokenize_function,
                    batched=True,
                    remove_columns=["question", "answer"]
                )
            
            if test_dataset:
                test_dataset = test_dataset.map(
                    tokenize_function,
                    batched=True,
                    remove_columns=["question", "answer"]
                )
            
            logger.info("Training data prepared successfully")
            
            return {
                "train": train_dataset,
                "val": val_dataset,
                "test": test_dataset
            }
        
        except Exception as e:
            logger.error(f"Failed to prepare training data: {e}")
            raise TrainingError(f"Data preparation failed: {e}")

    
    def train_model(
        self,
        job_id: int,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Train model for a training job
        
        Args:
            job_id: Training job ID
            progress_callback: Optional callback function(job_id, progress_data)
        
        Returns:
            Dictionary with training results
        
        Raises:
            TrainingError: If training fails
        """
        # Load training job
        job = self.db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if not job:
            raise TrainingError(f"Training job {job_id} not found")
        
        try:
            # Update job status
            job.status = "running"
            job.started_at = datetime.utcnow()
            job.training_logs = []
            self.db.commit()
            
            self._add_log(job, "info", "Training started")
            logger.info(f"Starting training for job {job_id}")
            
            # 清理内存
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            elif self.device == "mps":
                # MPS也支持内存清理
                torch.mps.empty_cache()
            logger.info("Memory cleaned before training")
            
            # Load base model and tokenizer
            model, tokenizer = self.load_base_model(job.model_name)
            
            # Configure LoRA
            model = self.configure_lora(
                model,
                lora_r=job.lora_r,
                lora_alpha=job.lora_alpha,
                lora_dropout=job.lora_dropout
            )
            
            # 启用梯度检查点以节省内存
            if hasattr(model, 'enable_input_require_grads'):
                model.enable_input_require_grads()
            if hasattr(model, 'gradient_checkpointing_enable'):
                model.gradient_checkpointing_enable()
                logger.info("Gradient checkpointing enabled for memory optimization")
            
            # Prepare training data
            datasets = self.prepare_training_data(job.dataset_id, tokenizer)
            
            # Calculate total steps
            train_size = len(datasets["train"])
            steps_per_epoch = train_size // job.batch_size
            job.total_steps = steps_per_epoch * job.epochs
            self.db.commit()
            
            # Create output directory
            output_dir = self.models_dir / f"job_{job_id}"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Training arguments - 针对MPS/GPU优化
            # MPS不支持fp16，使用fp32；CUDA支持fp16
            use_fp16 = self.device == "cuda"
            
            training_args = TrainingArguments(
                output_dir=str(output_dir),
                num_train_epochs=job.epochs,
                per_device_train_batch_size=job.batch_size,
                per_device_eval_batch_size=job.batch_size,
                learning_rate=job.learning_rate,
                warmup_steps=100,
                logging_steps=10,
                eval_strategy="epoch" if datasets["val"] else "no",  # Fixed: evaluation_strategy -> eval_strategy
                save_strategy="epoch",
                save_total_limit=2,
                load_best_model_at_end=True if datasets["val"] else False,
                metric_for_best_model="eval_loss" if datasets["val"] else None,
                greater_is_better=False,
                report_to="none",
                fp16=use_fp16,  # 只在CUDA上使用fp16
                remove_unused_columns=False,
                # 内存优化参数
                gradient_accumulation_steps=4,  # 梯度累积，减少内存使用
                max_grad_norm=1.0,  # 梯度裁剪
                optim="adamw_torch",  # 使用PyTorch原生优化器
                gradient_checkpointing=True,  # 启用梯度检查点，用时间换内存
                # MPS特定优化
                dataloader_num_workers=0 if self.device == "mps" else 2,  # MPS使用单线程
            )
            
            # Data collator
            data_collator = DataCollatorForLanguageModeling(
                tokenizer=tokenizer,
                mlm=False
            )
            
            # Custom callback for progress tracking
            class ProgressCallback:
                def __init__(self, trainer_service, job, db, progress_callback):
                    self.trainer_service = trainer_service
                    self.job = job
                    self.db = db
                    self.progress_callback = progress_callback
                    self.last_update = time.time()
                
                def on_epoch_end(self, args, state, control, **kwargs):
                    # Update epoch
                    self.job.current_epoch = int(state.epoch)
                    self.job.current_step = state.global_step
                    self.job.progress_percentage = (state.global_step / state.max_steps) * 100
                    
                    # Update metrics
                    if state.log_history:
                        latest_log = state.log_history[-1]
                        if "loss" in latest_log:
                            self.job.train_loss = latest_log["loss"]
                        if "eval_loss" in latest_log:
                            self.job.val_loss = latest_log["eval_loss"]
                    
                    self.db.commit()
                    
                    # Log progress
                    self.trainer_service._add_log(
                        self.job,
                        "info",
                        f"Epoch {self.job.current_epoch}/{self.job.epochs} completed - "
                        f"Loss: {self.job.train_loss:.4f}"
                    )
                    
                    # Check for anomalies
                    if self.trainer_service._detect_anomaly(self.job):
                        anomaly_msg = (
                            f"⚠️ ANOMALY DETECTED: Training loss fluctuating >50% over 3 consecutive epochs. "
                            f"Current loss: {self.job.train_loss:.4f}"
                        )
                        self.trainer_service._add_log(
                            self.job,
                            "warning",
                            anomaly_msg
                        )
                        logger.warning(f"Job {self.job.id}: {anomaly_msg}")
                    
                    # Call progress callback
                    if self.progress_callback:
                        self.progress_callback(self.job.id, {
                            "epoch": self.job.current_epoch,
                            "progress": self.job.progress_percentage,
                            "train_loss": self.job.train_loss,
                            "val_loss": self.job.val_loss
                        })
                
                def on_log(self, args, state, control, logs=None, **kwargs):
                    # Update every 30 seconds
                    current_time = time.time()
                    if current_time - self.last_update >= 30:
                        self.job.current_step = state.global_step
                        self.job.progress_percentage = (state.global_step / state.max_steps) * 100
                        
                        if logs and "loss" in logs:
                            self.job.train_loss = logs["loss"]
                        
                        self.db.commit()
                        self.last_update = current_time
            
            # Create trainer
            from transformers import TrainerCallback
            
            class CustomCallback(TrainerCallback):
                def __init__(self, progress_cb):
                    self.progress_cb = progress_cb
                
                def on_epoch_end(self, args, state, control, **kwargs):
                    self.progress_cb.on_epoch_end(args, state, control, **kwargs)
                
                def on_log(self, args, state, control, logs=None, **kwargs):
                    self.progress_cb.on_log(args, state, control, logs=logs, **kwargs)
            
            progress_cb = ProgressCallback(self, job, self.db, progress_callback)
            
            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=datasets["train"],
                eval_dataset=datasets["val"],
                data_collator=data_collator,
                callbacks=[CustomCallback(progress_cb)]
            )
            
            # Train model
            self._add_log(job, "info", "Starting training loop")
            train_result = trainer.train()
            
            # Evaluate on validation set
            if datasets["val"]:
                self._add_log(job, "info", "Evaluating on validation set")
                eval_result = trainer.evaluate()
                job.val_loss = eval_result.get("eval_loss")
                job.val_accuracy = eval_result.get("eval_accuracy")
            
            # Save model
            self._add_log(job, "info", "Saving model")
            model_save_path = output_dir / "final_model"
            trainer.save_model(str(model_save_path))
            tokenizer.save_pretrained(str(model_save_path))
            
            job.model_path = str(model_save_path)
            
            # Update job status
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.current_epoch = job.epochs
            job.progress_percentage = 100.0
            self.db.commit()
            
            self._add_log(job, "info", "Training completed successfully")
            logger.info(f"Training completed for job {job_id}")
            
            # 清理内存
            del model
            del trainer
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            elif self.device == "mps":
                torch.mps.empty_cache()
            logger.info("Memory cleaned after training")
            
            return {
                "job_id": job_id,
                "status": "completed",
                "train_loss": job.train_loss,
                "val_loss": job.val_loss,
                "val_accuracy": job.val_accuracy,
                "model_path": job.model_path,
                "duration": (job.completed_at - job.started_at).total_seconds()
            }
        
        except Exception as e:
            # Update job status to failed
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            self.db.commit()
            
            # 清理内存
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            elif self.device == "mps":
                torch.mps.empty_cache()
            
            # Log detailed error with traceback
            import traceback
            error_traceback = traceback.format_exc()
            self._add_log(job, "error", f"Training failed: {e}\n{error_traceback}")
            logger.error(f"Training failed for job {job_id}: {e}\n{error_traceback}")
            
            raise TrainingError(f"Training failed: {e}")
    
    def stop_training(self, job_id: int) -> Dict[str, Any]:
        """
        停止正在运行的训练任务
        
        本方法用于手动停止正在进行的训练任务。
        
        Args:
            job_id (int): 训练任务ID
        
        Returns:
            Dict[str, Any]: 停止结果字典，包含：
                - job_id: 任务ID
                - status: 任务状态（"stopped"）
                - message: 操作消息
        
        Raises:
            TrainingError: 在以下情况抛出异常：
                - 训练任务不存在
        
        注意事项：
            - 可以停止状态为"running"或"pending"的任务
            - 停止后任务状态变为"stopped"
            - 已完成的训练步骤不会回滚
            - 对于僵尸任务（显示running但实际已停止），也会正确更新状态
        """
        job = self.db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if not job:
            raise TrainingError(f"Training job {job_id} not found")
        
        # 允许停止running、pending状态的任务
        # 对于僵尸任务（显示running但实际已停止），也允许停止
        if job.status not in ["running", "pending"]:
            raise TrainingError(f"Training job {job_id} cannot be stopped (status: {job.status})")
        
        # 更新任务状态
        old_status = job.status
        job.status = "stopped"
        job.completed_at = datetime.utcnow()
        
        # 如果任务还没有开始时间，设置开始时间
        if not job.started_at:
            job.started_at = datetime.utcnow()
        
        self.db.commit()
        
        self._add_log(job, "warning", f"Training stopped by user (was {old_status})")
        logger.info(f"Training stopped for job {job_id} (was {old_status})")
        
        return {
            "job_id": job_id,
            "status": "stopped",
            "message": f"Training stopped successfully (was {old_status})"
        }
    
    def _add_log(self, job: TrainingJob, level: str, message: str):
        """
        向训练任务添加日志条目
        
        本方法用于记录训练过程中的重要事件和信息。
        
        Args:
            job (TrainingJob): 训练任务对象
            level (str): 日志级别，可选值：
                - "info": 一般信息（如训练开始、epoch完成）
                - "warning": 警告信息（如异常检测、训练停止）
                - "error": 错误信息（如训练失败）
            message (str): 日志消息内容
        
        日志格式：
            每条日志包含以下字段：
            - timestamp: 时间戳（ISO格式）
            - level: 日志级别
            - message: 日志消息
        
        存储位置：
            - 日志存储在TrainingJob.training_logs字段（JSON数组）
            - 同时输出到系统日志（loguru）
        """
        if job.training_logs is None:
            job.training_logs = []
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message
        }
        
        job.training_logs.append(log_entry)
        self.db.commit()
        
        # 同时输出到系统日志
        if level == "error":
            logger.error(f"Job {job.id}: {message}")
        elif level == "warning":
            logger.warning(f"Job {job.id}: {message}")
        else:
            logger.info(f"Job {job.id}: {message}")
    
    def _detect_anomaly(self, job: TrainingJob) -> bool:
        """
        检测训练loss的异常波动
        
        本方法监控训练loss的变化趋势，检测是否存在异常波动。
        如果连续3个epoch的loss波动超过50%，则认为存在异常。
        
        Args:
            job (TrainingJob): 训练任务对象
        
        Returns:
            bool: 如果检测到异常返回True，否则返回False
        
        检测逻辑：
            1. 从训练日志中提取最近3个epoch的loss值
            2. 计算相邻epoch之间的相对变化率
            3. 如果连续两次变化率都超过50%，判定为异常
        
        异常示例：
            - Epoch 1: loss=1.0
            - Epoch 2: loss=0.4 (变化60%)
            - Epoch 3: loss=0.8 (变化100%)
            → 检测到异常
        
        正常示例：
            - Epoch 1: loss=1.0
            - Epoch 2: loss=0.8 (变化20%)
            - Epoch 3: loss=0.6 (变化25%)
            → 未检测到异常
        
        注意事项：
            - 需要至少3个epoch的数据才能检测
            - 只检查最近的3个epoch
            - 异常检测不会中断训练，只会发出警告
        """
        if not job.training_logs or len(job.training_logs) < 3:
            return False
        
        # 从最近的日志中提取loss值
        loss_values = []
        for log_entry in reversed(job.training_logs):
            if "Loss:" in log_entry.get("message", ""):
                try:
                    # 解析日志消息中的loss值
                    # 格式示例："Epoch 1/3 completed - Loss: 0.1234"
                    message = log_entry["message"]
                    loss_str = message.split("Loss:")[1].strip().split()[0]
                    loss = float(loss_str)
                    loss_values.append(loss)
                    
                    if len(loss_values) >= 3:
                        break
                except (IndexError, ValueError):
                    continue
        
        # 需要至少3个loss值
        if len(loss_values) < 3:
            return False
        
        # 检查连续3个epoch的波动是否超过50%
        for i in range(len(loss_values) - 2):
            loss1, loss2, loss3 = loss_values[i], loss_values[i+1], loss_values[i+2]
            
            # 计算相对变化率
            if loss1 > 0:
                change1 = abs(loss2 - loss1) / loss1
                if loss2 > 0:
                    change2 = abs(loss3 - loss2) / loss2
                    
                    # 如果两次变化都超过50%，判定为异常
                    if change1 > 0.5 and change2 > 0.5:
                        return True
        
        return False
