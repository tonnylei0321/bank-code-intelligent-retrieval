"""
并行训练数据生成器

使用多线程和多个LLM API并行生成大规模训练数据
支持15万条样本数据，每条生成7个训练样本，总计105万条训练数据

特性：
1. 多线程并行处理
2. 多个LLM API负载均衡
3. 数据库批量写入优化
4. 进度监控和错误恢复
5. 内存优化和资源管理

作者：AI Assistant
日期：2026-01-30
"""

import asyncio
import aiohttp
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from queue import Queue
import logging
from datetime import datetime
import random

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.bank_code import BankCode
from app.models.qa_pair import QAPair
from app.models.dataset import Dataset
from app.core.database import get_db, engine

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM配置"""
    name: str
    base_url: str
    api_key: str
    model_name: str
    max_requests_per_minute: int = 60


class ParallelTrainingGenerator:
    """
    并行训练数据生成器
    
    使用多个LLM API并行生成训练数据，支持大规模数据处理
    """
    
    def __init__(self, dataset_id: int, progress_callback: Optional[callable] = None):
        """
        初始化生成器
        
        Args:
            dataset_id: 数据集ID
            progress_callback: 进度回调函数，接收stats字典参数
        """
        self.dataset_id = dataset_id
        self.progress_callback = progress_callback
        
        # 配置多个LLM
        self.llm_configs = [
            LLMConfig(
                name="阿里通义千问",
                base_url="https://dashscope.aliyuncs.com/api/v1/services/aigc",
                api_key="sk-03f639acddb8425abd3c1b9722ec1014",
                model_name="qwen-turbo",
                max_requests_per_minute=100
            ),
            LLMConfig(
                name="DeepSeek",
                base_url="https://api.deepseek.com",
                api_key="sk-9b923042a7714c9cb68ff338ab68d36d",
                model_name="deepseek-chat",
                max_requests_per_minute=100
            )
        ]
        
        # 线程池配置 - 优化大数据集
        if hasattr(self, '_bank_count') and self._bank_count > 50000:
            self.max_workers = 16  # 大数据集使用更多线程
        else:
            self.max_workers = 8  # 每个LLM 4个线程，2个LLM总共8个线程
        self.batch_size = 100  # 数据库批量写入大小
        
        # 统计信息
        self.stats = {
            "total_banks": 0,
            "processed_banks": 0,
            "generated_samples": 0,
            "failed_banks": 0,
            "start_time": None,
            "errors": []
        }
        
        # 线程安全的队列
        self.result_queue = Queue()
        self.error_queue = Queue()
        
        # 数据库会话工厂
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        logger.info(f"ParallelTrainingGenerator initialized with {len(self.llm_configs)} LLMs")
    
    def configure_llm(self, llm_name: str):
        """
        根据用户选择配置单个LLM
        
        Args:
            llm_name: LLM名称 ("qwen", "deepseek", "chatglm")
        """
        if llm_name == "qwen":
            self.llm_configs = [
                LLMConfig(
                    name="阿里通义千问",
                    base_url="https://dashscope.aliyuncs.com/api/v1/services/aigc",
                    api_key="sk-03f639acddb8425abd3c1b9722ec1014",
                    model_name="qwen-turbo",
                    max_requests_per_minute=100
                )
            ]
        elif llm_name == "deepseek":
            self.llm_configs = [
                LLMConfig(
                    name="DeepSeek",
                    base_url="https://api.deepseek.com",
                    api_key="sk-9b923042a7714c9cb68ff338ab68d36d",
                    model_name="deepseek-chat",
                    max_requests_per_minute=100
                )
            ]
        elif llm_name == "chatglm":
            self.llm_configs = [
                LLMConfig(
                    name="智谱ChatGLM",
                    base_url="https://open.bigmodel.cn/api/paas/v4",
                    api_key="your-chatglm-api-key",  # 需要配置实际的API密钥
                    model_name="glm-4",
                    max_requests_per_minute=100
                )
            ]
        else:
            # 默认使用多LLM并行
            pass
        
        logger.info(f"Configured LLM: {llm_name}, using {len(self.llm_configs)} LLM(s)")
    
    def set_bank_count(self, count: int):
        """设置银行数量以优化配置"""
        self._bank_count = count
        if count > 50000:
            self.max_workers = 16
            logger.info(f"Large dataset detected ({count:,} banks), using {self.max_workers} workers")
    
    async def generate_samples_async(
        self, 
        bank_name: str, 
        bank_code: str, 
        bank_id: int,
        llm_config: LLMConfig,
        session: aiohttp.ClientSession,
        samples_per_bank: int = 7
    ) -> List[Dict[str, Any]]:
        """
        异步生成单个银行的训练样本
        
        Args:
            bank_name: 银行名称
            bank_code: 联行号
            bank_id: 银行ID
            llm_config: LLM配置
            session: HTTP会话
            samples_per_bank: 每个银行生成的样本数量
            
        Returns:
            训练样本列表
        """
        try:
            print(f"🔧 DEBUG: generate_samples_async started for {bank_name} using {llm_config.name}")
            
            # 构建提示词
            prompt = self._build_prompt(bank_name, bank_code, samples_per_bank)
            print(f"🔧 DEBUG: Built prompt for {bank_name}, length: {len(prompt)}")
            
            # 调用LLM API
            print(f"🔧 DEBUG: Calling LLM API for {bank_name} using {llm_config.name}")
            response = await self._call_llm_api(prompt, llm_config, session)
            print(f"🔧 DEBUG: LLM API response received for {bank_name}, length: {len(response) if response else 0}")
            
            # 解析响应
            samples = self._parse_llm_response(response, bank_name, bank_code, bank_id, samples_per_bank)
            print(f"🔧 DEBUG: Parsed {len(samples)} samples for {bank_name}")
            
            logger.debug(f"Generated {len(samples)} samples for {bank_name} using {llm_config.name}")
            return samples
            
        except Exception as e:
            logger.error(f"Failed to generate samples for {bank_name} using {llm_config.name}: {e}")
            # 返回规则生成的样本作为备用
            return self._generate_rule_based_samples(bank_name, bank_code, bank_id, samples_per_bank)
    
    def _build_prompt(self, bank_name: str, bank_code: str, samples_per_bank: int = 7) -> str:
        """构建LLM提示词"""
        return f"""你是一个银行业务专家。请为以下银行生成{samples_per_bank}种不同的自然语言查询方式。

