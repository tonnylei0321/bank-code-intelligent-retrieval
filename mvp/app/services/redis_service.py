"""
Redis服务 - 银行代码数据缓存和快速检索

本服务实现了基于Redis的银行代码数据管理，提供：
1. 银行数据的Redis缓存管理
2. 快速的键值对检索
3. 数据同步和更新
4. 批量数据操作

主要功能：
    - 将银行数据加载到Redis
    - 支持多种检索模式（银行名称、联行号、关键词）
    - 提供数据统计和管理接口
    - 支持数据的增量更新

技术架构：
    - 缓存系统：Redis
    - 数据结构：Hash、Set、String
    - 检索策略：精确匹配 + 模糊匹配
    - 存储格式：结构化JSON数据

使用示例：
    >>> redis_service = RedisService()
    >>> await redis_service.initialize()
    >>> 
    >>> # 加载银行数据到Redis
    >>> await redis_service.load_bank_data_to_redis()
    >>> 
    >>> # 检索银行信息
    >>> results = await redis_service.search_banks("工商银行")
    >>> 
    >>> # 获取统计信息
    >>> stats = await redis_service.get_redis_stats()
"""

import json
import asyncio
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta

import aioredis
from loguru import logger
from sqlalchemy.orm import Session

from app.models.bank_code import BankCode


