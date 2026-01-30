"""
训练数据生成服务 - 使用大模型泛化标准银行数据

本模块实现大模型-小模型协同训练方案：
1. 大模型：将标准银行数据泛化为多样化训练样本
2. 小模型：学习银行实体识别的专业化任务

作者：AI Assistant
日期：2026-01-21
"""

import json
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.bank_code import BankCode
from app.core.database import get_db
from app.services.query_service import QueryService

logger = logging.getLogger(__name__)


class TrainingDataGenerator:
    """
    训练数据生成器
    
    使用大模型将标准银行数据泛化为小模型训练数据
    """
    
    def __init__(self, db: Session = None):
        self.db = db
        self.query_service = None  # 延迟初始化
    
    def generate_bank_variations(self, bank_record: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        为单个银行记录生成多种表达方式
        
        Args:
            bank_record: 标准银行记录 {"bank_name": "...", "bank_code": "..."}
            
        Returns:
            List of training samples with variations
        """
        try:
            bank_name = bank_record["bank_name"]
            bank_code = bank_record["bank_code"]
            
            # 构建大模型提示词
            prompt = f"""基于以下标准银行信息，生成用户可能的各种表达方式：

标准名称：{bank_name}
联行号：{bank_code}

请生成以下类型的用户表达，每种类型2-3个变体：

1. 简称表达（去掉"股份有限公司"等）
2. 口语化表达（调整词序）
3. 地区优先表达（地名在前）
4. 不完整表达（省略部分信息）
5. 别名表达（如农行、工行等）

输出JSON格式：
{{
  "variations": [
    {{
      "user_input": "用户表达",
      "entities": {{
        "bank_name": "银行名称",
        "location": "地理位置", 
        "branch_name": "支行名称"
      }},
      "confidence": 0.95
    }}
  ]
}}

JSON:"""

            # 使用大模型生成变体
            if self._get_query_service().model and self._get_query_service().tokenizer:
                response = self._generate_with_llm(prompt)
                variations = self._parse_variations(response, bank_record)
            else:
                # 如果大模型不可用，使用规则生成
                variations = self._generate_with_rules(bank_record)
            
            logger.info(f"Generated {len(variations)} variations for {bank_name}")
            return variations
            
        except Exception as e:
            logger.error(f"Failed to generate variations for {bank_record}: {e}")
            return []
    
    def _get_query_service(self):
        """延迟初始化QueryService"""
        if self.query_service is None:
            if self.db is None:
                self.db = next(get_db())
            self.query_service = QueryService(self.db)
        return self.query_service
    
    def _generate_with_llm(self, prompt: str) -> str:
        """使用大模型生成变体"""
        try:
            query_service = self._get_query_service()
            
            # 加载模型（如果未加载）
            if not query_service.model:
                # 使用最新的训练模型
                query_service.load_model()
            
            # 生成响应
            inputs = query_service.tokenizer(
                prompt,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            )
            
            if query_service.device in ["cuda", "mps"]:
                inputs = {k: v.to(query_service.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = query_service.model.generate(
                    **inputs,
                    max_new_tokens=512,
                    temperature=0.7,  # 稍高温度增加创造性
                    top_p=0.9,
                    do_sample=True,
                    pad_token_id=query_service.tokenizer.pad_token_id,
                    eos_token_id=query_service.tokenizer.eos_token_id
                )
            
            response = query_service.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return response.split("JSON:")[-1].strip() if "JSON:" in response else response
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return ""
    
    def _parse_variations(self, response: str, bank_record: Dict[str, str]) -> List[Dict[str, Any]]:
        """解析大模型生成的变体"""
        try:
            # 尝试解析JSON
            if "{" in response and "}" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]
                data = json.loads(json_str)
                
                if "variations" in data:
                    return data["variations"]
            
            # JSON解析失败，使用规则生成
            return self._generate_with_rules(bank_record)
            
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return self._generate_with_rules(bank_record)
    
    def _generate_with_rules(self, bank_record: Dict[str, str]) -> List[Dict[str, Any]]:
        """使用规则生成变体（备用方案）"""
        bank_name = bank_record["bank_name"]
        bank_code = bank_record["bank_code"]
        
        variations = []
        
        # 提取银行基本信息
        import re
        
        # 提取银行主名称
        main_bank = re.sub(r'股份有限公司|有限公司', '', bank_name)
        
        # 提取地理位置
        location_match = re.search(r'([\u4e00-\u9fff]{2,8}[市县区镇]?)', bank_name)
        location = location_match.group(1) if location_match else ""
        
        # 提取支行名称
        branch_match = re.search(r'([^银行]{2,10}[支分]行)', bank_name)
        branch = branch_match.group(1) if branch_match else ""
        
        # 生成变体
        if location and branch:
            # 简称表达
            variations.append({
                "user_input": f"{main_bank}{location}{branch}",
                "entities": {
                    "bank_name": main_bank,
                    "location": location,
                    "branch_name": branch
                },
                "confidence": 0.9
            })
            
            # 口语化表达
            variations.append({
                "user_input": f"{location}{branch.replace('支行', '')}的{main_bank}",
                "entities": {
                    "bank_name": main_bank,
                    "location": location,
                    "branch_name": branch.replace('支行', '')
                },
                "confidence": 0.85
            })
            
            # 不完整表达
            variations.append({
                "user_input": f"{main_bank}{branch}",
                "entities": {
                    "bank_name": main_bank,
                    "location": "",
                    "branch_name": branch
                },
                "confidence": 0.8
            })
        
        return variations
    
    def generate_comprehensive_dataset(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        为所有银行生成全面的训练数据集
        
        Args:
            limit: 限制处理的银行数量（用于测试）
            
        Returns:
            完整的训练数据集
        """
        training_data = []
        
        try:
            # 获取数据库连接
            db = next(get_db())
            
            # 查询所有银行记录
            query = db.query(BankCode)
            if limit:
                query = query.limit(limit)
            
            bank_records = query.all()
            
            logger.info(f"Processing {len(bank_records)} bank records...")
            
            for i, record in enumerate(bank_records):
                bank_record = {
                    "bank_name": record.bank_name,
                    "bank_code": record.bank_code
                }
                
                # 为每个银行生成变体
                variations = self.generate_bank_variations(bank_record)
                
                # 添加到训练数据
                for variation in variations:
                    training_sample = {
                        "id": f"{record.id}_{len(training_data)}",
                        "original_bank": bank_record,
                        "user_input": variation["user_input"],
                        "entities": variation["entities"],
                        "confidence": variation.get("confidence", 0.8),
                        "created_at": "2026-01-21"
                    }
                    training_data.append(training_sample)
                
                # 进度日志
                if (i + 1) % 100 == 0:
                    logger.info(f"Processed {i + 1}/{len(bank_records)} banks, generated {len(training_data)} samples")
            
            logger.info(f"Dataset generation completed: {len(training_data)} training samples")
            return training_data
            
        except Exception as e:
            logger.error(f"Failed to generate comprehensive dataset: {e}")
            return []
    
    def save_training_dataset(self, training_data: List[Dict[str, Any]], filename: str = "bank_ner_training_data.json"):
        """
        保存训练数据集到文件
        
        Args:
            training_data: 训练数据
            filename: 保存文件名
        """
        try:
            filepath = f"data/{filename}"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(training_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Training dataset saved to {filepath}")
            
            # 生成统计报告
            self._generate_dataset_report(training_data, filepath.replace('.json', '_report.txt'))
            
        except Exception as e:
            logger.error(f"Failed to save training dataset: {e}")
    
    def _generate_dataset_report(self, training_data: List[Dict[str, Any]], report_file: str):
        """生成数据集统计报告"""
        try:
            total_samples = len(training_data)
            unique_banks = len(set(sample["original_bank"]["bank_name"] for sample in training_data))
            avg_confidence = sum(sample["confidence"] for sample in training_data) / total_samples
            
            # 统计实体类型
            bank_entities = set()
            location_entities = set()
            branch_entities = set()
            
            for sample in training_data:
                entities = sample["entities"]
                if entities.get("bank_name"):
                    bank_entities.add(entities["bank_name"])
                if entities.get("location"):
                    location_entities.add(entities["location"])
                if entities.get("branch_name"):
                    branch_entities.add(entities["branch_name"])
            
            report = f"""
# 银行NER训练数据集报告

## 基本统计
- 总样本数: {total_samples:,}
- 覆盖银行数: {unique_banks:,}
- 平均置信度: {avg_confidence:.3f}
- 每银行平均样本数: {total_samples/unique_banks:.1f}

## 实体统计
- 银行名称实体: {len(bank_entities):,}
- 地理位置实体: {len(location_entities):,}
- 支行名称实体: {len(branch_entities):,}

## 数据质量
- 高置信度样本 (>0.9): {sum(1 for s in training_data if s['confidence'] > 0.9):,}
- 中置信度样本 (0.8-0.9): {sum(1 for s in training_data if 0.8 <= s['confidence'] <= 0.9):,}
- 低置信度样本 (<0.8): {sum(1 for s in training_data if s['confidence'] < 0.8):,}

## 生成时间
{training_data[0]['created_at'] if training_data else 'N/A'}

---
此数据集可用于训练专业的银行实体识别模型
"""
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            logger.info(f"Dataset report saved to {report_file}")
            
        except Exception as e:
            logger.error(f"Failed to generate dataset report: {e}")


# 导入torch（如果需要）
try:
    import torch
except ImportError:
    logger.warning("PyTorch not available, LLM generation will be disabled")
    torch = None