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
    
    def __init__(self, dataset_id: int):
        """
        初始化生成器
        
        Args:
            dataset_id: 数据集ID
        """
        self.dataset_id = dataset_id
        
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
        
        # 线程池配置
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
    
    async def generate_samples_async(
        self, 
        bank_name: str, 
        bank_code: str, 
        bank_id: int,
        llm_config: LLMConfig,
        session: aiohttp.ClientSession
    ) -> List[Dict[str, Any]]:
        """
        异步生成单个银行的训练样本
        
        Args:
            bank_name: 银行名称
            bank_code: 联行号
            bank_id: 银行ID
            llm_config: LLM配置
            session: HTTP会话
            
        Returns:
            训练样本列表
        """
        try:
            # 构建提示词
            prompt = self._build_prompt(bank_name, bank_code)
            
            # 调用LLM API
            response = await self._call_llm_api(prompt, llm_config, session)
            
            # 解析响应
            samples = self._parse_llm_response(response, bank_name, bank_code, bank_id)
            
            logger.debug(f"Generated {len(samples)} samples for {bank_name} using {llm_config.name}")
            return samples
            
        except Exception as e:
            logger.error(f"Failed to generate samples for {bank_name} using {llm_config.name}: {e}")
            # 返回规则生成的样本作为备用
            return self._generate_rule_based_samples(bank_name, bank_code, bank_id)
    
    def _build_prompt(self, bank_name: str, bank_code: str) -> str:
        """构建LLM提示词"""
        return f"""你是一个银行业务专家。请为以下银行生成7种不同的自然语言查询方式。

银行信息：
- 完整名称：{bank_name}
- 联行号：{bank_code}

要求：
1. 生成7种用户可能的问法
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

示例：
对于"中国工商银行股份有限公司北京市分行"，可以生成：
- "中国工商银行股份有限公司北京市分行"
- "工商银行北京市分行"
- "工行北京分行"
- "北京工商银行"
- "北京工行"
- "工商银行北京"
- "工行北京"

现在请为上述银行生成7种问法："""
    
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
        
        async with session.post(
            f"{llm_config.base_url}/text-generation/generation",
            headers=headers,
            json=data,
            timeout=30
        ) as response:
            result = await response.json()
            return result["output"]["text"]
    
    async def _call_deepseek_api(
        self, 
        prompt: str, 
        llm_config: LLMConfig, 
        session: aiohttp.ClientSession
    ) -> str:
        """调用DeepSeek API"""
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
        
        async with session.post(
            f"{llm_config.base_url}/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        ) as response:
            result = await response.json()
            return result["choices"][0]["message"]["content"]
    
    def _parse_llm_response(
        self, 
        response: str, 
        bank_name: str, 
        bank_code: str, 
        bank_id: int
    ) -> List[Dict[str, Any]]:
        """
        解析LLM响应
        
        Args:
            response: LLM响应文本
            bank_name: 银行名称
            bank_code: 联行号
            bank_id: 银行ID
            
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
                for i, question in enumerate(questions[:7]):  # 限制7个
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
                return self._generate_rule_based_samples(bank_name, bank_code, bank_id)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            return self._generate_rule_based_samples(bank_name, bank_code, bank_id)
    
    def _generate_rule_based_samples(
        self, 
        bank_name: str, 
        bank_code: str, 
        bank_id: int
    ) -> List[Dict[str, Any]]:
        """
        基于规则生成样本（备用方案）
        
        Args:
            bank_name: 银行名称
            bank_code: 联行号
            bank_id: 银行ID
            
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
        if short_name != bank_name:
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
        
        # 3-7. 其他变体
        variations = [
            f"{bank_name}的联行号",
            f"{short_name}联行号",
            f"{bank_name}代码",
            f"{short_name}的代码是多少",
            f"查询{bank_name}联行号"
        ]
        
        for variation in variations:
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
        
        return samples[:7]  # 限制7个
    
    def _save_samples_batch(self, samples: List[Dict[str, Any]]):
        """
        批量保存样本到数据库
        
        Args:
            samples: 样本列表
        """
        if not samples:
            return
        
        db = self.SessionLocal()
        try:
            # 批量插入
            qa_pairs = [QAPair(**sample) for sample in samples]
            db.bulk_save_objects(qa_pairs)
            db.commit()
            
            self.stats["generated_samples"] += len(samples)
            logger.info(f"Saved {len(samples)} samples to database")
            
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
    
    def run_parallel_generation(self, limit: Optional[int] = None):
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
            name=dataset_name,
            description="使用多LLM并行生成的大规模银行训练数据集",
            created_at=datetime.utcnow()
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