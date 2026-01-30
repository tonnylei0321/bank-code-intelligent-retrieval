"""
Model Evaluator Service - 模型评估服务

本服务负责对训练好的模型进行全面评估，包括准确性、性能和鲁棒性测试。

主要功能：
    - 准确性评估：计算准确率、精确率、召回率、F1分数
    - 性能评估：测量响应时间统计（平均值、P95、P99）
    - 鲁棒性测试：测试错别字容错、简称识别、空格容错
    - 错误分析：收集和分析错误案例
    - 报告生成：生成详细的评估报告（Markdown格式）
    - 对比评估：对比小模型方案与基准系统（Elasticsearch）
    - 成本分析：计算训练和推理成本

评估指标说明：
    1. 准确性指标：
       - Accuracy（准确率）：正确预测的比例
       - Precision（精确率）：预测为正的样本中实际为正的比例
       - Recall（召回率）：实际为正的样本中被正确预测的比例
       - F1 Score（F1分数）：精确率和召回率的调和平均数
    
    2. 性能指标：
       - 平均响应时间：所有查询的平均响应时间
       - P95响应时间：95%的查询响应时间不超过此值
       - P99响应时间：99%的查询响应时间不超过此值
    
    3. 鲁棒性指标：
       - 错别字容错：对输入中的错别字的容忍度
       - 简称识别：识别银行简称的能力
       - 空格容错：对额外空格的容忍度

使用示例：
    >>> from app.services.model_evaluator import ModelEvaluator
    >>> evaluator = ModelEvaluator(db_session)
    >>> 
    >>> # 评估训练好的模型
    >>> results = evaluator.evaluate_model(training_job_id=1)
    >>> 
    >>> # 评估基准系统
    >>> baseline_results = evaluator.evaluate_baseline(
    ...     training_job_id=1,
    ...     baseline_system=baseline_system
    ... )
    >>> 
    >>> # 生成评估报告
    >>> report_path = evaluator.generate_report(evaluation_id=1)
    >>> 
    >>> # 对比两种方案
    >>> comparison = evaluator.compare_evaluations(
    ...     model_evaluation_id=1,
    ...     baseline_evaluation_id=2
    ... )
"""
import time
import random
import statistics
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from sqlalchemy.orm import Session
from loguru import logger

from app.models.evaluation import Evaluation
from app.models.training_job import TrainingJob
from app.models.qa_pair import QAPair
from app.models.bank_code import BankCode


class EvaluationError(Exception):
    """
    评估异常基类
    
    用于标识模型评估过程中的所有错误，包括：
    - 模型加载失败
    - 评估数据不足
    - 指标计算错误
    - 报告生成失败
    """
    pass


