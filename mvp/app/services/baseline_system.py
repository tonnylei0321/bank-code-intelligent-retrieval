"""
Elasticsearch Baseline System - Elasticsearch基准系统服务

本服务实现基于Elasticsearch的全文检索方案，作为与小模型方案对比的基准系统。

主要功能：
    - 索引管理：创建和配置Elasticsearch索引
    - 数据索引：批量索引银行联行号数据
    - 全文检索：支持中文分词的全文搜索
    - 查询接口：提供与QueryService一致的查询接口
    - 统计信息：获取索引统计和状态信息

技术特点：
    - 使用ik_max_word中文分词器（如果可用）
    - 支持精确匹配和模糊匹配
    - 基于Elasticsearch的相关性评分
    - 自动降级到标准分词器

使用示例：
    >>> from app.services.baseline_system import BaselineSystem
    >>> baseline = BaselineSystem(es_host="localhost", es_port=9200)
    >>> 
    >>> # 检查可用性
    >>> if baseline.is_available():
    ...     # 创建索引
    ...     baseline.create_index()
    ...     
    ...     # 索引数据
    ...     result = baseline.index_bank_codes(bank_codes)
    ...     
    ...     # 查询
    ...     response = baseline.query("工商银行的联行号")
    ...     print(response["answer"])

对比优势：
    - 无需训练：直接索引数据即可使用
    - 响应快速：基于倒排索引的快速检索
    - 资源占用低：不需要GPU
    - 易于扩展：支持大规模数据

对比劣势：
    - 理解能力有限：基于关键词匹配，无法理解语义
    - 泛化能力弱：对新的查询方式适应性差
    - 需要精确关键词：对错别字和简称支持有限
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from elasticsearch import Elasticsearch, exceptions as es_exceptions

from app.models.bank_code import BankCode
from app.schemas.bank_code import BankCodeResponse

logger = logging.getLogger(__name__)


class BaselineSystem:
    """
    Elasticsearch基准检索系统
    
    使用Elasticsearch实现传统的全文检索方案，作为与小模型方案对比的基准。
    
    核心功能：
        1. 连接管理：
           - 初始化Elasticsearch客户端
           - 测试连接可用性
           - 自动重试机制
        
        2. 索引管理：
           - 创建索引并配置中文分词器
           - 支持ik_max_word分词器
           - 自动降级到标准分词器
           - 删除索引
        
        3. 数据索引：
           - 批量索引银行联行号数据
           - 支持增量索引
           - 错误处理和统计
        
        4. 全文检索：
           - 多字段搜索（银行名称、联行号）
           - 权重调整（精确匹配权重更高）
           - 通配符搜索支持
           - 数据集过滤
        
        5. 查询接口：
           - 提供与QueryService一致的接口
           - 自动构造答案文本
           - 计算置信度分数
           - 记录响应时间
        
        6. 统计信息：
           - 索引文档数量
           - 索引配置信息
           - 可用性状态
    
    属性：
        es_host (str): Elasticsearch主机地址
        es_port (int): Elasticsearch端口
        index_name (str): 索引名称
        client: Elasticsearch客户端对象
    
    索引配置：
        - 分片数：1
        - 副本数：0
        - 分词器：ik_max_word（中文）或standard（英文）
        - 字段映射：
          - bank_name: text（支持全文搜索）+ keyword（支持精确匹配）
          - bank_code: keyword（精确匹配）
          - clearing_code: keyword（精确匹配）
          - dataset_id: integer（过滤）
    """
    
    def __init__(self, es_host: str = "localhost", es_port: int = 9200):
        """
        初始化Elasticsearch客户端
        
        Args:
            es_host: Elasticsearch主机地址
            es_port: Elasticsearch端口
        """
        self.es_host = es_host
        self.es_port = es_port
        self.index_name = "bank_codes"
        
        try:
            self.client = Elasticsearch(
                [f"http://{es_host}:{es_port}"],
                request_timeout=30,
                max_retries=3,
                retry_on_timeout=True
            )
            
            # 测试连接
            if self.client.ping():
                logger.info(f"Successfully connected to Elasticsearch at {es_host}:{es_port}")
            else:
                logger.warning(f"Failed to ping Elasticsearch at {es_host}:{es_port}")
                
        except Exception as e:
            logger.error(f"Failed to initialize Elasticsearch client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """
        检查Elasticsearch是否可用
        
        Returns:
            bool: 是否可用
        """
        if self.client is None:
            return False
        
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Error checking Elasticsearch availability: {e}")
            return False
    
    def create_index(self) -> bool:
        """
        创建索引并配置中文分词器
        
        使用ik_max_word分词器进行中文分词，提高检索准确率。
        
        Returns:
            bool: 是否创建成功
        """
        if not self.is_available():
            logger.error("Elasticsearch is not available")
            return False
        
        # 索引配置
        index_config = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "bank_analyzer": {
                            "type": "custom",
                            "tokenizer": "ik_max_word",
                            "filter": ["lowercase"]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "bank_name": {
                        "type": "text",
                        "analyzer": "bank_analyzer",
                        "fields": {
                            "keyword": {
                                "type": "keyword"
                            }
                        }
                    },
                    "bank_code": {
                        "type": "keyword"
                    },
                    "clearing_code": {
                        "type": "keyword"
                    },
                    "dataset_id": {
                        "type": "integer"
                    },
                    "indexed_at": {
                        "type": "date"
                    }
                }
            }
        }
        
        try:
            # 检查索引是否已存在
            if self.client.indices.exists(index=self.index_name):
                logger.info(f"Index {self.index_name} already exists")
                return True
            
            # 创建索引
            self.client.indices.create(index=self.index_name, body=index_config)
            logger.info(f"Successfully created index {self.index_name}")
            return True
            
        except es_exceptions.RequestError as e:
            # 如果是因为ik分词器不存在，使用标准分词器
            if "unknown_tokenizer" in str(e).lower() or "ik_max_word" in str(e).lower():
                logger.warning("ik_max_word tokenizer not available, using standard tokenizer")
                
                # 使用标准分词器的配置
                index_config["settings"]["analysis"]["analyzer"]["bank_analyzer"] = {
                    "type": "standard"
                }
                
                try:
                    self.client.indices.create(index=self.index_name, body=index_config)
                    logger.info(f"Successfully created index {self.index_name} with standard tokenizer")
                    return True
                except Exception as e2:
                    logger.error(f"Failed to create index with standard tokenizer: {e2}")
                    return False
            else:
                logger.error(f"Failed to create index: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            return False
    
    def delete_index(self) -> bool:
        """
        删除索引
        
        Returns:
            bool: 是否删除成功
        """
        if not self.is_available():
            logger.error("Elasticsearch is not available")
            return False
        
        try:
            if self.client.indices.exists(index=self.index_name):
                self.client.indices.delete(index=self.index_name)
                logger.info(f"Successfully deleted index {self.index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete index: {e}")
            return False
    
    def index_bank_codes(self, bank_codes: List[BankCode]) -> Dict[str, Any]:
        """
        批量索引联行号数据到Elasticsearch
        
        Args:
            bank_codes: 联行号记录列表
            
        Returns:
            Dict: 索引结果统计
        """
        if not self.is_available():
            logger.error("Elasticsearch is not available")
            return {
                "success": False,
                "total": 0,
                "indexed": 0,
                "failed": 0,
                "error": "Elasticsearch is not available"
            }
        
        # 确保索引存在
        if not self.client.indices.exists(index=self.index_name):
            if not self.create_index():
                return {
                    "success": False,
                    "total": 0,
                    "indexed": 0,
                    "failed": 0,
                    "error": "Failed to create index"
                }
        
        total = len(bank_codes)
        indexed = 0
        failed = 0
        errors = []
        
        # 批量索引
        from elasticsearch.helpers import bulk
        
        actions = []
        for bank_code in bank_codes:
            action = {
                "_index": self.index_name,
                "_id": f"{bank_code.dataset_id}_{bank_code.id}",
                "_source": {
                    "bank_name": bank_code.bank_name,
                    "bank_code": bank_code.bank_code,
                    "clearing_code": bank_code.clearing_code,
                    "dataset_id": bank_code.dataset_id,
                    "indexed_at": datetime.utcnow().isoformat()
                }
            }
            actions.append(action)
        
        try:
            success_count, failed_items = bulk(
                self.client,
                actions,
                raise_on_error=False,
                raise_on_exception=False
            )
            
            indexed = success_count
            failed = len(failed_items) if failed_items else 0
            
            if failed > 0:
                errors = [str(item) for item in failed_items[:5]]  # 只记录前5个错误
                logger.warning(f"Failed to index {failed} documents")
            
            logger.info(f"Indexed {indexed}/{total} bank codes to Elasticsearch")
            
            # 刷新索引以确保数据可搜索
            self.client.indices.refresh(index=self.index_name)
            
            return {
                "success": True,
                "total": total,
                "indexed": indexed,
                "failed": failed,
                "errors": errors if errors else None
            }
            
        except Exception as e:
            logger.error(f"Failed to bulk index documents: {e}")
            return {
                "success": False,
                "total": total,
                "indexed": 0,
                "failed": total,
                "error": str(e)
            }
    
    def search(
        self,
        query: str,
        top_k: int = 3,
        dataset_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索联行号信息
        
        Args:
            query: 查询字符串
            top_k: 返回结果数量
            dataset_id: 限定数据集ID（可选）
            
        Returns:
            List[Dict]: 搜索结果列表
        """
        if not self.is_available():
            logger.error("Elasticsearch is not available")
            return []
        
        # 构建查询
        search_body = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "match": {
                                "bank_name": {
                                    "query": query,
                                    "boost": 2.0  # 银行名称权重更高
                                }
                            }
                        },
                        {
                            "term": {
                                "bank_code": {
                                    "value": query,
                                    "boost": 3.0  # 精确匹配联行号权重最高
                                }
                            }
                        },
                        {
                            "wildcard": {
                                "bank_name.keyword": {
                                    "value": f"*{query}*",
                                    "boost": 1.5
                                }
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            },
            "size": top_k
        }
        
        # 如果指定了数据集ID，添加过滤条件
        if dataset_id is not None:
            search_body["query"]["bool"]["filter"] = [
                {"term": {"dataset_id": dataset_id}}
            ]
        
        try:
            response = self.client.search(index=self.index_name, body=search_body)
            
            results = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                results.append({
                    "bank_name": source["bank_name"],
                    "bank_code": source["bank_code"],
                    "clearing_code": source["clearing_code"],
                    "score": hit["_score"],
                    "dataset_id": source.get("dataset_id")
                })
            
            logger.info(f"Found {len(results)} results for query: {query}")
            return results
            
        except es_exceptions.NotFoundError:
            logger.warning(f"Index {self.index_name} not found")
            return []
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def query(
        self,
        question: str,
        dataset_id: Optional[int] = None,
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        查询接口（与QueryService接口一致）
        
        Args:
            question: 查询问题
            dataset_id: 限定数据集ID（可选）
            top_k: 返回结果数量
            
        Returns:
            Dict: 查询响应，格式与QueryService一致
        """
        import time
        start_time = time.time()
        
        # 搜索
        results = self.search(question, top_k=top_k, dataset_id=dataset_id)
        
        response_time = (time.time() - start_time) * 1000  # 转换为毫秒
        
        # 构造响应
        if not results:
            return {
                "question": question,
                "answer": "抱歉，未找到相关的联行号信息",
                "confidence": 0.0,
                "response_time": response_time,
                "matched_records": [],
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # 构造答案
        top_result = results[0]
        if len(results) == 1:
            answer = f"{top_result['bank_name']}的联行号是{top_result['bank_code']}"
        else:
            answer = f"找到{len(results)}个相关结果：\n"
            for i, result in enumerate(results, 1):
                answer += f"{i}. {result['bank_name']}的联行号是{result['bank_code']}\n"
        
        # 计算置信度（基于Elasticsearch的score）
        max_score = results[0]["score"] if results else 0
        confidence = min(max_score / 10.0, 1.0)  # 归一化到0-1
        
        return {
            "question": question,
            "answer": answer.strip(),
            "confidence": confidence,
            "response_time": response_time,
            "matched_records": [
                {
                    "bank_name": r["bank_name"],
                    "bank_code": r["bank_code"],
                    "clearing_code": r["clearing_code"],
                    "score": r["score"]
                }
                for r in results
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取索引统计信息
        
        Returns:
            Dict: 统计信息
        """
        if not self.is_available():
            return {
                "available": False,
                "error": "Elasticsearch is not available"
            }
        
        try:
            if not self.client.indices.exists(index=self.index_name):
                return {
                    "available": True,
                    "index_exists": False,
                    "document_count": 0
                }
            
            # 获取文档数量
            count = self.client.count(index=self.index_name)
            
            # 获取索引信息
            index_info = self.client.indices.get(index=self.index_name)
            
            return {
                "available": True,
                "index_exists": True,
                "document_count": count["count"],
                "index_name": self.index_name,
                "settings": index_info[self.index_name]["settings"]
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "available": True,
                "error": str(e)
            }