class RedisService:
    """
    Redis服务 - 银行代码数据缓存和管理
    
    本类实现了完整的Redis缓存系统，包括：
    1. Redis连接管理
    2. 银行数据的缓存存储
    3. 多种检索策略
    4. 数据同步和更新
    5. 统计信息管理
    
    属性：
        redis_client: Redis异步客户端
        db: 数据库会话
        config: Redis配置参数
        key_prefix: Redis键前缀
    """
    
    def __init__(
        self,
        db: Session,
        redis_url: str = "redis://localhost:6379/0",
        key_prefix: str = "bank_code:",
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化Redis服务
        
        Args:
            db: 数据库会话
            redis_url: Redis连接URL
            key_prefix: Redis键前缀
            config: Redis配置参数
        """
        self.db = db
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.redis_client = None
        
        # 默认配置
        self.config = {
            "connection_timeout": 10,
            "socket_timeout": 5,
            "retry_on_timeout": True,
            "max_connections": 20,
            "decode_responses": True,
            "health_check_interval": 30,
            "default_ttl": 86400,  # 24小时
            "batch_size": 1000,
            "enable_compression": False
        }
        
        if config:
            self.config.update(config)
    
    async def initialize(self) -> bool:
        """
        初始化Redis连接
        
        Returns:
            是否成功初始化
        """
        try:
            logger.info(f"Initializing Redis connection to {self.redis_url}")
            
            self.redis_client = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=self.config["socket_timeout"],
                socket_connect_timeout=self.config["connection_timeout"],
                retry_on_timeout=self.config["retry_on_timeout"],
                max_connections=self.config["max_connections"],
                health_check_interval=self.config["health_check_interval"]
            )
            
            # 测试连接
            await self.redis_client.ping()
            logger.info("Redis connection established successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            return False
    
    async def close(self):
        """关闭Redis连接"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")
    
    def _get_bank_key(self, bank_id: int) -> str:
        """获取银行数据的Redis键"""
        return f"{self.key_prefix}bank:{bank_id}"
    
    def _get_name_key(self, bank_name: str) -> str:
        """获取银行名称索引的Redis键"""
        return f"{self.key_prefix}name:{bank_name.lower()}"
    
    def _get_code_key(self, bank_code: str) -> str:
        """获取联行号索引的Redis键"""
        return f"{self.key_prefix}code:{bank_code}"
    
    def _get_keyword_key(self, keyword: str) -> str:
        """获取关键词索引的Redis键"""
        return f"{self.key_prefix}keyword:{keyword.lower()}"
    
    def _get_stats_key(self) -> str:
        """获取统计信息的Redis键"""
        return f"{self.key_prefix}stats"
    
    def _extract_keywords(self, bank_name: str) -> List[str]:
        """
        从银行名称中提取关键词
        
        Args:
            bank_name: 银行名称
        
        Returns:
            关键词列表
        """
        keywords = []
        
        # 银行简称映射
        bank_mappings = {
            "中国工商银行": ["工商银行", "工行", "ICBC"],
            "中国农业银行": ["农业银行", "农行", "ABC"],
            "中国银行": ["中行", "BOC"],
            "中国建设银行": ["建设银行", "建行", "CCB"],
            "交通银行": ["交行", "BOCOM"],
            "招商银行": ["招行", "CMB"],
            "浦发银行": ["上海浦东发展银行", "SPDB"],
            "中信银行": ["中信", "CITIC"],
            "光大银行": ["中国光大银行", "CEB"],
            "华夏银行": ["华夏", "HXB"],
            "民生银行": ["中国民生银行", "CMBC"],
            "广发银行": ["广发", "CGB"],
            "平安银行": ["平安", "PAB"],
            "兴业银行": ["兴业", "CIB"],
            "邮储银行": ["中国邮政储蓄银行", "邮政储蓄银行", "PSBC"]
        }
        
        # 添加完整银行名称
        keywords.append(bank_name)
        
        # 查找匹配的简称
        for full_name, aliases in bank_mappings.items():
            if full_name in bank_name or bank_name in full_name:
                keywords.extend(aliases)
                break
        
        # 提取地理位置
        locations = [
            "北京", "上海", "天津", "重庆", "广州", "深圳", "厦门", "青岛", 
            "大连", "宁波", "苏州", "杭州", "南京", "武汉", "成都", "西安"
        ]
        
        for location in locations:
            if location in bank_name:
                keywords.append(location)
        
        # 提取支行类型
        branch_types = ["支行", "分行", "营业部", "营业厅", "分理处", "储蓄所"]
        for branch_type in branch_types:
            if branch_type in bank_name:
                keywords.append(branch_type)
        
        # 去重
        return list(set(keywords))
    
    async def load_bank_data_to_redis(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        将银行数据加载到Redis
        
        Args:
            force_reload: 是否强制重新加载
        
        Returns:
            加载结果统计
        """
        try:
            logger.info("Starting to load bank data to Redis...")
            
            if not self.redis_client:
                raise Exception("Redis client not initialized")
            
            # 检查是否需要重新加载
            if not force_reload:
                existing_count = await self.redis_client.get(f"{self.key_prefix}count")
                if existing_count:
                    logger.info(f"Redis already contains {existing_count} bank records")
                    db_count = self.db.query(BankCode).filter(BankCode.is_valid == True).count()
                    if int(existing_count) == db_count:
                        logger.info("Redis data is up to date")
                        return {
                            "status": "up_to_date",
                            "redis_count": int(existing_count),
                            "db_count": db_count
                        }
            
            # 获取所有有效银行记录
            bank_records = self.db.query(BankCode).filter(BankCode.is_valid == True).all()
            logger.info(f"Found {len(bank_records)} valid bank records in database")
            
            if not bank_records:
                logger.warning("No bank records found in database")
                return {"status": "no_data", "count": 0}
            
            # 清空现有数据（如果强制重新加载）
            if force_reload:
                pattern = f"{self.key_prefix}*"
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
                    logger.info(f"Cleared {len(keys)} existing Redis keys")
            
            # 批量加载数据
            batch_size = self.config["batch_size"]
            total_batches = (len(bank_records) + batch_size - 1) // batch_size
            loaded_count = 0
            
            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, len(bank_records))
                batch_records = bank_records[start_idx:end_idx]
                
                logger.info(f"Processing batch {batch_idx + 1}/{total_batches} ({len(batch_records)} records)")
                
                # 使用Redis pipeline提高性能
                pipe = self.redis_client.pipeline()
                
                for record in batch_records:
                    # 处理created_at字段
                    created_at_str = ""
                    if record.created_at:
                        if hasattr(record.created_at, 'isoformat'):
                            created_at_str = record.created_at.isoformat()
                        else:
                            created_at_str = str(record.created_at)
                    
                    # 银行基本信息
                    bank_data = {
                        "id": record.id,
                        "bank_name": record.bank_name,
                        "bank_code": record.bank_code,
                        "clearing_code": record.clearing_code or "",
                        "dataset_id": record.dataset_id or 0,
                        "created_at": created_at_str,
                        "updated_at": datetime.now().isoformat()
                    }
                    
                    # 存储银行数据
                    bank_key = self._get_bank_key(record.id)
                    pipe.hset(bank_key, mapping=bank_data)
                    
                    # 创建名称索引
                    name_key = self._get_name_key(record.bank_name)
                    pipe.set(name_key, record.id)
                    
                    # 创建联行号索引
                    code_key = self._get_code_key(record.bank_code)
                    pipe.set(code_key, record.id)
                    
                    # 创建关键词索引
                    keywords = self._extract_keywords(record.bank_name)
                    for keyword in keywords:
                        keyword_key = self._get_keyword_key(keyword)
                        pipe.sadd(keyword_key, record.id)
                    
                    loaded_count += 1
                
                # 执行批量操作
                await pipe.execute()
                logger.info(f"Loaded batch {batch_idx + 1}/{total_batches} to Redis")
            
            # 更新统计信息
            stats = {
                "total_count": loaded_count,
                "last_updated": datetime.now().isoformat(),
                "version": "1.0"
            }
            
            await self.redis_client.set(f"{self.key_prefix}count", loaded_count)
            await self.redis_client.hset(self._get_stats_key(), mapping=stats)
            
            logger.info(f"Successfully loaded {loaded_count} bank records to Redis")
            
            return {
                "status": "success",
                "loaded_count": loaded_count,
                "total_batches": total_batches
            }
            
        except Exception as e:
            logger.error(f"Failed to load bank data to Redis: {e}")
            return {"status": "error", "error": str(e)}
    
    async def search_banks(
        self,
        query: str,
        search_type: str = "auto",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        在Redis中搜索银行信息
        
        Args:
            query: 搜索查询
            search_type: 搜索类型 (auto, name, code, keyword)
            limit: 返回结果数量限制
        
        Returns:
            匹配的银行记录列表
        """
        try:
            if not self.redis_client:
                raise Exception("Redis client not initialized")
            
            logger.info(f"Searching banks in Redis: query='{query}', type='{search_type}'")
            
            bank_ids = set()
            
            if search_type == "auto":
                # 自动检测搜索类型
                if len(query) == 12 and query.isdigit():
                    search_type = "code"
                elif any(keyword in query for keyword in ["银行", "行", "支行", "分行"]):
                    search_type = "name"
                else:
                    search_type = "keyword"
            
            if search_type == "name":
                # 精确名称匹配
                name_key = self._get_name_key(query)
                bank_id = await self.redis_client.get(name_key)
                if bank_id:
                    bank_ids.add(int(bank_id))
                
                # 模糊名称匹配
                pattern = f"{self.key_prefix}name:*{query.lower()}*"
                keys = await self.redis_client.keys(pattern)
                for key in keys[:limit]:
                    bank_id = await self.redis_client.get(key)
                    if bank_id:
                        bank_ids.add(int(bank_id))
            
            elif search_type == "code":
                # 联行号匹配
                code_key = self._get_code_key(query)
                bank_id = await self.redis_client.get(code_key)
                if bank_id:
                    bank_ids.add(int(bank_id))
            
            elif search_type == "keyword":
                # 关键词匹配
                keyword_key = self._get_keyword_key(query)
                keyword_bank_ids = await self.redis_client.smembers(keyword_key)
                for bank_id in keyword_bank_ids:
                    bank_ids.add(int(bank_id))
                
                # 模糊关键词匹配
                pattern = f"{self.key_prefix}keyword:*{query.lower()}*"
                keys = await self.redis_client.keys(pattern)
                for key in keys[:limit * 2]:
                    keyword_bank_ids = await self.redis_client.smembers(key)
                    for bank_id in keyword_bank_ids:
                        bank_ids.add(int(bank_id))
            
            # 获取银行详细信息
            results = []
            for bank_id in list(bank_ids)[:limit]:
                bank_key = self._get_bank_key(bank_id)
                bank_data = await self.redis_client.hgetall(bank_key)
                
                if bank_data:
                    # 计算匹配分数
                    score = self._calculate_match_score(query, bank_data)
                    bank_data["match_score"] = score
                    bank_data["search_type"] = search_type
                    results.append(bank_data)
            
            # 按匹配分数排序
            results.sort(key=lambda x: x["match_score"], reverse=True)
            
            logger.info(f"Found {len(results)} matching banks in Redis")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search banks in Redis: {e}")
            return []
    
    def _calculate_match_score(self, query: str, bank_data: Dict[str, Any]) -> float:
        """
        计算匹配分数
        
        Args:
            query: 搜索查询
            bank_data: 银行数据
        
        Returns:
            匹配分数 (0-1)
        """
        score = 0.0
        query_lower = query.lower()
        bank_name_lower = bank_data.get("bank_name", "").lower()
        bank_code = bank_data.get("bank_code", "")
        
        # 完全匹配
        if query_lower == bank_name_lower:
            score += 1.0
        elif query == bank_code:
            score += 1.0
        # 包含匹配
        elif query_lower in bank_name_lower:
            score += 0.8
        elif bank_name_lower in query_lower:
            score += 0.6
        # 字符重叠
        else:
            common_chars = set(query_lower) & set(bank_name_lower)
            if len(query_lower) > 0:
                overlap_ratio = len(common_chars) / len(query_lower)
                score += overlap_ratio * 0.4
        
        return min(score, 1.0)
    
    async def get_bank_by_id(self, bank_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取银行信息
        
        Args:
            bank_id: 银行ID
        
        Returns:
            银行信息或None
        """
        try:
            if not self.redis_client:
                return None
            
            bank_key = self._get_bank_key(bank_id)
            bank_data = await self.redis_client.hgetall(bank_key)
            
            return bank_data if bank_data else None
            
        except Exception as e:
            logger.error(f"Failed to get bank by ID {bank_id}: {e}")
            return None
    
    async def get_bank_by_code(self, bank_code: str) -> Optional[Dict[str, Any]]:
        """
        根据联行号获取银行信息
        
        Args:
            bank_code: 联行号
        
        Returns:
            银行信息或None
        """
        try:
            if not self.redis_client:
                return None
            
            code_key = self._get_code_key(bank_code)
            bank_id = await self.redis_client.get(code_key)
            
            if bank_id:
                return await self.get_bank_by_id(int(bank_id))
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get bank by code {bank_code}: {e}")
            return None
    
    async def get_redis_stats(self) -> Dict[str, Any]:
        """
        获取Redis统计信息
        
        Returns:
            统计信息字典
        """
        try:
            if not self.redis_client:
                return {"error": "Redis client not initialized"}
            
            # 基本统计
            total_count = await self.redis_client.get(f"{self.key_prefix}count")
            stats_data = await self.redis_client.hgetall(self._get_stats_key())
            
            # Redis内存使用情况
            info = await self.redis_client.info("memory")
            memory_usage = info.get("used_memory_human", "Unknown")
            
            # 键统计
            all_keys = await self.redis_client.keys(f"{self.key_prefix}*")
            key_stats = {
                "total_keys": len(all_keys),
                "bank_keys": len([k for k in all_keys if ":bank:" in k]),
                "name_keys": len([k for k in all_keys if ":name:" in k]),
                "code_keys": len([k for k in all_keys if ":code:" in k]),
                "keyword_keys": len([k for k in all_keys if ":keyword:" in k])
            }
            
            return {
                "total_banks": int(total_count) if total_count else 0,
                "memory_usage": memory_usage,
                "key_statistics": key_stats,
                "last_updated": stats_data.get("last_updated", "Unknown"),
                "version": stats_data.get("version", "Unknown"),
                "redis_url": self.redis_url,
                "key_prefix": self.key_prefix
            }
            
        except Exception as e:
            logger.error(f"Failed to get Redis stats: {e}")
            return {"error": str(e)}
    
    async def clear_redis_data(self) -> bool:
        """
        清空Redis中的银行数据
        
        Returns:
            是否成功清空
        """
        try:
            if not self.redis_client:
                return False
            
            pattern = f"{self.key_prefix}*"
            keys = await self.redis_client.keys(pattern)
            
            if keys:
                await self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} Redis keys")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear Redis data: {e}")
            return False
    
    async def update_bank_data(self, bank_records: List[BankCode]) -> bool:
        """
        更新Redis中的银行数据
        
        Args:
            bank_records: 要更新的银行记录列表
        
        Returns:
            是否成功更新
        """
        try:
            if not self.redis_client or not bank_records:
                return False
            
            logger.info(f"Updating {len(bank_records)} bank records in Redis")
            
            pipe = self.redis_client.pipeline()
            
            for record in bank_records:
                # 处理created_at字段
                created_at_str = ""
                if record.created_at:
                    if hasattr(record.created_at, 'isoformat'):
                        created_at_str = record.created_at.isoformat()
                    else:
                        created_at_str = str(record.created_at)
                
                # 银行基本信息
                bank_data = {
                    "id": record.id,
                    "bank_name": record.bank_name,
                    "bank_code": record.bank_code,
                    "clearing_code": record.clearing_code or "",
                    "dataset_id": record.dataset_id or 0,
                    "created_at": created_at_str,
                    "updated_at": datetime.now().isoformat()
                }
                
                # 更新银行数据
                bank_key = self._get_bank_key(record.id)
                pipe.hset(bank_key, mapping=bank_data)
                
                # 更新索引
                name_key = self._get_name_key(record.bank_name)
                pipe.set(name_key, record.id)
                
                code_key = self._get_code_key(record.bank_code)
                pipe.set(code_key, record.id)
                
                # 更新关键词索引
                keywords = self._extract_keywords(record.bank_name)
                for keyword in keywords:
                    keyword_key = self._get_keyword_key(keyword)
                    pipe.sadd(keyword_key, record.id)
            
            await pipe.execute()
            
            # 更新统计信息
            current_count = await self.redis_client.get(f"{self.key_prefix}count")
            if current_count:
                # 检查是否是新增记录
                existing_codes = set()
                for record in bank_records:
                    code_key = self._get_code_key(record.bank_code)
                    if await self.redis_client.exists(code_key):
                        existing_codes.add(record.bank_code)
                
                new_records_count = len(bank_records) - len(existing_codes)
                if new_records_count > 0:
                    new_count = int(current_count) + new_records_count
                    await self.redis_client.set(f"{self.key_prefix}count", new_count)
            
            logger.info(f"Successfully updated {len(bank_records)} bank records in Redis")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update bank data in Redis: {e}")
            return False
    
    async def load_bank_data_from_file(
        self, 
        file_path: str, 
        file_format: str = "unl"
    ) -> Dict[str, Any]:
        """
        从文件加载银行数据到Redis
        
        Args:
            file_path: 文件路径
            file_format: 文件格式 (unl, csv, txt)
        
        Returns:
            加载结果
        """
        try:
            logger.info(f"Loading bank data from file: {file_path}")
            
            if not self.redis_client:
                raise Exception("Redis client not initialized")
            
            # 解析文件
            banks_data = []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 如果UTF-8解码失败，尝试其他编码
            if not lines:
                try:
                    with open(file_path, 'r', encoding='gbk') as f:
                        lines = f.readlines()
                    logger.info("Using GBK encoding for file")
                except:
                    with open(file_path, 'r', encoding='latin-1') as f:
                        lines = f.readlines()
                    logger.info("Using Latin-1 encoding for file")
            
            logger.info(f"File contains {len(lines)} lines")
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # 根据文件格式选择分隔符
                    if file_format == "unl" or '|' in line:
                        parts = line.split('|')
                    elif file_format == "csv" or ',' in line:
                        parts = line.split(',')
                    else:
                        parts = line.split('\t')
                    
                    if len(parts) < 3:
                        logger.warning(f"Line {line_num} has insufficient data, skipping")
                        continue
                    
                    # 对于UNL文件，检查倒数第二个字段是否为0
                    if file_format == "unl" or '|' in line:
                        if len(parts) >= 3:
                            # 实际上是倒数第三个字段（索引为-3）
                            target_field = parts[-3].strip()
                            if target_field != '0':
                                logger.debug(f"Line {line_num} third last field is not 0({target_field}), skipping")
                                continue
                        else:
                            logger.warning(f"Line {line_num} has insufficient fields, skipping")
                            continue
                    
                    # 提取数据
                    bank_code = parts[0].strip()
                    bank_name = parts[1].strip()
                    clearing_code = parts[2].strip() if len(parts) > 2 else ""
                    
                    # 验证数据
                    if not bank_code or not bank_name:
                        logger.warning(f"Line {line_num} has incomplete data, skipping")
                        continue
                    
                    # 验证联行号格式
                    if not bank_code.isdigit() or len(bank_code) != 12:
                        logger.warning(f"Line {line_num} has invalid bank code format: {bank_code}")
                        continue
                    
                    banks_data.append({
                        "bank_code": bank_code,
                        "bank_name": bank_name,
                        "clearing_code": clearing_code
                    })
                    
                except Exception as e:
                    logger.warning(f"Error parsing line {line_num}: {e}")
                    continue
            
            if not banks_data:
                return {
                    "status": "no_data",
                    "message": "No valid bank data found in file",
                    "loaded_count": 0
                }
            
            # 批量加载到Redis
            batch_size = self.config["batch_size"]
            total_batches = (len(banks_data) + batch_size - 1) // batch_size
            loaded_count = 0
            
            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, len(banks_data))
                batch_data = banks_data[start_idx:end_idx]
                
                logger.info(f"Processing batch {batch_idx + 1}/{total_batches} ({len(batch_data)} records)")
                
                pipe = self.redis_client.pipeline()
                
                for bank_data in batch_data:
                    # 生成临时ID（基于联行号）
                    temp_id = int(bank_data["bank_code"])
                    
                    # 银行基本信息
                    redis_bank_data = {
                        "id": temp_id,
                        "bank_name": bank_data["bank_name"],
                        "bank_code": bank_data["bank_code"],
                        "clearing_code": bank_data["clearing_code"],
                        "dataset_id": 1,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                    
                    # 存储银行数据
                    bank_key = self._get_bank_key(temp_id)
                    pipe.hset(bank_key, mapping=redis_bank_data)
                    
                    # 创建索引
                    name_key = self._get_name_key(bank_data["bank_name"])
                    pipe.set(name_key, temp_id)
                    
                    code_key = self._get_code_key(bank_data["bank_code"])
                    pipe.set(code_key, temp_id)
                    
                    # 创建关键词索引
                    keywords = self._extract_keywords(bank_data["bank_name"])
                    for keyword in keywords:
                        keyword_key = self._get_keyword_key(keyword)
                        pipe.sadd(keyword_key, temp_id)
                    
                    loaded_count += 1
                
                # 执行批量操作
                await pipe.execute()
                logger.info(f"Loaded batch {batch_idx + 1}/{total_batches} to Redis")
            
            # 更新统计信息
            stats = {
                "total_count": loaded_count,
                "last_updated": datetime.now().isoformat(),
                "version": "1.0",
                "source": "file_upload"
            }
            
            await self.redis_client.set(f"{self.key_prefix}count", loaded_count)
            await self.redis_client.hset(self._get_stats_key(), mapping=stats)
            
            logger.info(f"Successfully loaded {loaded_count} bank records from file to Redis")
            
            return {
                "status": "success",
                "loaded_count": loaded_count,
                "total_batches": total_batches,
                "source_file": file_path
            }
            
        except Exception as e:
            logger.error(f"Failed to load bank data from file: {e}")
            return {
                "status": "error", 
                "error": str(e),
                "loaded_count": 0
            }