class ModelEvaluator:
    """
    模型评估器服务 - 用于全面评估模型性能
    
    本类提供完整的模型评估功能，包括准确性、性能和鲁棒性测试。
    支持对比小模型方案与基准系统（Elasticsearch），生成详细的评估报告。
    
    核心功能：
        1. 模型评估：
           - 加载训练好的模型
           - 在测试集上生成预测
           - 计算各项评估指标
           - 保存评估结果到数据库
        
        2. 指标计算：
           - 准确率、精确率、召回率、F1分数
           - 按问题类型分别统计准确率
           - 响应时间统计（平均、P95、P99）
           - 混淆矩阵
        
        3. 鲁棒性测试：
           - 错别字容错测试
           - 简称识别测试
           - 空格容错测试
        
        4. 错误分析：
           - 收集错误案例
           - 分析错误类型
           - 提供错误详情
        
        5. 报告生成：
           - 生成Markdown格式的评估报告
           - 包含所有指标和错误案例
           - 提供性能评估建议
        
        6. 对比评估：
           - 对比小模型与基准系统
           - 生成对比报告
           - 提供方案选择建议
        
        7. 成本分析：
           - 计算训练成本
           - 计算推理成本
           - 对比两种方案的成本
    
    属性：
        db (Session): 数据库会话对象
        reports_dir (Path): 报告保存目录
        device (str): 评估设备（"cuda"或"cpu"）
    
    评估流程：
        1. 加载训练好的模型
        2. 加载测试数据
        3. 生成预测结果
        4. 计算评估指标
        5. 测试鲁棒性
        6. 收集错误案例
        7. 保存评估结果
        8. 生成评估报告
    """
    
    def __init__(
        self,
        db: Session,
        reports_dir: str = "reports"
    ):
        """
        初始化模型评估器
        
        Args:
            db (Session): SQLAlchemy数据库会话对象，用于访问评估数据
            reports_dir (str): 报告保存目录路径，默认为"reports"
                生成的评估报告将保存在此目录中
        
        说明：
            - 自动检测GPU可用性，优先使用CUDA加速
            - 如果没有GPU，自动降级到CPU评估
            - 自动创建报告保存目录（如果不存在）
            - 初始化时会记录设备信息到日志
        """
        self.db = db
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查设备可用性（优先使用GPU）
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"ModelEvaluator initialized - Device: {self.device}")
    
    def load_model(
        self,
        model_path: str
    ) -> Tuple[Any, Any]:
        """
        Load trained model and tokenizer
        
        Args:
            model_path: Path to saved model
        
        Returns:
            Tuple of (model, tokenizer)
        
        Raises:
            EvaluationError: If model loading fails
        """
        try:
            logger.info(f"Loading model from: {model_path}")
            
            # Load tokenizer
            tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                trust_remote_code=True
            )
            
            # Load model
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                trust_remote_code=True,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None
            )
            
            model.eval()  # Set to evaluation mode
            
            logger.info("Model loaded successfully")
            return model, tokenizer
        
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise EvaluationError(f"Model loading failed: {e}")
    
    def generate_answer(
        self,
        model,
        tokenizer,
        question: str,
        max_length: int = 256
    ) -> Tuple[str, float]:
        """
        Generate answer for a question
        
        Args:
            model: Trained model
            tokenizer: Tokenizer
            question: Question text
            max_length: Maximum generation length
        
        Returns:
            Tuple of (answer, response_time_ms)
        """
        try:
            # Format input
            prompt = f"Question: {question}\nAnswer:"
            
            # Tokenize
            inputs = tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=512
            )
            
            if self.device == "cuda":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate
            start_time = time.time()
            
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=max_length,
                    do_sample=False,
                    pad_token_id=tokenizer.pad_token_id,
                    eos_token_id=tokenizer.eos_token_id
                )
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to ms
            
            # Decode
            generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract answer (remove prompt)
            if "Answer:" in generated_text:
                answer = generated_text.split("Answer:")[-1].strip()
            else:
                answer = generated_text.strip()
            
            return answer, response_time
        
        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            return "", 0.0
    
    def extract_bank_code(self, text: str) -> Optional[str]:
        """
        从文本中提取银行联行号
        
        本方法使用正则表达式从模型生成的答案中提取12位银行联行号。
        
        Args:
            text (str): 包含银行联行号的文本
        
        Returns:
            Optional[str]: 提取到的12位联行号，如果未找到则返回None
        
        提取策略：
            1. 优先匹配：前后有中文字符或空格的12位数字
               - 这样可以避免匹配到更长数字中的一部分
               - 例如："工商银行的联行号是102100099996"
            
            2. 备用匹配：任意12位连续数字
               - 如果第一种模式未匹配到，使用此模式
               - 例如："102100099996"
        
        正则表达式说明：
            - \d{12}: 匹配12位数字
            - [\s\u4e00-\u9fff]: 匹配空格或中文字符
            - (?:^|...): 非捕获组，匹配开头或指定字符
            - (?:...|$): 非捕获组，匹配指定字符或结尾
        """
        import re
        
        # 优先匹配：前后有中文字符或空格的12位数字
        # 这样可以避免匹配到更长数字中的一部分
        matches = re.findall(r'(?:^|[\s\u4e00-\u9fff])(\d{12})(?:[\s\u4e00-\u9fff]|$)', text)
        if matches:
            return matches[0]
        
        # 备用方案：直接查找12位连续数字
        matches = re.findall(r'\d{12}', text)
        if matches:
            return matches[0]
        
        return None
    
    def calculate_metrics(
        self,
        predictions: List[str],
        references: List[str]
    ) -> Dict[str, float]:
        """
        Calculate evaluation metrics
        
        Args:
            predictions: List of predicted answers
            references: List of reference answers
        
        Returns:
            Dictionary with metrics
        """
        if len(predictions) != len(references):
            raise EvaluationError("Predictions and references must have same length")
        
        # Extract bank codes from predictions and references
        pred_codes = [self.extract_bank_code(p) for p in predictions]
        ref_codes = [self.extract_bank_code(r) for r in references]
        
        # Calculate metrics
        true_positives = sum(
            1 for p, r in zip(pred_codes, ref_codes)
            if p is not None and r is not None and p == r
        )
        
        false_positives = sum(
            1 for p, r in zip(pred_codes, ref_codes)
            if p is not None and (r is None or p != r)
        )
        
        false_negatives = sum(
            1 for p, r in zip(pred_codes, ref_codes)
            if p is None and r is not None
        )
        
        true_negatives = sum(
            1 for p, r in zip(pred_codes, ref_codes)
            if p is None and r is None
        )
        
        total = len(predictions)
        
        # Calculate metrics
        accuracy = (true_positives + true_negatives) / total if total > 0 else 0.0
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "true_negatives": true_negatives,
            "total": total
        }
    
    def calculate_response_time_stats(
        self,
        response_times: List[float]
    ) -> Dict[str, float]:
        """
        Calculate response time statistics
        
        Args:
            response_times: List of response times in milliseconds
        
        Returns:
            Dictionary with statistics
        """
        if not response_times:
            return {
                "avg_response_time": 0.0,
                "p95_response_time": 0.0,
                "p99_response_time": 0.0,
                "min_response_time": 0.0,
                "max_response_time": 0.0
            }
        
        sorted_times = sorted(response_times)
        
        return {
            "avg_response_time": statistics.mean(response_times),
            "p95_response_time": sorted_times[int(len(sorted_times) * 0.95)] if len(sorted_times) > 0 else 0.0,
            "p99_response_time": sorted_times[int(len(sorted_times) * 0.99)] if len(sorted_times) > 0 else 0.0,
            "min_response_time": min(response_times),
            "max_response_time": max(response_times)
        }
    
    def generate_typo_variant(self, text: str) -> str:
        """
        Generate text with typos
        
        Args:
            text: Original text
        
        Returns:
            Text with typos
        """
        if len(text) < 2:
            return text
        
        # Randomly swap adjacent characters
        chars = list(text)
        pos = random.randint(0, len(chars) - 2)
        chars[pos], chars[pos + 1] = chars[pos + 1], chars[pos]
        
        return ''.join(chars)
    
    def generate_abbreviation_variant(self, text: str) -> str:
        """
        Generate abbreviated version of text
        
        Args:
            text: Original text
        
        Returns:
            Abbreviated text
        """
        # Common abbreviations for Chinese bank names
        abbreviations = {
            "中国工商银行": "工行",
            "中国农业银行": "农行",
            "中国银行": "中行",
            "中国建设银行": "建行",
            "交通银行": "交行"
        }
        
        result = text
        for full, abbr in abbreviations.items():
            if full in result:
                result = result.replace(full, abbr)
                break
        
        return result
    
    def generate_space_variant(self, text: str) -> str:
        """
        Generate text with extra spaces
        
        Args:
            text: Original text
        
        Returns:
            Text with extra spaces
        """
        # Strip whitespace first to avoid issues with existing whitespace
        text = text.strip()
        
        # Add random spaces
        words = text.split()
        if len(words) > 1:
            # Add extra space between random words
            pos = random.randint(0, len(words) - 1)
            words.insert(pos, " ")
        
        return " ".join(words)
    
    def test_robustness(
        self,
        model,
        tokenizer,
        test_cases: List[Dict[str, str]]
    ) -> Dict[str, float]:
        """
        Test model robustness with variants
        
        Args:
            model: Trained model
            tokenizer: Tokenizer
            test_cases: List of test cases with 'question' and 'answer'
        
        Returns:
            Dictionary with robustness metrics
        """
        logger.info("Testing model robustness")
        
        typo_correct = 0
        abbr_correct = 0
        space_correct = 0
        
        # Sample test cases for robustness testing
        sample_size = min(100, len(test_cases))
        sampled_cases = random.sample(test_cases, sample_size)
        
        for case in sampled_cases:
            question = case["question"]
            expected_code = self.extract_bank_code(case["answer"])
            
            if not expected_code:
                continue
            
            # Test typo variant
            typo_question = self.generate_typo_variant(question)
            typo_answer, _ = self.generate_answer(model, tokenizer, typo_question)
            typo_code = self.extract_bank_code(typo_answer)
            if typo_code == expected_code:
                typo_correct += 1
            
            # Test abbreviation variant
            abbr_question = self.generate_abbreviation_variant(question)
            abbr_answer, _ = self.generate_answer(model, tokenizer, abbr_question)
            abbr_code = self.extract_bank_code(abbr_answer)
            if abbr_code == expected_code:
                abbr_correct += 1
            
            # Test space variant
            space_question = self.generate_space_variant(question)
            space_answer, _ = self.generate_answer(model, tokenizer, space_question)
            space_code = self.extract_bank_code(space_answer)
            if space_code == expected_code:
                space_correct += 1
        
        return {
            "typo_tolerance": typo_correct / sample_size if sample_size > 0 else 0.0,
            "abbreviation_accuracy": abbr_correct / sample_size if sample_size > 0 else 0.0,
            "space_tolerance": space_correct / sample_size if sample_size > 0 else 0.0
        }
    
    def collect_error_cases(
        self,
        questions: List[str],
        predictions: List[str],
        references: List[str],
        max_cases: int = 50
    ) -> List[Dict[str, str]]:
        """
        Collect error cases for analysis
        
        Args:
            questions: List of questions
            predictions: List of predicted answers
            references: List of reference answers
            max_cases: Maximum number of error cases to collect
        
        Returns:
            List of error cases
        """
        error_cases = []
        
        for q, p, r in zip(questions, predictions, references):
            pred_code = self.extract_bank_code(p)
            ref_code = self.extract_bank_code(r)
            
            if pred_code != ref_code:
                error_cases.append({
                    "question": q,
                    "expected_answer": r,
                    "actual_answer": p,
                    "expected_code": ref_code or "None",
                    "predicted_code": pred_code or "None",
                    "error_type": "wrong_code" if pred_code and ref_code else "missing_code"
                })
                
                if len(error_cases) >= max_cases:
                    break
        
        return error_cases
    
    def evaluate_model(
        self,
        training_job_id: int,
        evaluation_type: str = "model"
    ) -> Dict[str, Any]:
        """
        Evaluate trained model
        
        Args:
            training_job_id: Training job ID
            evaluation_type: Type of evaluation ('model' or 'baseline')
        
        Returns:
            Dictionary with evaluation results
        
        Raises:
            EvaluationError: If evaluation fails
        """
        # Load training job
        job = self.db.query(TrainingJob).filter(TrainingJob.id == training_job_id).first()
        if not job:
            raise EvaluationError(f"Training job {training_job_id} not found")
        
        if not job.model_path:
            raise EvaluationError(f"Training job {training_job_id} has no saved model")
        
        try:
            logger.info(f"Starting evaluation for training job {training_job_id}")
            
            # Load model
            model, tokenizer = self.load_model(job.model_path)
            
            # Load test data
            test_qa = self.db.query(QAPair).filter(
                QAPair.dataset_id == job.dataset_id,
                QAPair.split_type == "test"
            ).all()
            
            if not test_qa:
                raise EvaluationError(f"No test data found for dataset {job.dataset_id}")
            
            logger.info(f"Loaded {len(test_qa)} test cases")
            
            # Generate predictions
            questions = [qa.question for qa in test_qa]
            references = [qa.answer for qa in test_qa]
            predictions = []
            response_times = []
            
            logger.info("Generating predictions...")
            for i, question in enumerate(questions):
                if i % 10 == 0:
                    logger.info(f"Progress: {i}/{len(questions)}")
                
                answer, response_time = self.generate_answer(model, tokenizer, question)
                predictions.append(answer)
                response_times.append(response_time)
            
            # Calculate metrics
            logger.info("Calculating metrics...")
            metrics = self.calculate_metrics(predictions, references)
            
            # Calculate response time statistics
            time_stats = self.calculate_response_time_stats(response_times)
            metrics.update(time_stats)
            
            # Calculate per-question-type accuracy
            question_types = ["exact", "fuzzy", "reverse", "natural"]
            for qtype in question_types:
                type_qa = [qa for qa in test_qa if qa.question_type == qtype]
                if type_qa:
                    type_questions = [qa.question for qa in type_qa]
                    type_references = [qa.answer for qa in type_qa]
                    type_predictions = []
                    
                    for q in type_questions:
                        idx = questions.index(q)
                        type_predictions.append(predictions[idx])
                    
                    type_metrics = self.calculate_metrics(type_predictions, type_references)
                    metrics[f"{qtype}_match_accuracy"] = type_metrics["accuracy"]
            
            # Test robustness
            logger.info("Testing robustness...")
            test_cases = [{"question": qa.question, "answer": qa.answer} for qa in test_qa]
            robustness_metrics = self.test_robustness(model, tokenizer, test_cases)
            metrics.update(robustness_metrics)
            
            # Collect error cases
            logger.info("Collecting error cases...")
            error_cases = self.collect_error_cases(questions, predictions, references)
            
            # Save evaluation to database
            evaluation = Evaluation(
                training_job_id=training_job_id,
                evaluation_type=evaluation_type,
                metrics=metrics,
                error_cases=error_cases,
                evaluated_at=datetime.utcnow()
            )
            
            self.db.add(evaluation)
            self.db.commit()
            self.db.refresh(evaluation)
            
            logger.info(f"Evaluation completed - ID: {evaluation.id}")
            logger.info(f"Accuracy: {metrics['accuracy']:.4f}, F1: {metrics['f1_score']:.4f}")
            
            return {
                "evaluation_id": evaluation.id,
                "metrics": metrics,
                "error_cases": error_cases,
                "total_test_cases": len(test_qa)
            }
        
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            raise EvaluationError(f"Evaluation failed: {e}")
    
    def generate_report(
        self,
        evaluation_id: int
    ) -> str:
        """
        Generate evaluation report in Markdown format
        
        Args:
            evaluation_id: Evaluation ID
        
        Returns:
            Path to generated report file
        
        Raises:
            EvaluationError: If report generation fails
        """
        # Load evaluation
        evaluation = self.db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
        if not evaluation:
            raise EvaluationError(f"Evaluation {evaluation_id} not found")
        
        try:
            logger.info(f"Generating report for evaluation {evaluation_id}")
            
            # Load training job
            job = evaluation.training_job
            
            # Create report content
            report_lines = []
            report_lines.append(f"# 模型评估报告")
            report_lines.append(f"")
            report_lines.append(f"**评估ID**: {evaluation.id}")
            report_lines.append(f"**训练任务ID**: {evaluation.training_job_id}")
            report_lines.append(f"**评估类型**: {evaluation.evaluation_type}")
            report_lines.append(f"**评估时间**: {evaluation.evaluated_at.strftime('%Y-%m-%d %H:%M:%S')}")
            report_lines.append(f"")
            
            # Model information
            report_lines.append(f"## 模型信息")
            report_lines.append(f"")
            report_lines.append(f"- **基座模型**: {job.model_name}")
            report_lines.append(f"- **训练轮数**: {job.epochs}")
            report_lines.append(f"- **批次大小**: {job.batch_size}")
            report_lines.append(f"- **学习率**: {job.learning_rate}")
            report_lines.append(f"- **LoRA配置**: r={job.lora_r}, alpha={job.lora_alpha}, dropout={job.lora_dropout}")
            report_lines.append(f"")
            
            # Performance metrics
            metrics = evaluation.metrics
            report_lines.append(f"## 性能指标")
            report_lines.append(f"")
            report_lines.append(f"### 准确性指标")
            report_lines.append(f"")
            report_lines.append(f"| 指标 | 数值 |")
            report_lines.append(f"|------|------|")
            report_lines.append(f"| 准确率 (Accuracy) | {metrics.get('accuracy', 0):.4f} ({metrics.get('accuracy', 0)*100:.2f}%) |")
            report_lines.append(f"| 精确率 (Precision) | {metrics.get('precision', 0):.4f} ({metrics.get('precision', 0)*100:.2f}%) |")
            report_lines.append(f"| 召回率 (Recall) | {metrics.get('recall', 0):.4f} ({metrics.get('recall', 0)*100:.2f}%) |")
            report_lines.append(f"| F1分数 (F1 Score) | {metrics.get('f1_score', 0):.4f} ({metrics.get('f1_score', 0)*100:.2f}%) |")
            report_lines.append(f"")
            
            # Per-question-type accuracy
            report_lines.append(f"### 分场景准确率")
            report_lines.append(f"")
            report_lines.append(f"| 问题类型 | 准确率 |")
            report_lines.append(f"|----------|--------|")
            
            question_types = {
                "exact_match_accuracy": "精确匹配",
                "fuzzy_match_accuracy": "模糊匹配",
                "reverse_match_accuracy": "反向查询",
                "natural_match_accuracy": "自然语言"
            }
            
            for key, label in question_types.items():
                if key in metrics:
                    report_lines.append(f"| {label} | {metrics[key]:.4f} ({metrics[key]*100:.2f}%) |")
            report_lines.append(f"")
            
            # Response time statistics
            report_lines.append(f"### 响应时间统计")
            report_lines.append(f"")
            report_lines.append(f"| 指标 | 时间 (ms) |")
            report_lines.append(f"|------|-----------|")
            report_lines.append(f"| 平均响应时间 | {metrics.get('avg_response_time', 0):.2f} |")
            report_lines.append(f"| P95响应时间 | {metrics.get('p95_response_time', 0):.2f} |")
            report_lines.append(f"| P99响应时间 | {metrics.get('p99_response_time', 0):.2f} |")
            report_lines.append(f"| 最小响应时间 | {metrics.get('min_response_time', 0):.2f} |")
            report_lines.append(f"| 最大响应时间 | {metrics.get('max_response_time', 0):.2f} |")
            report_lines.append(f"")
            
            # Robustness metrics
            report_lines.append(f"### 鲁棒性指标")
            report_lines.append(f"")
            report_lines.append(f"| 测试类型 | 准确率 |")
            report_lines.append(f"|----------|--------|")
            report_lines.append(f"| 错别字容错 | {metrics.get('typo_tolerance', 0):.4f} ({metrics.get('typo_tolerance', 0)*100:.2f}%) |")
            report_lines.append(f"| 简称识别 | {metrics.get('abbreviation_accuracy', 0):.4f} ({metrics.get('abbreviation_accuracy', 0)*100:.2f}%) |")
            report_lines.append(f"| 空格容错 | {metrics.get('space_tolerance', 0):.4f} ({metrics.get('space_tolerance', 0)*100:.2f}%) |")
            report_lines.append(f"")
            
            # Confusion matrix
            report_lines.append(f"### 混淆矩阵")
            report_lines.append(f"")
            report_lines.append(f"| | 预测为正 | 预测为负 |")
            report_lines.append(f"|---|---------|---------|")
            report_lines.append(f"| **实际为正** | {metrics.get('true_positives', 0)} | {metrics.get('false_negatives', 0)} |")
            report_lines.append(f"| **实际为负** | {metrics.get('false_positives', 0)} | {metrics.get('true_negatives', 0)} |")
            report_lines.append(f"")
            
            # Error cases
            if evaluation.error_cases:
                report_lines.append(f"## 错误案例分析")
                report_lines.append(f"")
                report_lines.append(f"共收集 {len(evaluation.error_cases)} 个错误案例（最多显示前20个）：")
                report_lines.append(f"")
                
                for i, error in enumerate(evaluation.error_cases[:20], 1):
                    report_lines.append(f"### 错误案例 {i}")
                    report_lines.append(f"")
                    report_lines.append(f"- **问题**: {error['question']}")
                    report_lines.append(f"- **期望答案**: {error['expected_answer']}")
                    report_lines.append(f"- **实际答案**: {error['actual_answer']}")
                    report_lines.append(f"- **期望联行号**: {error['expected_code']}")
                    report_lines.append(f"- **预测联行号**: {error['predicted_code']}")
                    report_lines.append(f"- **错误类型**: {error['error_type']}")
                    report_lines.append(f"")
            
            # Summary
            report_lines.append(f"## 评估总结")
            report_lines.append(f"")
            report_lines.append(f"- 测试用例总数: {metrics.get('total', 0)}")
            report_lines.append(f"- 正确预测数: {metrics.get('true_positives', 0) + metrics.get('true_negatives', 0)}")
            report_lines.append(f"- 错误预测数: {metrics.get('false_positives', 0) + metrics.get('false_negatives', 0)}")
            report_lines.append(f"- 整体准确率: {metrics.get('accuracy', 0)*100:.2f}%")
            report_lines.append(f"")
            
            # Performance assessment
            accuracy = metrics.get('accuracy', 0)
            if accuracy >= 0.95:
                assessment = "优秀 - 模型达到了预期的准确率目标（≥95%）"
            elif accuracy >= 0.90:
                assessment = "良好 - 模型准确率接近目标，建议进一步优化"
            elif accuracy >= 0.80:
                assessment = "一般 - 模型准确率有待提高，建议调整训练参数或增加训练数据"
            else:
                assessment = "较差 - 模型准确率未达标，需要重新审视训练策略"
            
            report_lines.append(f"**性能评估**: {assessment}")
            report_lines.append(f"")
            
            # Save report
            report_filename = f"evaluation_{evaluation_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            report_path = self.reports_dir / report_filename
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_lines))
            
            # Update evaluation with report path
            evaluation.report_path = str(report_path)
            self.db.commit()
            
            logger.info(f"Report generated: {report_path}")
            
            return str(report_path)
        
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            raise EvaluationError(f"Report generation failed: {e}")

    def evaluate_baseline(
        self,
        training_job_id: int,
        baseline_system
    ) -> Dict[str, Any]:
        """
        Evaluate baseline system (Elasticsearch)
        
        Args:
            training_job_id: Training job ID (for test data)
            baseline_system: BaselineSystem instance
        
        Returns:
            Dictionary with evaluation results
        
        Raises:
            EvaluationError: If evaluation fails
        """
        # Load training job
        job = self.db.query(TrainingJob).filter(TrainingJob.id == training_job_id).first()
        if not job:
            raise EvaluationError(f"Training job {training_job_id} not found")
        
        if not baseline_system or not baseline_system.is_available():
            raise EvaluationError("Baseline system (Elasticsearch) is not available")
        
        try:
            logger.info(f"Starting baseline evaluation for training job {training_job_id}")
            
            # Load test data
            test_qa = self.db.query(QAPair).filter(
                QAPair.dataset_id == job.dataset_id,
                QAPair.split_type == "test"
            ).all()
            
            if not test_qa:
                raise EvaluationError(f"No test data found for dataset {job.dataset_id}")
            
            logger.info(f"Loaded {len(test_qa)} test cases")
            
            # Generate predictions using baseline
            questions = [qa.question for qa in test_qa]
            references = [qa.answer for qa in test_qa]
            predictions = []
            response_times = []
            
            logger.info("Generating predictions with baseline system...")
            for i, question in enumerate(questions):
                if i % 10 == 0:
                    logger.info(f"Progress: {i}/{len(questions)}")
                
                result = baseline_system.query(question, dataset_id=job.dataset_id)
                predictions.append(result["answer"])
                response_times.append(result["response_time"])
            
            # Calculate metrics
            logger.info("Calculating metrics...")
            metrics = self.calculate_metrics(predictions, references)
            
            # Calculate response time statistics
            time_stats = self.calculate_response_time_stats(response_times)
            metrics.update(time_stats)
            
            # Calculate per-question-type accuracy
            question_types = ["exact", "fuzzy", "reverse", "natural"]
            for qtype in question_types:
                type_qa = [qa for qa in test_qa if qa.question_type == qtype]
                if type_qa:
                    type_questions = [qa.question for qa in type_qa]
                    type_references = [qa.answer for qa in type_qa]
                    type_predictions = []
                    
                    for q in type_questions:
                        idx = questions.index(q)
                        type_predictions.append(predictions[idx])
                    
                    type_metrics = self.calculate_metrics(type_predictions, type_references)
                    metrics[f"{qtype}_match_accuracy"] = type_metrics["accuracy"]
            
            # Collect error cases
            logger.info("Collecting error cases...")
            error_cases = self.collect_error_cases(questions, predictions, references)
            
            # Save evaluation to database
            evaluation = Evaluation(
                training_job_id=training_job_id,
                evaluation_type="baseline",
                metrics=metrics,
                error_cases=error_cases,
                evaluated_at=datetime.utcnow()
            )
            
            self.db.add(evaluation)
            self.db.commit()
            self.db.refresh(evaluation)
            
            logger.info(f"Baseline evaluation completed - ID: {evaluation.id}")
            logger.info(f"Accuracy: {metrics['accuracy']:.4f}, F1: {metrics['f1_score']:.4f}")
            
            return {
                "evaluation_id": evaluation.id,
                "metrics": metrics,
                "error_cases": error_cases,
                "total_test_cases": len(test_qa)
            }
        
        except Exception as e:
            logger.error(f"Baseline evaluation failed: {e}")
            raise EvaluationError(f"Baseline evaluation failed: {e}")
    
    def compare_evaluations(
        self,
        model_evaluation_id: int,
        baseline_evaluation_id: int
    ) -> Dict[str, Any]:
        """
        Compare model and baseline evaluations
        
        Args:
            model_evaluation_id: Model evaluation ID
            baseline_evaluation_id: Baseline evaluation ID
        
        Returns:
            Dictionary with comparison results
        
        Raises:
            EvaluationError: If comparison fails
        """
        # Load evaluations
        model_eval = self.db.query(Evaluation).filter(Evaluation.id == model_evaluation_id).first()
        baseline_eval = self.db.query(Evaluation).filter(Evaluation.id == baseline_evaluation_id).first()
        
        if not model_eval:
            raise EvaluationError(f"Model evaluation {model_evaluation_id} not found")
        if not baseline_eval:
            raise EvaluationError(f"Baseline evaluation {baseline_evaluation_id} not found")
        
        # Verify they use the same test set
        if model_eval.training_job_id != baseline_eval.training_job_id:
            logger.warning("Evaluations are from different training jobs - comparison may not be fair")
        
        model_metrics = model_eval.metrics
        baseline_metrics = baseline_eval.metrics
        
        # Calculate differences
        comparison = {
            "model_evaluation_id": model_evaluation_id,
            "baseline_evaluation_id": baseline_evaluation_id,
            "accuracy_comparison": {
                "model": model_metrics.get("accuracy", 0),
                "baseline": baseline_metrics.get("accuracy", 0),
                "difference": model_metrics.get("accuracy", 0) - baseline_metrics.get("accuracy", 0),
                "improvement_pct": ((model_metrics.get("accuracy", 0) - baseline_metrics.get("accuracy", 0)) / baseline_metrics.get("accuracy", 1)) * 100 if baseline_metrics.get("accuracy", 0) > 0 else 0
            },
            "response_time_comparison": {
                "model_avg": model_metrics.get("avg_response_time", 0),
                "baseline_avg": baseline_metrics.get("avg_response_time", 0),
                "difference": model_metrics.get("avg_response_time", 0) - baseline_metrics.get("avg_response_time", 0),
                "model_p95": model_metrics.get("p95_response_time", 0),
                "baseline_p95": baseline_metrics.get("p95_response_time", 0)
            },
            "f1_comparison": {
                "model": model_metrics.get("f1_score", 0),
                "baseline": baseline_metrics.get("f1_score", 0),
                "difference": model_metrics.get("f1_score", 0) - baseline_metrics.get("f1_score", 0)
            },
            "per_type_comparison": {}
        }
        
        # Compare per-question-type accuracy
        question_types = ["exact", "fuzzy", "reverse", "natural"]
        for qtype in question_types:
            key = f"{qtype}_match_accuracy"
            if key in model_metrics and key in baseline_metrics:
                comparison["per_type_comparison"][qtype] = {
                    "model": model_metrics[key],
                    "baseline": baseline_metrics[key],
                    "difference": model_metrics[key] - baseline_metrics[key]
                }
        
        # Resource consumption (placeholder - would need actual measurements)
        comparison["resource_consumption"] = {
            "model": {
                "memory": "Depends on model size and batch size",
                "gpu": "Required for training, optional for inference",
                "storage": "Model weights + training data"
            },
            "baseline": {
                "memory": "Elasticsearch index size",
                "gpu": "Not required",
                "storage": "Elasticsearch index"
            }
        }
        
        logger.info(f"Comparison completed: Model vs Baseline")
        logger.info(f"Accuracy difference: {comparison['accuracy_comparison']['difference']:.4f}")
        logger.info(f"Response time difference: {comparison['response_time_comparison']['difference']:.2f}ms")
        
        return comparison
    
    def generate_comparison_report(
        self,
        model_evaluation_id: int,
        baseline_evaluation_id: int
    ) -> str:
        """
        Generate comparison report
        
        Args:
            model_evaluation_id: Model evaluation ID
            baseline_evaluation_id: Baseline evaluation ID
        
        Returns:
            Path to generated report file
        
        Raises:
            EvaluationError: If report generation fails
        """
        try:
            logger.info(f"Generating comparison report")
            
            # Get comparison results
            comparison = self.compare_evaluations(model_evaluation_id, baseline_evaluation_id)
            
            # Load evaluations
            model_eval = self.db.query(Evaluation).filter(Evaluation.id == model_evaluation_id).first()
            baseline_eval = self.db.query(Evaluation).filter(Evaluation.id == baseline_evaluation_id).first()
            
            # Create report content
            report_lines = []
            report_lines.append(f"# 模型对比评估报告")
            report_lines.append(f"")
            report_lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report_lines.append(f"")
            
            # Evaluation information
            report_lines.append(f"## 评估信息")
            report_lines.append(f"")
            report_lines.append(f"| 项目 | 小模型方案 | 基准系统 (Elasticsearch) |")
            report_lines.append(f"|------|-----------|-------------------------|")
            report_lines.append(f"| 评估ID | {model_evaluation_id} | {baseline_evaluation_id} |")
            report_lines.append(f"| 评估时间 | {model_eval.evaluated_at.strftime('%Y-%m-%d %H:%M:%S')} | {baseline_eval.evaluated_at.strftime('%Y-%m-%d %H:%M:%S')} |")
            report_lines.append(f"")
            
            # Accuracy comparison
            acc_comp = comparison["accuracy_comparison"]
            report_lines.append(f"## 准确率对比")
            report_lines.append(f"")
            report_lines.append(f"| 指标 | 小模型方案 | 基准系统 | 差异 | 提升比例 |")
            report_lines.append(f"|------|-----------|---------|------|---------|")
            report_lines.append(f"| 准确率 | {acc_comp['model']:.4f} ({acc_comp['model']*100:.2f}%) | {acc_comp['baseline']:.4f} ({acc_comp['baseline']*100:.2f}%) | {acc_comp['difference']:+.4f} | {acc_comp['improvement_pct']:+.2f}% |")
            report_lines.append(f"")
            
            # F1 comparison
            f1_comp = comparison["f1_comparison"]
            report_lines.append(f"| F1分数 | {f1_comp['model']:.4f} | {f1_comp['baseline']:.4f} | {f1_comp['difference']:+.4f} | - |")
            report_lines.append(f"")
            
            # Per-type comparison
            if comparison["per_type_comparison"]:
                report_lines.append(f"### 分场景准确率对比")
                report_lines.append(f"")
                report_lines.append(f"| 问题类型 | 小模型方案 | 基准系统 | 差异 |")
                report_lines.append(f"|----------|-----------|---------|------|")
                
                type_labels = {
                    "exact": "精确匹配",
                    "fuzzy": "模糊匹配",
                    "reverse": "反向查询",
                    "natural": "自然语言"
                }
                
                for qtype, label in type_labels.items():
                    if qtype in comparison["per_type_comparison"]:
                        comp = comparison["per_type_comparison"][qtype]
                        report_lines.append(f"| {label} | {comp['model']:.4f} ({comp['model']*100:.2f}%) | {comp['baseline']:.4f} ({comp['baseline']*100:.2f}%) | {comp['difference']:+.4f} |")
                report_lines.append(f"")
            
            # Response time comparison
            time_comp = comparison["response_time_comparison"]
            report_lines.append(f"## 响应时间对比")
            report_lines.append(f"")
            report_lines.append(f"| 指标 | 小模型方案 (ms) | 基准系统 (ms) | 差异 (ms) |")
            report_lines.append(f"|------|----------------|--------------|----------|")
            report_lines.append(f"| 平均响应时间 | {time_comp['model_avg']:.2f} | {time_comp['baseline_avg']:.2f} | {time_comp['difference']:+.2f} |")
            report_lines.append(f"| P95响应时间 | {time_comp['model_p95']:.2f} | {time_comp['baseline_p95']:.2f} | {time_comp['model_p95'] - time_comp['baseline_p95']:+.2f} |")
            report_lines.append(f"")
            
            # Resource consumption
            report_lines.append(f"## 资源消耗对比")
            report_lines.append(f"")
            report_lines.append(f"### 小模型方案")
            report_lines.append(f"")
            report_lines.append(f"- **内存**: 取决于模型大小和批次大小")
            report_lines.append(f"- **GPU**: 训练阶段必需，推理阶段可选")
            report_lines.append(f"- **存储**: 模型权重 + 训练数据")
            report_lines.append(f"")
            report_lines.append(f"### 基准系统 (Elasticsearch)")
            report_lines.append(f"")
            report_lines.append(f"- **内存**: Elasticsearch索引大小")
            report_lines.append(f"- **GPU**: 不需要")
            report_lines.append(f"- **存储**: Elasticsearch索引")
            report_lines.append(f"")
            
            # Summary
            report_lines.append(f"## 对比总结")
            report_lines.append(f"")
            
            # Determine winner
            if acc_comp['difference'] > 0.05:
                winner = "小模型方案在准确率上有明显优势"
            elif acc_comp['difference'] > 0:
                winner = "小模型方案在准确率上略有优势"
            elif acc_comp['difference'] > -0.05:
                winner = "两种方案准确率相当"
            else:
                winner = "基准系统在准确率上有优势"
            
            report_lines.append(f"**准确率**: {winner}")
            report_lines.append(f"")
            
            if time_comp['difference'] < 0:
                speed_winner = "小模型方案响应更快"
            elif time_comp['difference'] < 100:
                speed_winner = "两种方案响应时间相当"
            else:
                speed_winner = "基准系统响应更快"
            
            report_lines.append(f"**响应时间**: {speed_winner}")
            report_lines.append(f"")
            
            # Recommendation
            report_lines.append(f"### 建议")
            report_lines.append(f"")
            
            if acc_comp['model'] >= 0.95 and acc_comp['difference'] > 0:
                report_lines.append(f"- 小模型方案达到了预期目标（准确率≥95%）且优于基准系统")
                report_lines.append(f"- 建议采用小模型方案，可以提供更好的用户体验")
            elif acc_comp['model'] >= 0.90:
                report_lines.append(f"- 小模型方案接近目标，建议进一步优化")
                report_lines.append(f"- 可以考虑增加训练数据或调整训练参数")
            else:
                report_lines.append(f"- 小模型方案尚未达到预期目标")
                report_lines.append(f"- 建议重新审视训练策略或考虑使用基准系统")
            
            report_lines.append(f"")
            
            # Save report
            report_filename = f"comparison_{model_evaluation_id}_vs_{baseline_evaluation_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            report_path = self.reports_dir / report_filename
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_lines))
            
            logger.info(f"Comparison report generated: {report_path}")
            
            return str(report_path)
        
        except Exception as e:
            logger.error(f"Failed to generate comparison report: {e}")
            raise EvaluationError(f"Comparison report generation failed: {e}")

    def calculate_training_cost(
        self,
        training_job_id: int,
        api_cost_per_1k_tokens: float = 0.002,  # 通义千问API成本
        gpu_cost_per_hour: float = 1.0  # GPU成本（假设值）
    ) -> Dict[str, Any]:
        """
        Calculate training cost
        
        Args:
            training_job_id: Training job ID
            api_cost_per_1k_tokens: API cost per 1000 tokens
            gpu_cost_per_hour: GPU cost per hour
        
        Returns:
            Dictionary with cost breakdown
        """
        # Load training job
        job = self.db.query(TrainingJob).filter(TrainingJob.id == training_job_id).first()
        if not job:
            raise EvaluationError(f"Training job {training_job_id} not found")
        
        # Calculate API cost (for QA generation)
        qa_pairs = self.db.query(QAPair).filter(
            QAPair.dataset_id == job.dataset_id
        ).all()
        
        # Estimate tokens used for QA generation
        # Rough estimate: 100 tokens per QA pair (input + output)
        estimated_tokens = len(qa_pairs) * 100
        api_cost = (estimated_tokens / 1000) * api_cost_per_1k_tokens
        
        # Calculate training time cost
        if job.started_at and job.completed_at:
            training_hours = (job.completed_at - job.started_at).total_seconds() / 3600
            training_cost = training_hours * gpu_cost_per_hour
        else:
            training_hours = 0
            training_cost = 0
        
        # Storage cost (simplified)
        storage_cost = 0.01  # Placeholder
        
        total_cost = api_cost + training_cost + storage_cost
        
        return {
            "api_cost": api_cost,
            "api_tokens": estimated_tokens,
            "training_cost": training_cost,
            "training_hours": training_hours,
            "storage_cost": storage_cost,
            "total_cost": total_cost,
            "currency": "USD"
        }
    
    def calculate_inference_cost(
        self,
        num_queries: int,
        avg_response_time_ms: float,
        gpu_cost_per_hour: float = 1.0
    ) -> Dict[str, Any]:
        """
        Calculate inference cost
        
        Args:
            num_queries: Number of queries
            avg_response_time_ms: Average response time in milliseconds
            gpu_cost_per_hour: GPU cost per hour
        
        Returns:
            Dictionary with cost breakdown
        """
        # Calculate total inference time
        total_time_hours = (num_queries * avg_response_time_ms / 1000) / 3600
        
        # Calculate cost
        inference_cost = total_time_hours * gpu_cost_per_hour
        
        # Cost per query
        cost_per_query = inference_cost / num_queries if num_queries > 0 else 0
        
        return {
            "num_queries": num_queries,
            "total_time_hours": total_time_hours,
            "inference_cost": inference_cost,
            "cost_per_query": cost_per_query,
            "currency": "USD"
        }
    
    def calculate_baseline_cost(
        self,
        num_queries: int,
        avg_response_time_ms: float,
        es_cost_per_hour: float = 0.5  # Elasticsearch成本（假设值）
    ) -> Dict[str, Any]:
        """
        Calculate baseline system cost
        
        Args:
            num_queries: Number of queries
            avg_response_time_ms: Average response time in milliseconds
            es_cost_per_hour: Elasticsearch cost per hour
        
        Returns:
            Dictionary with cost breakdown
        """
        # Calculate total query time
        total_time_hours = (num_queries * avg_response_time_ms / 1000) / 3600
        
        # Calculate cost
        query_cost = total_time_hours * es_cost_per_hour
        
        # Cost per query
        cost_per_query = query_cost / num_queries if num_queries > 0 else 0
        
        # No training cost for baseline
        return {
            "num_queries": num_queries,
            "total_time_hours": total_time_hours,
            "query_cost": query_cost,
            "cost_per_query": cost_per_query,
            "training_cost": 0,  # No training needed
            "currency": "USD"
        }
    
    def generate_cost_comparison(
        self,
        training_job_id: int,
        model_evaluation_id: int,
        baseline_evaluation_id: int
    ) -> Dict[str, Any]:
        """
        Generate cost comparison between model and baseline
        
        Args:
            training_job_id: Training job ID
            model_evaluation_id: Model evaluation ID
            baseline_evaluation_id: Baseline evaluation ID
        
        Returns:
            Dictionary with cost comparison
        """
        # Load evaluations
        model_eval = self.db.query(Evaluation).filter(Evaluation.id == model_evaluation_id).first()
        baseline_eval = self.db.query(Evaluation).filter(Evaluation.id == baseline_evaluation_id).first()
        
        if not model_eval or not baseline_eval:
            raise EvaluationError("Evaluations not found")
        
        # Calculate training cost
        training_cost = self.calculate_training_cost(training_job_id)
        
        # Calculate inference costs
        model_metrics = model_eval.metrics
        baseline_metrics = baseline_eval.metrics
        
        num_test_cases = model_metrics.get("total", 0)
        
        model_inference_cost = self.calculate_inference_cost(
            num_test_cases,
            model_metrics.get("avg_response_time", 0)
        )
        
        baseline_inference_cost = self.calculate_baseline_cost(
            num_test_cases,
            baseline_metrics.get("avg_response_time", 0)
        )
        
        # Total costs
        model_total_cost = training_cost["total_cost"] + model_inference_cost["inference_cost"]
        baseline_total_cost = baseline_inference_cost["query_cost"]
        
        return {
            "model_costs": {
                "training": training_cost,
                "inference": model_inference_cost,
                "total": model_total_cost
            },
            "baseline_costs": {
                "training": 0,
                "inference": baseline_inference_cost,
                "total": baseline_total_cost
            },
            "comparison": {
                "cost_difference": model_total_cost - baseline_total_cost,
                "model_more_expensive": model_total_cost > baseline_total_cost,
                "cost_ratio": model_total_cost / baseline_total_cost if baseline_total_cost > 0 else 0
            },
            "note": "成本估算基于假设的价格，实际成本可能有所不同"
        }