银行信息：
- 完整名称：{bank_name}
- 联行号：{bank_code}

要求：
1. 生成{samples_per_bank}种用户可能的问法
2. 包括：完整名称、简称、口语化表达、地区+银行名、不完整描述等
3. 模拟真实用户的查询习惯（简短、自然、口语化）
4. 每种问法要自然、简洁，不要太长

请直接返回JSON格式（不要有其他文字）：
{{
    "questions": [
        "问法1",
        "问法2", 
        "问法3",
        "问法4",
        "问法5",
        "问法6",
        "问法7"
    ]
}}

现在请为上述银行生成{samples_per_bank}种问法："""
    
    async def _call_llm_api(
        self, 
        prompt: str, 
        llm_config: LLMConfig, 
        session: aiohttp.ClientSession
    ) -> str:
        """
        调用LLM API
        
        Args:
            prompt: 提示词
            llm_config: LLM配置
            session: HTTP会话
            
        Returns:
            LLM响应文本
        """
        print(f"🔧 DEBUG: _call_llm_api started for {llm_config.name}")
        
        if llm_config.name == "阿里通义千问":
            return await self._call_qwen_api(prompt, llm_config, session)
        elif llm_config.name == "DeepSeek":
            return await self._call_deepseek_api(prompt, llm_config, session)
        else:
            raise ValueError(f"Unsupported LLM: {llm_config.name}")
    
    async def _call_qwen_api(
        self, 
        prompt: str, 
        llm_config: LLMConfig, 
        session: aiohttp.ClientSession
    ) -> str:
        """调用阿里通义千问API"""
        print(f"🔧 DEBUG: _call_qwen_api started")
        
        headers = {
            "Authorization": f"Bearer {llm_config.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": llm_config.model_name,
            "input": {
                "messages": [
                    {"role": "system", "content": "你是一个专业的银行业务助手。"},
                    {"role": "user", "content": prompt}
                ]
            },
            "parameters": {
                "temperature": 0.7,
                "max_tokens": 1000
            }
        }
        
        print(f"🔧 DEBUG: Making HTTP POST request to {llm_config.base_url}/text-generation/generation")
        
        try:
            async with session.post(
                f"{llm_config.base_url}/text-generation/generation",
                headers=headers,
                json=data,
                timeout=30
            ) as response:
                print(f"🔧 DEBUG: HTTP response status: {response.status}")
                result = await response.json()
                print(f"🔧 DEBUG: HTTP response received, parsing JSON")
                response_text = result["output"]["text"]
                print(f"🔧 DEBUG: Extracted response text, length: {len(response_text)}")
                return response_text
        except Exception as e:
            print(f"🔧 DEBUG: Error in _call_qwen_api: {e}")
            raise
    
    async def _call_deepseek_api(
        self, 
        prompt: str, 
        llm_config: LLMConfig, 
        session: aiohttp.ClientSession
    ) -> str:
        """调用DeepSeek API"""
        print(f"🔧 DEBUG: _call_deepseek_api started")
        
        headers = {
            "Authorization": f"Bearer {llm_config.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": llm_config.model_name,
            "messages": [
                {"role": "system", "content": "你是一个专业的银行业务助手。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        print(f"🔧 DEBUG: Making HTTP POST request to {llm_config.base_url}/v1/chat/completions")
        
        try:
            async with session.post(
                f"{llm_config.base_url}/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            ) as response:
                print(f"🔧 DEBUG: HTTP response status: {response.status}")
                result = await response.json()
                print(f"🔧 DEBUG: HTTP response received, parsing JSON")
                response_text = result["choices"][0]["message"]["content"]
                print(f"🔧 DEBUG: Extracted response text, length: {len(response_text)}")
                return response_text
        except Exception as e:
            print(f"🔧 DEBUG: Error in _call_deepseek_api: {e}")
            raise
    
    def _parse_llm_response(
        self, 
        response: str, 
        bank_name: str, 
        bank_code: str, 
        bank_id: int,
        samples_per_bank: int = 7
    ) -> List[Dict[str, Any]]:
        """
        解析LLM响应
        
        Args:
            response: LLM响应文本
            bank_name: 银行名称
            bank_code: 联行号
            bank_id: 银行ID
            samples_per_bank: 每个银行生成的样本数量
            
        Returns:
            训练样本列表
        """
        try:
            # 提取JSON部分
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
                questions = result.get("questions", [])
                
                # 构建训练样本
                samples = []
                for i, question in enumerate(questions[:samples_per_bank]):  # 限制指定数量
                    if question and len(question.strip()) > 0:
                        samples.append({
                            "dataset_id": self.dataset_id,
                            "source_record_id": bank_id,
                            "question": question.strip(),
                            "answer": f"{bank_name}的联行号是{bank_code}",
                            "question_type": "natural",
                            "split_type": "train",
                            "bank_name": bank_name,
                            "bank_code": bank_code,
                            "generated_at": datetime.utcnow()
                        })
                
                return samples
            else:
                logger.warning(f"No JSON found in LLM response for {bank_name}")
                return self._generate_rule_based_samples(bank_name, bank_code, bank_id, samples_per_bank)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            return self._generate_rule_based_samples(bank_name, bank_code, bank_id, samples_per_bank)
            logger.error(f"Failed to parse LLM JSON response: {e}")
            return self._generate_rule_based_samples(bank_name, bank_code, bank_id)
    
    def _generate_rule_based_samples(
        self, 
        bank_name: str, 
        bank_code: str, 
        bank_id: int,
        samples_per_bank: int = 7
    ) -> List[Dict[str, Any]]:
        """
        基于规则生成样本（备用方案）
        
        Args:
            bank_name: 银行名称
            bank_code: 联行号
            bank_id: 银行ID
            samples_per_bank: 每个银行生成的样本数量
            
        Returns:
            训练样本列表
        """
        samples = []
        
        # 1. 完整名称
        samples.append({
            "dataset_id": self.dataset_id,
            "source_record_id": bank_id,
            "question": bank_name,
            "answer": f"{bank_name}的联行号是{bank_code}",
            "question_type": "exact",
            "split_type": "train",
            "bank_name": bank_name,
            "bank_code": bank_code,
            "generated_at": datetime.utcnow()
        })
        
        # 2. 简称
        short_name = bank_name.replace("股份有限公司", "").replace("有限公司", "")
        if short_name != bank_name and len(samples) < samples_per_bank:
            samples.append({
                "dataset_id": self.dataset_id,
                "source_record_id": bank_id,
                "question": short_name,
                "answer": f"{bank_name}的联行号是{bank_code}",
                "question_type": "fuzzy",
                "split_type": "train",
                "bank_name": bank_name,
                "bank_code": bank_code,
                "generated_at": datetime.utcnow()
            })
        
        # 3-N. 其他变体
        variations = [
            f"{bank_name}的联行号",
            f"{short_name}联行号",
            f"{bank_name}代码",
            f"{short_name}的代码是多少",
            f"查询{bank_name}联行号",
            f"{bank_name}银行代码",
            f"{short_name}的联行号是什么"
        ]
        
        for variation in variations:
            if len(samples) >= samples_per_bank:
                break
            samples.append({
                "dataset_id": self.dataset_id,
                "source_record_id": bank_id,
                "question": variation,
                "answer": f"{bank_name}的联行号是{bank_code}",
                "question_type": "natural",
                "split_type": "train",
                "bank_name": bank_name,
                "bank_code": bank_code,
                "generated_at": datetime.utcnow()
            })
        
        return samples[:samples_per_bank]  # 确保返回指定数量
    
    def _save_samples_batch(self, samples: List[Dict[str, Any]]):
        """
        优化的批量保存样本到数据库
        
        Args:
            samples: 样本列表
        """
        if not samples:
            return
        
        db = self.SessionLocal()
        try:
            # 使用批量插入优化性能
            batch_size = 1000  # 每批1000条记录
            total_saved = 0
            
            for i in range(0, len(samples), batch_size):
                batch = samples[i:i + batch_size]
                
                # 使用bulk_insert_mappings进行高效批量插入
                db.bulk_insert_mappings(QAPair, batch)
                total_saved += len(batch)
                
                # 每批提交一次，避免内存占用过大
                if i % (batch_size * 5) == 0:  # 每5000条提交一次
                    db.commit()
                    logger.info(f"Batch saved: {total_saved}/{len(samples)} samples")
            
            # 最终提交
            db.commit()
            
            self.stats["generated_samples"] += len(samples)
            logger.info(f"Successfully saved {len(samples)} samples to database in batches")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save samples batch: {e}")
            raise
        finally:
            db.close()
    
    async def process_bank_batch_async(
        self, 
        banks: List[Dict[str, Any]], 
        llm_config: LLMConfig
    ):
        """
        异步处理银行批次
        
        Args:
            banks: 银行列表
            llm_config: LLM配置
        """
        async with aiohttp.ClientSession() as session:
            # 控制请求频率
            semaphore = asyncio.Semaphore(4)  # 每个LLM最多4个并发请求
            
            async def process_single_bank(bank):
                async with semaphore:
                    try:
                        samples = await self.generate_samples_async(
                            bank["bank_name"],
                            bank["bank_code"],
                            bank["id"],
                            llm_config,
                            session
                        )
                        
                        # 添加到结果队列
                        self.result_queue.put(samples)
                        self.stats["processed_banks"] += 1
                        
                        # 请求间隔（避免超过API限制）
                        await asyncio.sleep(60 / llm_config.max_requests_per_minute)
                        
                    except Exception as e:
                        self.error_queue.put({
                            "bank": bank,
                            "error": str(e),
                            "llm": llm_config.name
                        })
                        self.stats["failed_banks"] += 1
            
            # 并发处理所有银行
            tasks = [process_single_bank(bank) for bank in banks]
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def run_parallel_generation_for_banks(
        self, 
        bank_ids: List[int], 
        samples_per_bank: int = 7,
        use_llm: bool = False
    ) -> List[Dict[str, Any]]:
        """
        为指定的银行ID列表运行并行生成
        
        Args:
            bank_ids: 银行ID列表
            samples_per_bank: 每个银行生成的样本数量
            use_llm: 是否使用LLM（False=规则生成，True=LLM生成）
        
        Returns:
            生成的训练样本列表
        """
        logger.info(f"Starting parallel generation for {len(bank_ids)} specific banks...")
        print(f"🔧 DEBUG: Starting parallel generation for {len(bank_ids)} specific banks...")
        print(f"🔧 DEBUG: Bank IDs: {bank_ids[:10]}...")  # Show first 10 IDs
        self.stats["start_time"] = time.time()
        
        # 获取指定的银行数据
        db = self.SessionLocal()
        try:
            # 确保获取最新的数据
            db.execute("BEGIN IMMEDIATE;")  # 强制刷新事务
            db.rollback()
            
            banks = []
            for bank_id in bank_ids:
                print(f"🔧 DEBUG: Looking for bank ID {bank_id}")
                record = db.query(BankCode).filter(BankCode.id == bank_id).first()
                if record:
                    banks.append({
                        "id": record.id,
                        "bank_name": record.bank_name,
                        "bank_code": record.bank_code
                    })
                    print(f"🔧 DEBUG: Found bank {record.id}: {record.bank_name}")
                else:
                    print(f"🔧 DEBUG: Bank ID {bank_id} not found!")
                    # 尝试查询所有银行看看数据库连接是否正常
                    total_count = db.query(BankCode).count()
                    print(f"🔧 DEBUG: Total banks in database: {total_count}")
                    if bank_id <= 5:  # 只对前几个ID做详细检查
                        all_ids = [r.id for r in db.query(BankCode.id).limit(10).all()]
                        print(f"🔧 DEBUG: First 10 bank IDs in database: {all_ids}")
            
            self.stats["total_banks"] = len(banks)
            logger.info(f"Found {len(banks)} banks to process")
            print(f"🔧 DEBUG: Found {len(banks)} banks to process")
            
        except Exception as e:
            print(f"🔧 DEBUG: Error querying banks: {e}")
            logger.error(f"Error querying banks: {e}")
        finally:
            db.close()
        
        if not banks:
            logger.warning("No banks found for processing")
            print("🔧 DEBUG: No banks found for processing")
            return []
        
        # 使用规则生成或LLM生成
        all_samples = []
        
        if use_llm:
            # 使用LLM并行生成
            all_samples = self._run_llm_parallel_generation(banks, samples_per_bank)
        else:
            # 使用规则生成（快速模式）
            all_samples = self._run_rule_based_generation(banks, samples_per_bank)
        
        # 批量保存到数据库
        self._save_samples_batch(all_samples)
        
        # 输出统计
        elapsed = time.time() - self.stats["start_time"]
        logger.info(f"Parallel generation completed in {elapsed:.2f} seconds")
        logger.info(f"Generated {len(all_samples)} samples for {len(banks)} banks")
        
        return all_samples
    
    def run_parallel_generation_with_data(
        self, 
        banks_data: List[Dict[str, Any]], 
        samples_per_bank: int = 7,
        use_llm: bool = False
    ) -> List[Dict[str, Any]]:
        """
        使用直接传递的银行数据运行并行生成（避免数据库会话问题）
        
        Args:
            banks_data: 银行数据列表 [{"id": 1, "bank_name": "...", "bank_code": "..."}, ...]
            samples_per_bank: 每个银行生成的样本数量
            use_llm: 是否使用LLM（False=规则生成，True=LLM生成）
        
        Returns:
            生成的训练样本列表
        """
        logger.info(f"Starting parallel generation with direct data for {len(banks_data)} banks...")
        print(f"🔧 DEBUG: Starting parallel generation with direct data for {len(banks_data)} banks...")
        self.stats["start_time"] = time.time()
        self.stats["total_banks"] = len(banks_data)
        
        if not banks_data:
            logger.warning("No banks data provided for processing")
            print("🔧 DEBUG: No banks data provided for processing")
            return []
        
        # 使用规则生成或LLM生成
        all_samples = []
        
        if use_llm:
            # 使用LLM并行生成
            all_samples = self._run_llm_parallel_generation(banks_data, samples_per_bank)
        else:
            # 使用规则生成（快速模式）
            all_samples = self._run_rule_based_generation(banks_data, samples_per_bank)
        
        # 批量保存到数据库
        self._save_samples_batch(all_samples)
        
        # 输出统计
        elapsed = time.time() - self.stats["start_time"]
        logger.info(f"Parallel generation completed in {elapsed:.2f} seconds")
        logger.info(f"Generated {len(all_samples)} samples for {len(banks_data)} banks")
        
        return all_samples
    
    def _run_rule_based_generation(
        self, 
        banks: List[Dict[str, Any]], 
        samples_per_bank: int
    ) -> List[Dict[str, Any]]:
        """
        使用规则生成（多线程并行）
        
        Args:
            banks: 银行列表
            samples_per_bank: 每个银行生成的样本数量
        
        Returns:
            生成的训练样本列表
        """
        logger.info("Using rule-based parallel generation...")
        all_samples = []
        
        def generate_for_bank(bank):
            """为单个银行生成样本"""
            samples = self._generate_rule_based_samples(
                bank["bank_name"],
                bank["bank_code"],
                bank["id"],
                samples_per_bank
            )
            self.stats["processed_banks"] += 1
            return samples
        
        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_bank = {
                executor.submit(generate_for_bank, bank): bank 
                for bank in banks
            }
            
            # 收集结果
            for future in as_completed(future_to_bank):
                try:
                    samples = future.result()
                    all_samples.extend(samples)
                    
                    # 进度报告
                    progress = (self.stats["processed_banks"] / self.stats["total_banks"]) * 100
                    if self.stats["processed_banks"] % 10 == 0:  # 每10个银行报告一次
                        logger.info(f"Progress: {progress:.1f}% ({self.stats['processed_banks']}/{self.stats['total_banks']})")
                        
                except Exception as e:
                    bank = future_to_bank[future]
                    logger.error(f"Failed to generate samples for {bank['bank_name']}: {e}")
                    self.stats["failed_banks"] += 1
        
        return all_samples
    
    def _run_llm_parallel_generation(
        self, 
        banks: List[Dict[str, Any]], 
        samples_per_bank: int
    ) -> List[Dict[str, Any]]:
        """
        使用LLM并行生成
        
        Args:
            banks: 银行列表
            samples_per_bank: 每个银行生成的样本数量
        
        Returns:
            生成的训练样本列表
        """
        logger.info("Using LLM parallel generation...")
        print(f"🔧 DEBUG: Starting LLM parallel generation for {len(banks)} banks")
        
        # 将银行分配给不同的LLM
        banks_per_llm = len(banks) // len(self.llm_configs)
        llm_bank_assignments = []
        
        print(f"🔧 DEBUG: Available LLM configs: {len(self.llm_configs)}")
        for i, llm_config in enumerate(self.llm_configs):
            print(f"🔧 DEBUG: LLM {i}: {llm_config.name}")
            start_idx = i * banks_per_llm
            if i == len(self.llm_configs) - 1:  # 最后一个LLM处理剩余的
                end_idx = len(banks)
            else:
                end_idx = (i + 1) * banks_per_llm
            
            assigned_banks = banks[start_idx:end_idx]
            llm_bank_assignments.append((llm_config, assigned_banks))
            logger.info(f"{llm_config.name} assigned {len(assigned_banks)} banks")
            print(f"🔧 DEBUG: {llm_config.name} assigned {len(assigned_banks)} banks")
        
        # 启动数据库写入线程
        all_samples = []
        sample_queue = Queue()
        
        def collect_samples():
            """收集样本的线程"""
            print("🔧 DEBUG: Sample collector thread started")
            while True:
                try:
                    samples = sample_queue.get(timeout=10)
                    if samples is None:  # 结束信号
                        print("🔧 DEBUG: Sample collector received end signal")
                        break
                    all_samples.extend(samples)
                    print(f"🔧 DEBUG: Collected {len(samples)} samples, total: {len(all_samples)}")
                except Exception as e:
                    print(f"🔧 DEBUG: Sample collector timeout or error: {e}")
                    continue
        
        collector_thread = threading.Thread(target=collect_samples)
        collector_thread.daemon = True
        collector_thread.start()
        
        print(f"🔧 DEBUG: Starting ThreadPoolExecutor with {len(self.llm_configs)} workers")
        
        # 使用线程池并行处理不同LLM
        with ThreadPoolExecutor(max_workers=len(self.llm_configs)) as executor:
            futures = []
            
            for i, (llm_config, assigned_banks) in enumerate(llm_bank_assignments):
                print(f"🔧 DEBUG: Submitting task {i} for {llm_config.name} with {len(assigned_banks)} banks")
                future = executor.submit(
                    self._process_banks_with_llm,
                    assigned_banks,
                    llm_config,
                    samples_per_bank,
                    sample_queue
                )
                futures.append(future)
            
            print(f"🔧 DEBUG: Submitted {len(futures)} tasks, waiting for completion...")
            
            # 等待所有任务完成
            completed_count = 0
            for future in as_completed(futures):
                try:
                    result = future.result()
                    completed_count += 1
                    print(f"🔧 DEBUG: Task {completed_count}/{len(futures)} completed successfully")
                except Exception as e:
                    completed_count += 1
                    logger.error(f"LLM processing failed: {e}")
                    print(f"🔧 DEBUG: Task {completed_count}/{len(futures)} failed: {e}")
        
        print("🔧 DEBUG: All tasks completed, ending collector thread")
        
        # 结束收集线程
        sample_queue.put(None)
        collector_thread.join()
        
        print(f"🔧 DEBUG: LLM parallel generation completed, returning {len(all_samples)} samples")
        return all_samples
    
    def _process_banks_with_llm(
        self,
        banks: List[Dict[str, Any]],
        llm_config: LLMConfig,
        samples_per_bank: int,
        sample_queue: Queue
    ):
        """
        使用指定LLM处理银行列表
        
        Args:
            banks: 银行列表
            llm_config: LLM配置
            samples_per_bank: 每个银行生成的样本数量
            sample_queue: 样本收集队列
        """
        print(f"🔧 DEBUG: _process_banks_with_llm started for {llm_config.name} with {len(banks)} banks")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            print(f"🔧 DEBUG: Starting async processing for {llm_config.name}")
            loop.run_until_complete(
                self._process_banks_async(banks, llm_config, samples_per_bank, sample_queue)
            )
            print(f"🔧 DEBUG: Async processing completed for {llm_config.name}")
        except Exception as e:
            print(f"🔧 DEBUG: Error in _process_banks_with_llm for {llm_config.name}: {e}")
            logger.error(f"Error in _process_banks_with_llm for {llm_config.name}: {e}")
        finally:
            loop.close()
            print(f"🔧 DEBUG: Event loop closed for {llm_config.name}")
    
    async def _process_banks_async(
        self,
        banks: List[Dict[str, Any]],
        llm_config: LLMConfig,
        samples_per_bank: int,
        sample_queue: Queue
    ):
        """
        异步处理银行列表
        """
        print(f"🔧 DEBUG: _process_banks_async started for {llm_config.name} with {len(banks)} banks")
        
        async with aiohttp.ClientSession() as session:
            print(f"🔧 DEBUG: HTTP session created for {llm_config.name}")
            semaphore = asyncio.Semaphore(4)  # 每个LLM最多4个并发请求
            
            async def process_single_bank(bank):
                async with semaphore:
                    try:
                        print(f"🔧 DEBUG: Processing bank {bank['bank_name']} with {llm_config.name}")
                        samples = await self.generate_samples_async(
                            bank["bank_name"],
                            bank["bank_code"],
                            bank["id"],
                            llm_config,
                            session,
                            samples_per_bank
                        )
                        
                        sample_queue.put(samples)
                        self.stats["processed_banks"] += 1
                        print(f"🔧 DEBUG: Successfully processed {bank['bank_name']}, generated {len(samples)} samples")
                        
                        # 进度报告
                        progress = (self.stats["processed_banks"] / self.stats["total_banks"]) * 100
                        if self.stats["processed_banks"] % 5 == 0:
                            logger.info(f"LLM Progress: {progress:.1f}% ({self.stats['processed_banks']}/{self.stats['total_banks']})")
                        
                        # 请求间隔 - 优化大数据集处理
                        if len(banks) > 10000:  # 大数据集使用更短间隔
                            await asyncio.sleep(0.1)  # 100ms间隔，每秒10个请求
                        else:
                            await asyncio.sleep(60 / llm_config.max_requests_per_minute)
                        
                    except Exception as e:
                        print(f"🔧 DEBUG: Error processing {bank['bank_name']} with {llm_config.name}: {e}")
                        logger.error(f"Failed to process {bank['bank_name']} with {llm_config.name}: {e}")
                        # 使用规则生成作为备用
                        samples = self._generate_rule_based_samples(
                            bank["bank_name"],
                            bank["bank_code"],
                            bank["id"],
                            samples_per_bank
                        )
                        sample_queue.put(samples)
                        self.stats["failed_banks"] += 1
                        print(f"🔧 DEBUG: Used fallback rule generation for {bank['bank_name']}, generated {len(samples)} samples")
            
            print(f"🔧 DEBUG: Creating {len(banks)} tasks for {llm_config.name}")
            # 并发处理所有银行
            tasks = [process_single_bank(bank) for bank in banks]
            print(f"🔧 DEBUG: Starting asyncio.gather for {len(tasks)} tasks")
            await asyncio.gather(*tasks, return_exceptions=True)
            print(f"🔧 DEBUG: asyncio.gather completed for {llm_config.name}")
        """
        运行并行生成
        
        Args:
            limit: 限制处理的银行数量（用于测试）
        """
        logger.info("Starting parallel training data generation...")
        self.stats["start_time"] = time.time()
        
        # 获取所有银行数据
        db = self.SessionLocal()
        try:
            query = db.query(BankCode)
            if limit:
                query = query.limit(limit)
            
            banks = []
            for record in query.all():
                banks.append({
                    "id": record.id,
                    "bank_name": record.bank_name,
                    "bank_code": record.bank_code
                })
            
            self.stats["total_banks"] = len(banks)
            logger.info(f"Found {len(banks)} banks to process")
            
        finally:
            db.close()
        
        # 将银行分配给不同的LLM
        banks_per_llm = len(banks) // len(self.llm_configs)
        llm_bank_assignments = []
        
        for i, llm_config in enumerate(self.llm_configs):
            start_idx = i * banks_per_llm
            if i == len(self.llm_configs) - 1:  # 最后一个LLM处理剩余的
                end_idx = len(banks)
            else:
                end_idx = (i + 1) * banks_per_llm
            
            assigned_banks = banks[start_idx:end_idx]
            llm_bank_assignments.append((llm_config, assigned_banks))
            logger.info(f"{llm_config.name} assigned {len(assigned_banks)} banks")
        
        # 启动数据库写入线程
        db_writer_thread = threading.Thread(target=self._database_writer_worker)
        db_writer_thread.daemon = True
        db_writer_thread.start()
        
        # 启动进度监控线程
        monitor_thread = threading.Thread(target=self._progress_monitor)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # 使用线程池并行处理不同LLM
        with ThreadPoolExecutor(max_workers=len(self.llm_configs)) as executor:
            futures = []
            
            for llm_config, assigned_banks in llm_bank_assignments:
                future = executor.submit(
                    self._run_async_batch,
                    assigned_banks,
                    llm_config
                )
                futures.append(future)
            
            # 等待所有任务完成
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"LLM processing failed: {e}")
        
        # 等待数据库写入完成
        self.result_queue.put(None)  # 结束信号
        db_writer_thread.join()
        
        # 输出最终统计
        self._print_final_stats()
    
    def _run_async_batch(self, banks: List[Dict[str, Any]], llm_config: LLMConfig):
        """在线程中运行异步批处理"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.process_bank_batch_async(banks, llm_config))
        finally:
            loop.close()
    
    def _database_writer_worker(self):
        """数据库写入工作线程"""
        batch = []
        
        while True:
            try:
                # 从队列获取结果
                samples = self.result_queue.get(timeout=10)
                
                if samples is None:  # 结束信号
                    # 保存剩余的批次
                    if batch:
                        self._save_samples_batch(batch)
                    break
                
                batch.extend(samples)
                
                # 批量保存
                if len(batch) >= self.batch_size:
                    self._save_samples_batch(batch)
                    batch = []
                
            except Exception as e:
                logger.error(f"Database writer error: {e}")
                continue
    
    def _progress_monitor(self):
        """进度监控线程"""
        while True:
            time.sleep(30)  # 每30秒报告一次进度
            
            if self.stats["total_banks"] == 0:
                continue
            
            progress = (self.stats["processed_banks"] / self.stats["total_banks"]) * 100
            elapsed = time.time() - self.stats["start_time"]
            
            if self.stats["processed_banks"] > 0:
                avg_time_per_bank = elapsed / self.stats["processed_banks"]
                remaining_banks = self.stats["total_banks"] - self.stats["processed_banks"]
                eta = remaining_banks * avg_time_per_bank
                
                logger.info(
                    f"Progress: {progress:.1f}% "
                    f"({self.stats['processed_banks']}/{self.stats['total_banks']} banks) "
                    f"Generated: {self.stats['generated_samples']} samples "
                    f"Failed: {self.stats['failed_banks']} "
                    f"ETA: {eta/60:.1f} minutes"
                )
                
                # 调用进度回调
                if self.progress_callback:
                    try:
                        self.progress_callback(self.stats.copy())
                    except Exception as e:
                        logger.error(f"Progress callback error: {e}")
            
            # 如果完成了，退出监控
            if self.stats["processed_banks"] + self.stats["failed_banks"] >= self.stats["total_banks"]:
                break
    
    def _print_final_stats(self):
        """打印最终统计信息"""
        elapsed = time.time() - self.stats["start_time"]
        
        logger.info("=" * 60)
        logger.info("PARALLEL TRAINING DATA GENERATION COMPLETED")
        logger.info("=" * 60)
        logger.info(f"Total banks: {self.stats['total_banks']:,}")
        logger.info(f"Processed banks: {self.stats['processed_banks']:,}")
        logger.info(f"Failed banks: {self.stats['failed_banks']:,}")
        logger.info(f"Generated samples: {self.stats['generated_samples']:,}")
        logger.info(f"Total time: {elapsed/60:.1f} minutes")
        logger.info(f"Average time per bank: {elapsed/self.stats['total_banks']:.2f} seconds")
        logger.info(f"Samples per second: {self.stats['generated_samples']/elapsed:.2f}")
        logger.info("=" * 60)


    def run_parallel_generation(self, limit: Optional[int] = None):
        """
        运行并行生成（原有方法，保持兼容性）
        
        Args:
            limit: 限制处理的银行数量（用于测试）
        """
        logger.info("Starting parallel training data generation...")
        self.stats["start_time"] = time.time()
        
        # 获取所有银行数据
        db = self.SessionLocal()
        try:
            query = db.query(BankCode)
            if limit:
                query = query.limit(limit)
            
            banks = []
            for record in query.all():
                banks.append({
                    "id": record.id,
                    "bank_name": record.bank_name,
                    "bank_code": record.bank_code
                })
            
            self.stats["total_banks"] = len(banks)
            logger.info(f"Found {len(banks)} banks to process")
            
        finally:
            db.close()
        
        if not banks:
            logger.warning("No banks found for processing")
            return []
        
        # 使用规则生成（快速模式）
        all_samples = self._run_rule_based_generation(banks, 7)
        
        # 批量保存到数据库
        self._save_samples_batch(all_samples)
        
        # 输出最终统计
        self._print_final_stats()
        
        return all_samples


def create_training_dataset(dataset_name: str = "大规模银行训练数据集") -> int:
    """
    创建训练数据集
    
    Args:
        dataset_name: 数据集名称
        
    Returns:
        数据集ID
    """
    db = next(get_db())
    try:
        dataset = Dataset(
            filename=f"{dataset_name}.json",
            file_path=f"generated/{dataset_name}_{int(datetime.utcnow().timestamp())}.json",
            file_size=0,  # 将在生成完成后更新
            total_records=0,  # 将在生成完成后更新
            valid_records=0,  # 将在生成完成后更新
            invalid_records=0,
            status='uploaded',
            uploaded_by=None  # 系统生成
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        
        logger.info(f"Created dataset: {dataset_name} (ID: {dataset.id})")
        return dataset.id
        
    finally:
        db.close()


# 使用示例
if __name__ == "__main__":
    # 创建数据集
    dataset_id = create_training_dataset()
    
    # 创建生成器
    generator = ParallelTrainingGenerator(dataset_id)
    
    # 运行生成（测试时可以设置limit）
    generator.run_parallel_generation(limit=1000)  # 测试1000条
    # generator.run_parallel_generation()  # 生产环境处理全部数据