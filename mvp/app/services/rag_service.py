"""
RAG Service - 检索增强生成服务

本服务实现了基于向量数据库的RAG系统，用于银行代码智能检索。

主要功能：
    - 向量化银行数据并存储到Chroma数据库
    - 基于语义相似度检索相关银行信息
    - 支持混合检索（向量检索 + 关键词检索）
    - 自动管理向量数据库的创建和更新

技术架构：
    - 向量数据库：ChromaDB
    - 嵌入模型：sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
    - 检索策略：语义相似度 + 关键词过滤
    - 存储格式：银行名称、联行号、清算代码的结构化向量

使用示例：
    >>> rag_service = RAGService(db_session)
    >>> 
    >>> # 初始化向量数据库
    >>> await rag_service.initialize_vector_db()
    >>> 
    >>> # 检索相关银行
    >>> results = await rag_service.retrieve_relevant_banks(
    ...     "工商银行北京分行",
    ...     top_k=5
    ... )
    >>> 
    >>> # 更新向量数据库
    >>> await rag_service.update_vector_db()
"""
import os
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np
from sqlalchemy.orm import Session
from loguru import logger

from app.models.bank_code import BankCode


class RAGService:
    """
    RAG服务 - 基于向量数据库的检索增强生成
    
    本类实现了完整的RAG系统，包括：
    1. 向量数据库管理（ChromaDB）
    2. 文档嵌入和检索
    3. 混合检索策略
    4. 数据同步和更新
    5. 参数配置管理
    
    属性：
        db (Session): 数据库会话
        chroma_client: ChromaDB客户端
        collection: 向量集合
        embedding_model: 嵌入模型
        vector_db_path (str): 向量数据库存储路径
        config (Dict): RAG配置参数
    """
    
    def __init__(
        self,
        db: Session,
        vector_db_path: str = "data/vector_db",
        embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化RAG服务
        
        Args:
            db: 数据库会话
            vector_db_path: 向量数据库存储路径
            embedding_model_name: 嵌入模型名称
            config: RAG配置参数
        """
        self.db = db
        self.vector_db_path = Path(vector_db_path)
        self.vector_db_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化RAG配置参数
        self.config = self._get_default_config()
        if config:
            self.config.update(config)
        
        # 初始化ChromaDB客户端
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.vector_db_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
                is_persistent=True
            )
        )
        
        # 初始化嵌入模型
        logger.info(f"Loading embedding model: {embedding_model_name}")
        self.embedding_model = SentenceTransformer(embedding_model_name)
        logger.info("Embedding model loaded successfully")
        
        # 获取或创建集合
        self.collection_name = "bank_codes"
        try:
            self.collection = self.chroma_client.get_collection(self.collection_name)
            logger.info(f"Loaded existing collection: {self.collection_name}")
        except Exception:
            self.collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"description": "Bank codes and information for RAG retrieval"}
            )
            logger.info(f"Created new collection: {self.collection_name}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        获取RAG系统的默认配置参数
        
        Returns:
            默认配置字典
        """
        return {
            # 检索阶段参数
            "chunk_size": 512,                    # 文档分块大小
            "chunk_overlap": 50,                  # 分块重叠大小
            "top_k": 5,                          # 检索结果数量
            "similarity_threshold": 0.1,          # 相似度阈值（降低以提高召回率）
            "vector_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            
            # 增强阶段参数
            "temperature": 0.1,                   # 生成温度
            "max_tokens": 512,                    # 最大生成长度
            "context_format": "structured",       # 上下文格式
            "instruction": "基于提供的银行信息，准确回答用户关于银行联行号的问题。",
            
            # 混合检索参数
            "vector_weight": 0.6,                 # 向量检索权重
            "keyword_weight": 0.4,                # 关键词检索权重
            "enable_hybrid": True,                # 启用混合检索
            
            # 性能优化参数
            "batch_size": 100,                    # 批处理大小
            "cache_enabled": True,                # 启用缓存
            "cache_ttl": 3600,                   # 缓存过期时间（秒）
        }
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取当前RAG配置参数
        
        Returns:
            当前配置字典
        """
        return self.config.copy()
    
    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """
        更新RAG配置参数
        
        Args:
            new_config: 新的配置参数
        
        Returns:
            是否更新成功
        """
        try:
            # 验证配置参数
            validated_config = self._validate_config(new_config)
            
            # 更新配置
            self.config.update(validated_config)
            
            logger.info(f"RAG配置已更新: {validated_config}")
            return True
            
        except Exception as e:
            logger.error(f"更新RAG配置失败: {e}")
            return False
    
    def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证RAG配置参数
        
        Args:
            config: 待验证的配置
        
        Returns:
            验证后的配置
        
        Raises:
            ValueError: 配置参数无效
        """
        validated = {}
        
        # 检索阶段参数验证
        if "chunk_size" in config:
            chunk_size = int(config["chunk_size"])
            if not 100 <= chunk_size <= 2048:
                raise ValueError("chunk_size必须在100-2048之间")
            validated["chunk_size"] = chunk_size
        
        if "chunk_overlap" in config:
            chunk_overlap = int(config["chunk_overlap"])
            if not 0 <= chunk_overlap <= 200:
                raise ValueError("chunk_overlap必须在0-200之间")
            validated["chunk_overlap"] = chunk_overlap
        
        if "top_k" in config:
            top_k = int(config["top_k"])
            if not 1 <= top_k <= 50:
                raise ValueError("top_k必须在1-50之间")
            validated["top_k"] = top_k
        
        if "similarity_threshold" in config:
            threshold = float(config["similarity_threshold"])
            if not 0.0 <= threshold <= 1.0:
                raise ValueError("similarity_threshold必须在0.0-1.0之间")
            validated["similarity_threshold"] = threshold
        
        # 增强阶段参数验证
        if "temperature" in config:
            temperature = float(config["temperature"])
            if not 0.0 <= temperature <= 2.0:
                raise ValueError("temperature必须在0.0-2.0之间")
            validated["temperature"] = temperature
        
        if "max_tokens" in config:
            max_tokens = int(config["max_tokens"])
            if not 50 <= max_tokens <= 2048:
                raise ValueError("max_tokens必须在50-2048之间")
            validated["max_tokens"] = max_tokens
        
        if "context_format" in config:
            if config["context_format"] not in ["structured", "natural", "json"]:
                raise ValueError("context_format必须是structured、natural或json")
            validated["context_format"] = config["context_format"]
        
        if "instruction" in config:
            instruction = str(config["instruction"]).strip()
            if len(instruction) < 10:
                raise ValueError("instruction长度不能少于10个字符")
            validated["instruction"] = instruction
        
        # 混合检索参数验证
        vector_weight_provided = "vector_weight" in config
        keyword_weight_provided = "keyword_weight" in config
        
        if vector_weight_provided:
            weight = float(config["vector_weight"])
            if not 0.0 <= weight <= 1.0:
                raise ValueError("vector_weight必须在0.0-1.0之间")
            validated["vector_weight"] = weight
        
        if keyword_weight_provided:
            weight = float(config["keyword_weight"])
            if not 0.0 <= weight <= 1.0:
                raise ValueError("keyword_weight必须在0.0-1.0之间")
            validated["keyword_weight"] = weight
        
        # 权重自动计算逻辑
        if vector_weight_provided and not keyword_weight_provided:
            # 只提供了vector_weight，自动计算keyword_weight
            validated["keyword_weight"] = 1.0 - validated["vector_weight"]
        elif keyword_weight_provided and not vector_weight_provided:
            # 只提供了keyword_weight，自动计算vector_weight
            validated["vector_weight"] = 1.0 - validated["keyword_weight"]
        elif vector_weight_provided and keyword_weight_provided:
            # 两个权重都提供了，检查和是否为1.0
            total_weight = validated["vector_weight"] + validated["keyword_weight"]
            if abs(total_weight - 1.0) > 0.01:
                raise ValueError("vector_weight和keyword_weight的和必须等于1.0")
        
        if "enable_hybrid" in config:
            validated["enable_hybrid"] = bool(config["enable_hybrid"])
        
        # 性能参数验证
        if "batch_size" in config:
            batch_size = int(config["batch_size"])
            if not 10 <= batch_size <= 1000:
                raise ValueError("batch_size必须在10-1000之间")
            validated["batch_size"] = batch_size
        
        if "cache_enabled" in config:
            validated["cache_enabled"] = bool(config["cache_enabled"])
        
        if "cache_ttl" in config:
            cache_ttl = int(config["cache_ttl"])
            if not 60 <= cache_ttl <= 86400:  # 1分钟到1天
                raise ValueError("cache_ttl必须在60-86400秒之间")
            validated["cache_ttl"] = cache_ttl
        
        return validated
    
    def _create_document_text(self, bank_record: BankCode) -> str:
        """
        创建用于向量化的文档文本
        
        Args:
            bank_record: 银行记录
        
        Returns:
            格式化的文档文本
        """
        # 创建包含所有相关信息的文本
        text_parts = [
            f"银行名称: {bank_record.bank_name}",
            f"联行号: {bank_record.bank_code}",
        ]
        
        if bank_record.clearing_code:
            text_parts.append(f"清算代码: {bank_record.clearing_code}")
        
        return " | ".join(text_parts)
    
    def _extract_bank_keywords(self, bank_name: str) -> List[str]:
        """
        从银行名称中提取关键词 - 大幅增强版本
        
        Args:
            bank_name: 银行名称
        
        Returns:
            关键词列表
        """
        # 常见银行关键词
        bank_keywords = []
        
        # 主要银行简称映射 - 大幅扩展版本
        bank_mappings = {
            # 国有大型银行
            "中国工商银行": ["工商银行", "工行", "ICBC", "中国工商", "工商", "工商行"],
            "中国农业银行": ["农业银行", "农行", "ABC", "中国农业", "农业", "农行银行"],
            "中国银行": ["中行", "BOC", "中银", "中国银行"],
            "中国建设银行": ["建设银行", "建行", "CCB", "中国建设", "建设", "建行银行"],
            
            # 股份制银行
            "交通银行": ["交行", "BOCOM", "交通", "交银"],
            "中国邮政储蓄银行": ["邮储银行", "邮政银行", "PSBC", "邮储", "邮政储蓄", "邮政", "邮储行", "邮政行"],
            "招商银行": ["招行", "CMB", "招商", "招银"],
            "浦发银行": ["上海浦东发展银行", "SPDB", "浦东发展银行", "浦东发展", "浦发", "浦东银行"],
            "中信银行": ["CITIC", "中信", "中信行"],
            "中国光大银行": ["光大银行", "CEB", "光大", "光大行"],
            "华夏银行": ["HXB", "华夏", "华夏行"],
            "中国民生银行": ["民生银行", "CMBC", "民生", "民生行"],
            "广发银行": ["CGB", "广发", "广东发展银行", "广发行", "广东发展"],
            "平安银行": ["PAB", "平安", "平安行"],
            "兴业银行": ["CIB", "兴业", "兴业行"],
            
            # 城市商业银行
            "北京银行": ["BOB", "北京", "北京行", "京行"],
            "上海银行": ["BOS", "上海", "上海行", "沪行"],
            "江苏银行": ["江苏", "江苏行", "苏行"],
            "浙商银行": ["浙商", "浙商行"],
            "渤海银行": ["渤海", "渤海行"],
            "恒丰银行": ["恒丰", "恒丰行"],
            "南京银行": ["南京", "南京行", "宁行"],
            "宁波银行": ["宁波", "宁波行", "甬行"],
            "杭州银行": ["杭州", "杭州行", "杭行"],
            "徽商银行": ["徽商", "徽商行", "皖行"],
            "长沙银行": ["长沙", "长沙行", "湘行"],
            "郑州银行": ["郑州", "郑州行", "豫行"],
            "青岛银行": ["青岛", "青岛行", "青行"],
            "大连银行": ["大连", "大连行", "连行"],
            "哈尔滨银行": ["哈尔滨", "哈尔滨行", "哈行"],
            "盛京银行": ["盛京", "盛京行"],
            "锦州银行": ["锦州", "锦州行"],
            
            # 农村商业银行
            "北京农商银行": ["北京农商", "京农商", "北京农村商业银行"],
            "上海农商银行": ["上海农商", "沪农商", "上海农村商业银行"],
            "重庆农商银行": ["重庆农商", "渝农商", "重庆农村商业银行"],
            "广州农商银行": ["广州农商", "穗农商", "广州农村商业银行"],
            "深圳农商银行": ["深圳农商", "深农商", "深圳农村商业银行"],
            
            # 外资银行
            "东亚银行": ["东亚", "东亚行", "BEA"],
            "花旗银行": ["花旗", "花旗行", "Citibank"],
            "汇丰银行": ["汇丰", "汇丰行", "HSBC"],
            "渣打银行": ["渣打", "渣打行", "Standard Chartered"],
            "星展银行": ["星展", "星展行", "DBS"],
            "三菱银行": ["三菱", "三菱行", "MUFG"],
            "三井银行": ["三井", "三井行", "SMBC"],
            
            # 政策性银行
            "国家开发银行": ["国开行", "国家开发", "CDB"],
            "中国进出口银行": ["进出口银行", "进出口行", "EXIM"],
            "中国农业发展银行": ["农发行", "农业发展银行", "ADBC"],
            
            # 其他银行
            "中国银联": ["银联", "UnionPay"],
            "网商银行": ["网商", "网商行"],
            "微众银行": ["微众", "微众行"],
            "新网银行": ["新网", "新网行"],
            "亿联银行": ["亿联", "亿联行"]
        }
        
        # 添加完整银行名称
        bank_keywords.append(bank_name)
        
        # 查找匹配的简称 - 使用更精确的匹配
        for full_name, aliases in bank_mappings.items():
            # 完全匹配或包含匹配
            if full_name == bank_name or full_name in bank_name:
                bank_keywords.extend(aliases)
                break
            # 检查是否银行名称包含任何别名
            for alias in aliases:
                if alias in bank_name and len(alias) >= 2:  # 至少2个字符的别名
                    bank_keywords.extend([full_name] + aliases)
                    break
        
        # 提取地理位置信息 - 大幅扩展版本
        locations = []
        common_locations = [
            # 直辖市
            "北京", "上海", "天津", "重庆",
            # 省会城市
            "石家庄", "太原", "呼和浩特", "沈阳", "长春", "哈尔滨",
            "南京", "杭州", "合肥", "福州", "南昌", "济南", "郑州",
            "武汉", "长沙", "广州", "南宁", "海口", "成都", "贵阳",
            "昆明", "拉萨", "西安", "兰州", "西宁", "银川", "乌鲁木齐",
            # 计划单列市
            "厦门", "深圳", "青岛", "大连", "宁波",
            # 重要地级市
            "苏州", "无锡", "常州", "温州", "嘉兴", "湖州", "绍兴", "金华", 
            "衢州", "舟山", "台州", "丽水", "芜湖", "蚌埠", "淮南", "马鞍山", 
            "淮北", "铜陵", "安庆", "黄山", "滁州", "阜阳", "宿州", "六安", 
            "亳州", "池州", "宣城", "莆田", "三明", "泉州", "漳州", "南平", 
            "龙岩", "宁德", "景德镇", "萍乡", "九江", "新余", "鹰潭", "赣州", 
            "吉安", "宜春", "抚州", "上饶", "淄博", "枣庄", "东营", "烟台", 
            "潍坊", "济宁", "泰安", "威海", "日照", "莱芜", "临沂", "德州", 
            "聊城", "滨州", "菏泽", "开封", "洛阳", "平顶山", "安阳", "鹤壁", 
            "新乡", "焦作", "濮阳", "许昌", "漯河", "三门峡", "南阳", "商丘", 
            "信阳", "周口", "驻马店", "黄石", "十堰", "宜昌", "襄阳", "鄂州", 
            "荆门", "孝感", "荆州", "黄冈", "咸宁", "随州", "恩施", "株洲", 
            "湘潭", "衡阳", "邵阳", "岳阳", "常德", "张家界", "益阳", "郴州", 
            "永州", "怀化", "娄底", "韶关", "珠海", "汕头", "佛山", "江门", 
            "湛江", "茂名", "肇庆", "惠州", "梅州", "汕尾", "河源", "阳江", 
            "清远", "东莞", "中山", "潮州", "揭阳", "云浮", "柳州", "桂林", 
            "梧州", "北海", "防城港", "钦州", "贵港", "玉林", "百色", "贺州", 
            "河池", "来宾", "崇左", "三亚", "三沙", "儋州", "自贡", "攀枝花", 
            "泸州", "德阳", "绵阳", "广元", "遂宁", "内江", "乐山", "南充", 
            "眉山", "宜宾", "广安", "达州", "雅安", "巴中", "资阳", "江油", 
            "六盘水", "遵义", "安顺", "毕节", "铜仁", "曲靖", "玉溪", "保山", 
            "昭通", "丽江", "普洱", "临沧", "昌都", "山南", "日喀则", "那曲", 
            "阿里", "林芝", "铜川", "宝鸡", "咸阳", "渭南", "延安", "汉中", 
            "榆林", "安康", "商洛", "嘉峪关", "金昌", "白银", "天水", "武威", 
            "张掖", "平凉", "酒泉", "庆阳", "定西", "陇南", "海东", "石嘴山", 
            "吴忠", "固原", "中卫", "克拉玛依", "吐鲁番", "哈密"
        ]
        
        for location in common_locations:
            if location in bank_name:
                locations.append(location)
        
        bank_keywords.extend(locations)
        
        # 提取支行、分行等类型信息 - 扩展版本
        branch_types = [
            "支行", "分行", "分理处", "储蓄所", "营业部", "营业厅", "网点", 
            "分支机构", "办事处", "代理点", "服务点", "自助银行", "便民服务点"
        ]
        for branch_type in branch_types:
            if branch_type in bank_name:
                bank_keywords.append(branch_type)
        
        # 提取特殊区域标识 - 新增功能
        special_areas = [
            # 开发区
            "开发区", "高新区", "经济开发区", "技术开发区", "工业园区", "科技园",
            "保税区", "自贸区", "新区", "示范区", "试验区",
            # 商业区
            "CBD", "商务区", "金融区", "商业区", "购物中心", "广场", "大厦",
            "中心", "城", "港", "湾", "岛", "山", "湖", "河", "桥", "路", "街",
            # 交通枢纽
            "机场", "火车站", "高铁站", "地铁站", "汽车站", "港口", "码头"
        ]
        
        for area in special_areas:
            if area in bank_name:
                bank_keywords.append(area)
        
        # 去重并过滤短关键词
        unique_keywords = []
        seen = set()
        for keyword in bank_keywords:
            if keyword not in seen and len(keyword) >= 2:  # 至少2个字符
                seen.add(keyword)
                unique_keywords.append(keyword)
        
        return unique_keywords
    
    def _extract_question_entities(self, question: str) -> Dict[str, str]:
        """
        从问题中提取结构化实体信息 - 增强版本
        
        Args:
            question: 用户问题
        
        Returns:
            提取的实体字典
        """
        import re
        
        entities = {
            'bank_name': None,
            'bank_type': None,
            'location': None,
            'branch_name': None,
            'keywords': [],
            'full_name': None  # 添加完整名称字段
        }
        
        # 检查是否是完整的银行名称
        if "股份有限公司" in question and ("支行" in question or "分行" in question):
            entities['full_name'] = question.strip()
            logger.info(f"RAG: Detected full bank name: {entities['full_name']}")
        
        # 银行名称映射（大幅扩展，支持更多银行简称和别名）
        bank_mappings = {
            # 国有大型银行
            '工商银行': '中国工商银行',
            '工行': '中国工商银行',
            'ICBC': '中国工商银行',
            '农业银行': '中国农业银行',
            '农行': '中国农业银行', 
            'ABC': '中国农业银行',
            '中国银行': '中国银行',
            '中行': '中国银行',
            'BOC': '中国银行',
            '建设银行': '中国建设银行',
            '建行': '中国建设银行',
            'CCB': '中国建设银行',
            
            # 股份制银行
            '交通银行': '交通银行',
            '交行': '交通银行',
            'BOCOM': '交通银行',
            '招商银行': '招商银行',
            '招行': '招商银行',
            'CMB': '招商银行',
            '浦发银行': '上海浦东发展银行',
            '浦东发展银行': '上海浦东发展银行',
            'SPDB': '上海浦东发展银行',
            '中信银行': '中信银行',
            '中信': '中信银行',
            'CITIC': '中信银行',
            '光大银行': '中国光大银行',
            '光大': '中国光大银行',
            'CEB': '中国光大银行',
            '华夏银行': '华夏银行',
            '华夏': '华夏银行',
            'HXB': '华夏银行',
            '民生银行': '中国民生银行',
            '民生': '中国民生银行',
            'CMBC': '中国民生银行',
            '广发银行': '广发银行',
            '广发': '广发银行',
            'CGB': '广发银行',
            '广东发展银行': '广发银行',
            '平安银行': '平安银行',
            '平安': '平安银行',
            'PAB': '平安银行',
            '兴业银行': '兴业银行',
            '兴业': '兴业银行',
            'CIB': '兴业银行',
            
            # 邮政储蓄银行
            '邮储银行': '中国邮政储蓄银行',
            '邮政储蓄银行': '中国邮政储蓄银行',
            '邮政银行': '中国邮政储蓄银行',
            '邮储': '中国邮政储蓄银行',
            '邮政储蓄': '中国邮政储蓄银行',
            'PSBC': '中国邮政储蓄银行',
            
            # 城市商业银行
            '北京银行': '北京银行',
            'BOB': '北京银行',
            '上海银行': '上海银行',
            'BOS': '上海银行',
            '江苏银行': '江苏银行',
            '浙商银行': '浙商银行',
            '浙商': '浙商银行',
            '渤海银行': '渤海银行',
            '渤海': '渤海银行',
            '恒丰银行': '恒丰银行',
            '恒丰': '恒丰银行',
            '南京银行': '南京银行',
            '宁波银行': '宁波银行',
            '杭州银行': '杭州银行',
            '徽商银行': '徽商银行',
            '长沙银行': '长沙银行',
            '郑州银行': '郑州银行',
            '青岛银行': '青岛银行',
            '大连银行': '大连银行',
            '哈尔滨银行': '哈尔滨银行',
            '盛京银行': '盛京银行',
            '锦州银行': '锦州银行',
            
            # 外资银行
            '东亚银行': '东亚银行',
            '花旗银行': '花旗银行',
            '花旗': '花旗银行',
            '汇丰银行': '汇丰银行',
            '汇丰': '汇丰银行',
            '渣打银行': '渣打银行',
            '渣打': '渣打银行',
            '星展银行': '星展银行',
            '星展': '星展银行',
            '三菱银行': '三菱银行',
            '三井银行': '三井银行'
        }
        
        # 提取银行名称 - 增强匹配逻辑
        for short_name, full_name in bank_mappings.items():
            if short_name in question:
                entities['bank_name'] = full_name
                entities['bank_type'] = short_name
                entities['keywords'].append(short_name)
                entities['keywords'].append(full_name)
                break
        
        # 如果没有找到简称，尝试完整名称匹配
        if not entities['bank_name']:
            for full_name in bank_mappings.values():
                if full_name in question:
                    entities['bank_name'] = full_name
                    entities['bank_type'] = full_name
                    entities['keywords'].append(full_name)
                    break
        
        # 提取地理位置 - 大幅扩展城市列表
        locations = [
            # 直辖市
            '北京', '上海', '天津', '重庆',
            # 省会城市和计划单列市
            '广州', '深圳', '厦门', '青岛', '大连', '宁波', '苏州', '杭州', '南京', 
            '武汉', '成都', '西安', '长沙', '郑州', '济南', '合肥', '福州', '南昌', 
            '太原', '石家庄', '沈阳', '长春', '哈尔滨', '昆明', '贵阳', '南宁', 
            '海口', '兰州', '银川', '西宁', '乌鲁木齐', '拉萨', '呼和浩特',
            # 重要地级市
            '无锡', '常州', '温州', '嘉兴', '湖州', '绍兴', '金华', '衢州', 
            '舟山', '台州', '丽水', '芜湖', '蚌埠', '淮南', '马鞍山', '淮北', 
            '铜陵', '安庆', '黄山', '滁州', '阜阳', '宿州', '六安', '亳州', 
            '池州', '宣城', '莆田', '三明', '泉州', '漳州', '南平', '龙岩', 
            '宁德', '景德镇', '萍乡', '九江', '新余', '鹰潭', '赣州', '吉安', 
            '宜春', '抚州', '上饶', '淄博', '枣庄', '东营', '烟台', '潍坊', 
            '济宁', '泰安', '威海', '日照', '莱芜', '临沂', '德州', '聊城', 
            '滨州', '菏泽', '开封', '洛阳', '平顶山', '安阳', '鹤壁', '新乡', 
            '焦作', '濮阳', '许昌', '漯河', '三门峡', '南阳', '商丘', '信阳', 
            '周口', '驻马店', '黄石', '十堰', '宜昌', '襄阳', '鄂州', '荆门', 
            '孝感', '荆州', '黄冈', '咸宁', '随州', '恩施', '株洲', '湘潭', 
            '衡阳', '邵阳', '岳阳', '常德', '张家界', '益阳', '郴州', '永州', 
            '怀化', '娄底', '韶关', '珠海', '汕头', '佛山', '江门', '湛江', 
            '茂名', '肇庆', '惠州', '梅州', '汕尾', '河源', '阳江', '清远', 
            '东莞', '中山', '潮州', '揭阳', '云浮', '柳州', '桂林', '梧州', 
            '北海', '防城港', '钦州', '贵港', '玉林', '百色', '贺州', '河池', 
            '来宾', '崇左', '三亚', '三沙', '儋州'
        ]
        
        for location in locations:
            if location in question:
                entities['location'] = location
                entities['keywords'].append(location)
                break
        
        # 提取支行名称（更精确的模式）- 增强支行类型识别
        branch_patterns = [
            r'([^银行]{2,12}支行)',
            r'([^银行]{2,12}分行)',
            r'([^银行]{2,12}营业部)',
            r'([^银行]{2,12}营业厅)',
            r'([^银行]{2,12}分理处)',
            r'([^银行]{2,12}储蓄所)',
            r'([^银行]{2,12}网点)'
        ]
        
        for pattern in branch_patterns:
            match = re.search(pattern, question)
            if match:
                branch_full = match.group(1)
                # 提取支行名称（去掉类型后缀）
                for suffix in ['支行', '分行', '营业部', '营业厅', '分理处', '储蓄所', '网点']:
                    if branch_full.endswith(suffix):
                        entities['branch_name'] = branch_full[:-len(suffix)].strip()
                        break
                else:
                    entities['branch_name'] = branch_full.strip()
                entities['keywords'].append(branch_full)
                break
        
        # 特殊处理：商业区、商圈、地标等
        commercial_areas = [
            # 北京
            '西单', '王府井', '中关村', '国贸', '金融街', '望京', '三里屯', 
            '朝阳门', '建国门', '复兴门', '西直门', '东直门', '安定门', '崇文门',
            '宣武门', '阜成门', '德胜门', '和平门', '前门', '天安门', '雍和宫',
            '北京站', '北京西站', '北京南站', '首都机场', '大兴机场',
            # 上海
            '陆家嘴', '外滩', '南京路', '淮海路', '徐家汇', '人民广场', '静安寺',
            '虹桥', '浦东', '黄浦', '长宁', '普陀', '闸北', '虹口', '杨浦',
            '闵行', '宝山', '嘉定', '金山', '松江', '青浦', '奉贤', '崇明',
            # 广州
            '天河', '越秀', '荔湾', '海珠', '白云', '黄埔', '番禺', '花都',
            '南沙', '从化', '增城', '珠江新城', '体育中心', '五羊新城',
            # 深圳
            '福田', '罗湖', '南山', '宝安', '龙岗', '盐田', '龙华', '坪山',
            '光明', '大鹏', '华强北', '科技园', '蛇口', '前海'
        ]
        
        for area in commercial_areas:
            if area in question:
                if not entities['branch_name']:
                    entities['branch_name'] = area
                entities['keywords'].append(area)
                # 如果是知名商业区，也可能是地理位置
                if not entities['location'] and area in ['西单', '王府井', '中关村', '国贸', '金融街', '陆家嘴', '外滩']:
                    entities['location'] = area
        
        return entities
    
    async def _full_name_exact_retrieve(
        self,
        full_name: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        完整银行名称精确匹配检索
        
        Args:
            full_name: 完整银行名称
            top_k: 返回结果数量
        
        Returns:
            匹配的银行记录列表
        """
        try:
            logger.info(f"RAG: Full name exact retrieval for: {full_name}")
            
            # 获取所有数据进行精确匹配
            all_results = self.collection.get(include=["metadatas"])
            
            if not all_results["metadatas"]:
                logger.warning("No data found in vector database")
                return []
            
            matches = []
            
            for metadata in all_results["metadatas"]:
                bank_name_meta = metadata["bank_name"]
                
                # 计算完整名称匹配分数
                exact_score = 0
                matched_keywords = []
                
                # 完全匹配检查
                if full_name.lower() == bank_name_meta.lower():
                    exact_score = 10.0  # 完全匹配最高分
                    matched_keywords.append("完全匹配")
                elif full_name.lower() in bank_name_meta.lower():
                    exact_score = 8.0   # 包含匹配高分
                    matched_keywords.append("包含匹配")
                elif bank_name_meta.lower() in full_name.lower():
                    exact_score = 6.0   # 被包含匹配中等分
                    matched_keywords.append("被包含匹配")
                else:
                    # 计算字符重叠度
                    full_name_chars = set(full_name.lower())
                    bank_name_chars = set(bank_name_meta.lower())
                    overlap = len(full_name_chars & bank_name_chars)
                    total = len(full_name_chars | bank_name_chars)
                    
                    if total > 0:
                        overlap_ratio = overlap / total
                        if overlap_ratio > 0.7:  # 70%以上字符重叠
                            exact_score = overlap_ratio * 5.0
                            matched_keywords.append(f"字符重叠{overlap_ratio:.2f}")
                
                # 只保留有匹配的结果
                if exact_score > 0:
                    matches.append({
                        "bank_name": metadata["bank_name"],
                        "bank_code": metadata["bank_code"],
                        "clearing_code": metadata.get("clearing_code", ""),
                        "similarity_score": 1.0,
                        "keyword_score": exact_score,
                        "final_score": exact_score,
                        "matched_keywords": matched_keywords,
                        "bank_id": metadata["bank_id"]
                    })
            
            # 按分数排序
            matches.sort(key=lambda x: x["final_score"], reverse=True)
            result = matches[:top_k]
            
            logger.info(f"RAG: Full name exact retrieval found {len(result)} matches")
            for i, match in enumerate(result):
                logger.info(f"RAG: Full Name Match {i+1}: {match['bank_name']} (Score: {match['final_score']:.3f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Full name exact retrieval failed: {e}")
            return []
    
    async def _exact_bank_retrieve(
        self,
        bank_name: str,
        location: str = None,
        branch_name: str = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        精确银行名称匹配检索 - 修复版本，优先使用字符串匹配
        
        Args:
            bank_name: 银行名称
            location: 地理位置（可选）
            branch_name: 支行名称（可选）
            top_k: 返回结果数量
        
        Returns:
            匹配的银行记录列表
        """
        try:
            logger.info(f"RAG: Exact bank retrieval for: {bank_name}, location: {location}, branch: {branch_name}")
            
            # 获取所有数据进行精确匹配（这是最可靠的方法）
            all_results = self.collection.get(include=["metadatas"])
            
            if not all_results["metadatas"]:
                logger.warning("No data found in vector database")
                return []
            
            matches = []
            
            for metadata in all_results["metadatas"]:
                bank_name_meta = metadata["bank_name"]
                
                # 精确匹配评分
                exact_score = 0
                matched_keywords = []
                
                # 银行名称匹配（必须匹配）
                bank_match = False
                if bank_name:
                    # 检查多种匹配方式
                    if (bank_name.lower() in bank_name_meta.lower() or 
                        any(alias.lower() in bank_name_meta.lower() for alias in [
                            "工商银行", "中国工商银行", "ICBC"
                        ] if bank_name in ["工商银行", "中国工商银行"])):
                        exact_score += 3.0
                        matched_keywords.append(bank_name)
                        bank_match = True
                
                # 支行名称匹配（关键！）
                branch_match = False
                if branch_name:
                    if branch_name.lower() in bank_name_meta.lower():
                        exact_score += 5.0  # 支行匹配给予最高分
                        matched_keywords.append(branch_name)
                        branch_match = True
                    else:
                        # 如果指定了支行但不匹配，大幅降分
                        exact_score -= 2.0
                
                # 地理位置匹配
                if location and location.lower() in bank_name_meta.lower():
                    exact_score += 1.0
                    matched_keywords.append(location)
                
                # 只有在有实际匹配时才加入结果
                if (bank_match or branch_match) and exact_score > 0:
                    matches.append({
                        "bank_name": metadata["bank_name"],
                        "bank_code": metadata["bank_code"],
                        "clearing_code": metadata.get("clearing_code", ""),
                        "similarity_score": 1.0,  # 精确匹配给满分
                        "keyword_score": exact_score,
                        "final_score": exact_score,
                        "matched_keywords": matched_keywords,
                        "bank_id": metadata["bank_id"]
                    })
            
            # 按分数排序
            matches.sort(key=lambda x: x["final_score"], reverse=True)
            result = matches[:top_k]
            
            logger.info(f"RAG: Exact bank retrieval found {len(result)} matches")
            for i, match in enumerate(result):
                logger.info(f"RAG: Exact Match {i+1}: {match['bank_name']} (Score: {match['final_score']:.3f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Exact bank retrieval failed: {e}")
            return []
            logger.info(f"RAG: Exact bank retrieval for: {bank_name}, location: {location}, branch: {branch_name}")
            
            # 获取所有数据进行精确匹配（这是最可靠的方法）
            all_results = self.collection.get(include=["metadatas"])
            
            if not all_results["metadatas"]:
                logger.warning("No data found in vector database")
                return []
            
            matches = []
            
            for metadata in all_results["metadatas"]:
                bank_name_meta = metadata["bank_name"]
                
                # 精确匹配评分
                exact_score = 0
                matched_keywords = []
                
                # 银行名称匹配（必须匹配）
                bank_match = False
                if bank_name:
                    # 检查多种匹配方式
                    if (bank_name.lower() in bank_name_meta.lower() or 
                        any(alias.lower() in bank_name_meta.lower() for alias in [
                            "工商银行", "中国工商银行", "ICBC"
                        ] if bank_name in ["工商银行", "中国工商银行"])):
                        exact_score += 3.0
                        matched_keywords.append(bank_name)
                        bank_match = True
                
                # 支行名称匹配（关键！）
                branch_match = False
                if branch_name:
                    if branch_name.lower() in bank_name_meta.lower():
                        exact_score += 5.0  # 支行匹配给予最高分
                        matched_keywords.append(branch_name)
                        branch_match = True
                    else:
                        # 如果指定了支行但不匹配，大幅降分
                        exact_score -= 2.0
                
                # 地理位置匹配
                if location and location.lower() in bank_name_meta.lower():
                    exact_score += 1.0
                    matched_keywords.append(location)
                
                # 只有在有实际匹配时才加入结果
                if (bank_match or branch_match) and exact_score > 0:
                    matches.append({
                        "bank_name": metadata["bank_name"],
                        "bank_code": metadata["bank_code"],
                        "clearing_code": metadata.get("clearing_code", ""),
                        "similarity_score": 1.0,  # 精确匹配给满分
                        "keyword_score": exact_score,
                        "final_score": exact_score,
                        "matched_keywords": matched_keywords,
                        "bank_id": metadata["bank_id"]
                    })
            
            # 按分数排序
            matches.sort(key=lambda x: x["final_score"], reverse=True)
            result = matches[:top_k]
            
            logger.info(f"RAG: Exact bank retrieval found {len(result)} matches")
            for i, match in enumerate(result):
                logger.info(f"RAG: Exact Match {i+1}: {match['bank_name']} (Score: {match['final_score']:.3f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Exact bank retrieval failed: {e}")
            return []
    
    async def _location_bank_retrieve(
        self,
        location: str,
        bank_type: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        地理位置 + 银行类型匹配检索 - 优化版本，基于向量检索
        
        Args:
            location: 地理位置
            bank_type: 银行类型
            top_k: 返回结果数量
        
        Returns:
            匹配的银行记录列表
        """
        try:
            logger.info(f"RAG: Location bank retrieval for: {location} + {bank_type}")
            
            # 构建查询文本
            query_text = f"{bank_type} {location}"
            
            # 使用向量检索
            query_embedding = self.embedding_model.encode([query_text], convert_to_tensor=False)
            
            vector_results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=min(top_k * 8, 150),  # 获取更多候选
                include=["metadatas", "distances"]
            )
            
            if not vector_results["metadatas"] or not vector_results["metadatas"][0]:
                logger.warning("No results found in location bank retrieval")
                return []
            
            matches = []
            metadatas = vector_results["metadatas"][0]
            distances = vector_results["distances"][0]
            
            for i, metadata in enumerate(metadatas):
                bank_name_meta = metadata["bank_name"]
                distance = distances[i]
                
                # 基础向量相似度分数
                base_score = max(0.0, 1.0 / (1.0 + distance))
                
                # 地理位置和银行类型匹配检查
                location_match = location.lower() in bank_name_meta.lower()
                bank_match = bank_type.lower() in bank_name_meta.lower()
                
                if location_match or bank_match:
                    match_score = 0
                    matched_keywords = []
                    
                    if location_match and bank_match:
                        match_score = 2.5  # 双重匹配高分
                        matched_keywords = [location, bank_type]
                    elif location_match:
                        match_score = 1.5  # 地理位置匹配
                        matched_keywords = [location]
                    elif bank_match:
                        match_score = 1.5  # 银行类型匹配
                        matched_keywords = [bank_type]
                    
                    final_score = base_score + match_score
                    
                    matches.append({
                        "bank_name": metadata["bank_name"],
                        "bank_code": metadata["bank_code"],
                        "clearing_code": metadata.get("clearing_code", ""),
                        "similarity_score": base_score,
                        "keyword_score": match_score,
                        "final_score": final_score,
                        "matched_keywords": matched_keywords,
                        "bank_id": metadata["bank_id"]
                    })
            
            # 按分数排序
            matches.sort(key=lambda x: x["final_score"], reverse=True)
            result = matches[:top_k]
            
            logger.info(f"RAG: Location bank retrieval found {len(result)} matches")
            for i, match in enumerate(result):
                logger.info(f"RAG: Location Match {i+1}: {match['bank_name']} (Score: {match['final_score']:.3f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Location bank retrieval failed: {e}")
            return []
    
    def _deduplicate_and_rerank(
        self,
        question: str,
        all_results: List[Dict[str, Any]],
        entities: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        去重并重新排序所有检索结果
        
        Args:
            question: 原始问题
            all_results: 所有检索结果
            entities: 提取的实体
        
        Returns:
            去重并重排序的结果
        """
        # 去重（基于bank_code）
        seen_codes = set()
        unique_results = []
        
        for result in all_results:
            if result['bank_code'] not in seen_codes:
                seen_codes.add(result['bank_code'])
                unique_results.append(result)
        
        # 重新计算综合分数
        for result in unique_results:
            base_score = result.get('strategy_score', result.get('final_score', 0))
            
            # 银行名称精确匹配加分
            if entities.get('bank_name') and entities['bank_name'] in result['bank_name']:
                base_score += 2.0
            
            # 地理位置匹配加分
            if entities.get('location') and entities['location'] in result['bank_name']:
                base_score += 1.0
            
            # 支行名称匹配加分
            if entities.get('branch_name') and entities['branch_name'] in result['bank_name']:
                base_score += 1.5
            
            # 检索方法权重调整
            method = result.get('retrieval_method', 'unknown')
            if method == 'full_name_exact':
                base_score *= 2.0  # 完整名称匹配最高额外加权
            elif method == 'exact_bank':
                base_score *= 1.2  # 精确银行匹配额外加权
            elif method == 'location_bank':
                base_score *= 1.1  # 地理位置匹配额外加权
            
            result['final_score'] = base_score
        
        # 按最终分数排序
        unique_results.sort(key=lambda x: x['final_score'], reverse=True)
        
        return unique_results
    
    def _extract_question_keywords(self, question: str) -> List[str]:
        """
        从用户问题中提取关键词
        
        Args:
            question: 用户问题
        
        Returns:
            关键词列表
        """
        import re
        
        keywords = []
        
        # 1. 提取银行名称相关关键词
        bank_patterns = [
            r'(中国工商银行|工商银行|工行)',
            r'(中国农业银行|农业银行|农行)',
            r'(中国银行|中行)',
            r'(中国建设银行|建设银行|建行)',
            r'(交通银行|交行)',
            r'(招商银行|招行)',
            r'(浦发银行|上海浦东发展银行)',
            r'(中信银行|中信)',
            r'(光大银行|中国光大银行)',
            r'(华夏银行|华夏)',
            r'(民生银行|中国民生银行)',
            r'(广发银行|广发)',
            r'(平安银行|平安)',
            r'(兴业银行|兴业)',
            r'(浙商银行|浙商)',
            r'(渤海银行|渤海)',
            r'(恒丰银行|恒丰)',
            r'(邮储银行|邮政储蓄银行|邮政银行)',
            r'([^，。！？\s]{2,8}银行)'  # 通用银行名称模式
        ]
        
        for pattern in bank_patterns:
            matches = re.findall(pattern, question)
            for match in matches:
                if isinstance(match, tuple):
                    keywords.extend([m for m in match if m])
                else:
                    keywords.append(match)
        
        # 2. 提取地理位置关键词
        location_patterns = [
            r'(北京|上海|天津|重庆)',
            r'(广州|深圳|厦门|青岛|大连|宁波|苏州|杭州|南京|武汉|成都|西安)',
            r'([^，。！？\s]{2,6}[市县区镇])',
            r'([^，。！？\s]{2,8}[省])'
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, question)
            keywords.extend(matches)
        
        # 3. 提取支行类型关键词
        branch_patterns = [
            r'([^，。！？\s]{1,10}支行)',
            r'([^，。！？\s]{1,10}分行)',
            r'(营业部|营业厅|分理处|储蓄所)'
        ]
        
        for pattern in branch_patterns:
            matches = re.findall(pattern, question)
            keywords.extend(matches)
        
        # 4. 分词提取（简单版本）
        # 提取2-4字的词组
        for length in [4, 3, 2]:
            for i in range(len(question) - length + 1):
                word = question[i:i+length]
                # 过滤掉常见停用词和标点
                if not re.search(r'[，。！？\s的是在有什么多少哪里怎么样]', word):
                    keywords.append(word)
        
        # 去重并过滤
        unique_keywords = []
        seen = set()
        for kw in keywords:
            kw = kw.strip()
            if kw and len(kw) >= 2 and kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        
        return unique_keywords
    
    async def initialize_vector_db(self, force_rebuild: bool = False) -> bool:
        """
        初始化向量数据库
        
        Args:
            force_rebuild: 是否强制重建数据库
        
        Returns:
            是否成功初始化
        """
        try:
            # 检查是否需要重建
            collection_count = self.collection.count()
            bank_count = self.db.query(BankCode).count()
            
            if not force_rebuild and collection_count > 0:
                logger.info(f"Vector database already initialized with {collection_count} documents")
                if collection_count == bank_count:
                    logger.info("Vector database is up to date")
                    return True
                else:
                    logger.info(f"Database has {bank_count} banks but vector DB has {collection_count} documents. Updating...")
            
            logger.info("Initializing vector database...")
            
            # 如果强制重建，清空集合
            if force_rebuild and collection_count > 0:
                self.chroma_client.delete_collection(self.collection_name)
                self.collection = self.chroma_client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Bank codes and information for RAG retrieval"}
                )
                logger.info("Cleared existing collection for rebuild")
            
            # 获取所有银行记录
            bank_records = self.db.query(BankCode).filter(BankCode.is_valid == True).all()
            logger.info(f"Found {len(bank_records)} valid bank records")
            
            if not bank_records:
                logger.warning("No bank records found in database")
                return False
            
            # 批量处理向量化
            batch_size = 100
            total_batches = (len(bank_records) + batch_size - 1) // batch_size
            
            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, len(bank_records))
                batch_records = bank_records[start_idx:end_idx]
                
                logger.info(f"Processing batch {batch_idx + 1}/{total_batches} ({len(batch_records)} records)")
                
                # 准备批量数据
                documents = []
                metadatas = []
                ids = []
                
                for record in batch_records:
                    # 创建文档文本
                    doc_text = self._create_document_text(record)
                    documents.append(doc_text)
                    
                    # 创建元数据
                    keywords = self._extract_bank_keywords(record.bank_name)
                    metadata = {
                        "bank_id": record.id,
                        "bank_name": record.bank_name,
                        "bank_code": record.bank_code,
                        "clearing_code": record.clearing_code or "",  # 确保不是None
                        "keywords": ",".join(keywords),
                        "dataset_id": record.dataset_id or 0  # 确保不是None
                    }
                    metadatas.append(metadata)
                    
                    # 创建唯一ID
                    ids.append(f"bank_{record.id}")
                
                # 生成嵌入向量
                embeddings = self.embedding_model.encode(documents, convert_to_tensor=False)
                embeddings_list = embeddings.tolist()
                
                # 添加到向量数据库
                self.collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids,
                    embeddings=embeddings_list
                )
                
                logger.info(f"Added batch {batch_idx + 1}/{total_batches} to vector database")
            
            final_count = self.collection.count()
            logger.info(f"Vector database initialized successfully with {final_count} documents")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize vector database: {e}")
            return False
    
    async def retrieve_relevant_banks(
        self,
        question: str,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        基于语义相似度检索相关银行 - 优化性能版本
        
        Args:
            question: 用户问题
            top_k: 返回结果数量（可选，使用配置默认值）
            similarity_threshold: 相似度阈值（可选，使用配置默认值）
        
        Returns:
            相关银行记录列表
        """
        try:
            # 使用配置参数或传入参数
            top_k = top_k or self.config.get("top_k", 5)
            similarity_threshold = similarity_threshold or self.config.get("similarity_threshold", 0.3)
            
            logger.info(f"RAG: Starting optimized retrieval for question: {question[:50]}...")
            
            # 检查向量数据库是否已初始化
            collection_count = self.collection.count()
            if collection_count == 0:
                logger.warning("Vector database is empty, initializing...")
                await self.initialize_vector_db()
                collection_count = self.collection.count()
                
                if collection_count == 0:
                    logger.error("Failed to initialize vector database")
                    return []
            
            # 智能实体提取
            entities = self._extract_question_entities(question)
            logger.info(f"RAG: Extracted entities: {entities}")
            
            # 优化策略：根据查询类型选择最佳检索方法
            
            # 策略1：完整银行名称 - 直接精确匹配，跳过其他策略
            if entities.get('full_name'):
                logger.info("RAG: Using full name exact match strategy")
                results = await self._full_name_exact_retrieve(entities['full_name'], top_k)
                for result in results:
                    result['retrieval_method'] = 'full_name_exact'
                    result['final_score'] = result.get('final_score', 0) * 20.0  # 最高权重
                return results[:top_k]
            
            # 策略2：银行名称+支行名称 - 精确匹配优先
            if entities.get('bank_name') and entities.get('branch_name'):
                logger.info("RAG: Using bank+branch exact match strategy")
                results = await self._exact_bank_retrieve(
                    entities['bank_name'], 
                    entities.get('location'), 
                    entities['branch_name'],
                    top_k
                )
                if results:  # 如果精确匹配有结果，直接返回
                    for result in results:
                        result['retrieval_method'] = 'exact_bank'
                        result['final_score'] = result.get('final_score', 0) * 10.0
                    return results[:top_k]
            
            # 策略3：混合检索 - 仅在前面策略无结果时使用
            logger.info("RAG: Using hybrid retrieval strategy")
            all_results = []
            
            # 精确银行匹配
            if entities.get('bank_name') or entities.get('branch_name'):
                exact_results = await self._exact_bank_retrieve(
                    entities.get('bank_name', ''), 
                    entities.get('location'), 
                    entities.get('branch_name'),
                    top_k
                )
                for result in exact_results:
                    result['retrieval_method'] = 'exact_bank'
                    result['strategy_score'] = result.get('final_score', 0) * 5.0
                    all_results.append(result)
            
            # 如果精确匹配结果不足，使用关键词检索补充
            if len(all_results) < top_k:
                keyword_results = await self._optimized_keyword_retrieve(question, top_k - len(all_results))
                for result in keyword_results:
                    result['retrieval_method'] = 'keyword'
                    result['strategy_score'] = result.get('final_score', 0) * 3.0
                    all_results.append(result)
            
            # 如果仍然结果不足，使用向量检索
            if len(all_results) < top_k:
                vector_results = await self._vector_retrieve(question, top_k - len(all_results), similarity_threshold)
                for result in vector_results:
                    result['retrieval_method'] = 'vector'
                    result['strategy_score'] = result.get('final_score', 0) * 1.0
                    all_results.append(result)
            
            # 去重和重排序
            final_results = self._deduplicate_and_rerank(question, all_results, entities)[:top_k]
            
            logger.info(f"RAG: Returning {len(final_results)} results from optimized retrieval")
            
            return final_results
            
        except Exception as e:
            logger.error(f"Failed to retrieve relevant banks: {e}")
            return []
    
    async def _vector_retrieve(
        self,
        question: str,
        top_k: int,
        similarity_threshold: float
    ) -> List[Dict[str, Any]]:
        """向量检索 - 修复版本，降低阈值并改进匹配逻辑"""
        # 生成问题的嵌入向量
        question_embedding = self.embedding_model.encode([question], convert_to_tensor=False)
        
        # 在向量数据库中搜索，获取更多候选结果
        results = self.collection.query(
            query_embeddings=question_embedding.tolist(),
            n_results=min(top_k * 10, 500),  # 获取更多候选结果
            include=["documents", "metadatas", "distances"]
        )
        
        if not results["documents"] or not results["documents"][0]:
            logger.warning("No results found in vector database")
            return []
        
        # 处理结果 - 增加智能重排序
        retrieved_banks = []
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]
        
        logger.info(f"RAG: Found {len(documents)} potential matches from vector search")
        
        # 第一步：基于向量相似度的初步筛选（降低阈值）
        candidates = []
        for i, (doc, metadata, distance) in enumerate(zip(documents, metadatas, distances)):
            # 计算相似度分数 (距离越小，相似度越高)
            similarity_score = max(0.0, 1.0 / (1.0 + distance))
            
            logger.info(f"RAG: Vector Candidate {i+1}: {metadata['bank_name']} | Distance: {distance:.3f} | Similarity: {similarity_score:.3f}")
            
            # 大幅降低相似度阈值，让更多结果通过
            effective_threshold = min(similarity_threshold, 0.05)  # 最低阈值0.05
            if similarity_score >= effective_threshold:
                candidates.append({
                    "bank_name": metadata["bank_name"],
                    "bank_code": metadata["bank_code"],
                    "clearing_code": metadata["clearing_code"],
                    "similarity_score": similarity_score,
                    "keywords": metadata.get("keywords", "").split(","),
                    "bank_id": metadata["bank_id"],
                    "distance": distance
                })
        
        # 第二步：基于关键词匹配的重排序
        question_lower = question.lower()
        question_keywords = self._extract_question_keywords(question)
        
        logger.info(f"RAG: Extracted question keywords: {question_keywords}")
        
        for candidate in candidates:
            bank_name = candidate["bank_name"]
            bank_name_lower = bank_name.lower()
            
            # 计算关键词匹配分数
            keyword_score = 0
            matched_keywords = []
            
            # 1. 直接字符串匹配检查（最重要）
            for kw in question_keywords:
                if len(kw) >= 2 and kw.lower() in bank_name_lower:
                    if len(kw) >= 4:
                        keyword_score += 3.0  # 长关键词高分
                    elif len(kw) == 3:
                        keyword_score += 2.0  # 中等关键词
                    else:
                        keyword_score += 1.0  # 短关键词
                    matched_keywords.append(kw)
            
            # 2. 银行别名匹配
            bank_keywords = candidate.get("keywords", [])
            for q_kw in question_keywords:
                if q_kw.lower() in [bk.lower() for bk in bank_keywords]:
                    keyword_score += 1.5
                    matched_keywords.append(q_kw)
            
            # 3. 字符重叠度
            common_chars = set(question_lower) & set(bank_name_lower)
            char_overlap_ratio = len(common_chars) / max(len(set(question_lower)), 1)
            keyword_score += char_overlap_ratio * 0.5
            
            # 综合分数：向量相似度 + 关键词匹配分数
            candidate["keyword_score"] = keyword_score
            candidate["matched_keywords"] = matched_keywords
            candidate["final_score"] = candidate["similarity_score"] * 0.3 + keyword_score * 0.7  # 更重视关键词匹配
            
            logger.info(f"RAG: Enhanced scoring for {bank_name[:30]}... | "
                      f"Vector: {candidate['similarity_score']:.3f} | "
                      f"Keyword: {keyword_score:.3f} | "
                      f"Final: {candidate['final_score']:.3f} | "
                      f"Matched: {matched_keywords}")
        
        # 按综合分数排序
        candidates.sort(key=lambda x: x["final_score"], reverse=True)
        retrieved_banks = candidates[:top_k]
        
        return retrieved_banks
    
    async def _optimized_keyword_retrieve(
        self,
        question: str,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        优化的关键词检索 - 减少关键词数量，提高性能
        
        Args:
            question: 用户问题
            top_k: 返回结果数量
        
        Returns:
            匹配的银行记录列表
        """
        try:
            logger.info(f"RAG: Starting optimized keyword retrieval for: {question}")
            
            # 提取核心关键词（减少数量）
            core_keywords = self._extract_core_keywords(question)
            logger.info(f"RAG: Core keywords: {core_keywords}")
            
            if not core_keywords:
                return []
            
            # 获取所有数据进行关键词匹配
            all_results = self.collection.get(include=["metadatas"])
            
            if not all_results["metadatas"]:
                logger.warning("No data found in vector database")
                return []
            
            matches = []
            
            for metadata in all_results["metadatas"]:
                bank_name = metadata["bank_name"]
                bank_name_lower = bank_name.lower()
                
                # 计算关键词匹配分数
                keyword_score = 0
                matched_keywords = []
                
                for keyword in core_keywords:
                    if len(keyword) >= 2:  # 只考虑长度>=2的关键词
                        keyword_lower = keyword.lower()
                        
                        # 直接字符串匹配
                        if keyword_lower in bank_name_lower:
                            # 根据关键词长度和重要性给分
                            if len(keyword) >= 4:
                                keyword_score += 3.0  # 长关键词高分
                            elif len(keyword) == 3:
                                keyword_score += 2.0  # 中等关键词
                            else:
                                keyword_score += 1.0  # 短关键词
                            
                            matched_keywords.append(keyword)
                
                # 只保留有匹配的结果
                if keyword_score > 0:
                    matches.append({
                        "bank_name": metadata["bank_name"],
                        "bank_code": metadata["bank_code"],
                        "clearing_code": metadata.get("clearing_code", ""),
                        "similarity_score": 0.8,  # 关键词匹配给固定相似度
                        "keyword_score": keyword_score,
                        "final_score": keyword_score,
                        "matched_keywords": matched_keywords,
                        "bank_id": metadata["bank_id"]
                    })
            
            # 按分数排序
            matches.sort(key=lambda x: x["final_score"], reverse=True)
            result = matches[:top_k * 2]  # 返回更多结果用于合并
            
            logger.info(f"RAG: Optimized keyword search found {len(result)} matches")
            
            return result
            
        except Exception as e:
            logger.error(f"Optimized keyword retrieval failed: {e}")
            return []
    
    def _extract_core_keywords(self, question: str) -> List[str]:
        """
        提取核心关键词 - 优化版本，减少关键词数量
        
        Args:
            question: 用户问题
        
        Returns:
            核心关键词列表
        """
        import re
        
        keywords = []
        
        # 1. 提取银行名称（完整匹配优先）
        bank_patterns = [
            r'(中国工商银行|工商银行)',
            r'(中国农业银行|农业银行)',
            r'(中国银行)',
            r'(中国建设银行|建设银行)',
            r'(交通银行)',
            r'(招商银行)',
            r'(浦发银行|上海浦东发展银行)',
            r'(中信银行)',
            r'(光大银行|中国光大银行)',
            r'(华夏银行)',
            r'(民生银行|中国民生银行)',
            r'(广发银行)',
            r'(平安银行)',
            r'(兴业银行)',
            r'(邮储银行|邮政储蓄银行)',
        ]
        
        for pattern in bank_patterns:
            matches = re.findall(pattern, question)
            for match in matches:
                if isinstance(match, tuple):
                    keywords.extend([m for m in match if m and len(m) >= 3])
                else:
                    if len(match) >= 3:
                        keywords.append(match)
        
        # 2. 提取地理位置（主要城市）
        location_patterns = [
            r'(北京|上海|天津|重庆)',
            r'(广州|深圳|厦门|青岛|大连|宁波|苏州|杭州|南京|武汉|成都|西安)',
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, question)
            keywords.extend(matches)
        
        # 3. 提取支行类型（重要关键词）
        branch_patterns = [
            r'([^，。！？\s]{2,8}支行)',
            r'([^，。！？\s]{2,8}分行)',
            r'(营业部|营业厅|分理处)'
        ]
        
        for pattern in branch_patterns:
            matches = re.findall(pattern, question)
            keywords.extend(matches)
        
        # 4. 提取重要的4字以上词组
        long_words = re.findall(r'[^，。！？\s]{4,8}', question)
        for word in long_words:
            if not re.search(r'[的是在有什么多少哪里怎么样]', word):
                keywords.append(word)
        
        # 去重并过滤，限制关键词数量
        unique_keywords = []
        seen = set()
        for kw in keywords:
            kw = kw.strip()
            if kw and len(kw) >= 2 and kw not in seen and len(unique_keywords) < 10:  # 限制最多10个关键词
                seen.add(kw)
                unique_keywords.append(kw)
        
        return unique_keywords
    
    def _rerank_combined_results(
        self,
        question: str,
        combined_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """重新排序合并后的结果"""
        question_lower = question.lower()
        
        for result in combined_results:
            bank_name = result["bank_name"]
            bank_name_lower = bank_name.lower()
            
            # 重新计算综合分数
            base_score = result.get("final_score", 0)
            
            # 精确匹配加分
            exact_match_bonus = 0
            if result.get("retrieval_method") == "keyword":
                # 关键词检索结果通常更精确
                exact_match_bonus += 0.5
            
            # 完整匹配检查
            question_words = set(question_lower.split())
            bank_words = set(bank_name_lower.split())
            word_overlap = len(question_words & bank_words) / max(len(question_words), 1)
            exact_match_bonus += word_overlap * 0.3
            
            result["final_score"] = base_score + exact_match_bonus
        
        # 按最终分数排序
        combined_results.sort(key=lambda x: x["final_score"], reverse=True)
        return combined_results
    
    async def load_from_file(self, file_path: str, force_rebuild: bool = False) -> bool:
        """
        从文件直接加载银行数据到向量数据库
        
        Args:
            file_path: 银行数据文件路径
            force_rebuild: 是否强制重建数据库
        
        Returns:
            是否成功加载
        """
        try:
            logger.info(f"从文件加载银行数据到RAG: {file_path}")
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return False
            
            # 如果强制重建，清空集合
            if force_rebuild:
                collection_count = self.collection.count()
                if collection_count > 0:
                    self.chroma_client.delete_collection(self.collection_name)
                    self.collection = self.chroma_client.create_collection(
                        name=self.collection_name,
                        metadata={"description": "Bank codes and information for RAG retrieval"}
                    )
                    logger.info("清空现有向量数据库")
            
            # 读取文件数据
            bank_records = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 按竖线分隔，取第一列和第二列
                    parts = line.split('|')
                    if len(parts) >= 2:
                        bank_code = parts[0].strip()
                        bank_name = parts[1].strip()
                        
                        # 跳过空值
                        if bank_code and bank_name:
                            bank_records.append({
                                'id': line_num,
                                'bank_code': bank_code,
                                'bank_name': bank_name,
                                'clearing_code': '',  # 文件中没有清算代码
                                'dataset_id': 0
                            })
            
            logger.info(f"从文件读取到 {len(bank_records)} 条银行记录")
            
            if not bank_records:
                logger.warning("文件中没有有效的银行记录")
                return False
            
            # 批量处理向量化
            batch_size = 100
            total_batches = (len(bank_records) + batch_size - 1) // batch_size
            
            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, len(bank_records))
                batch_records = bank_records[start_idx:end_idx]
                
                logger.info(f"处理批次 {batch_idx + 1}/{total_batches} ({len(batch_records)} 条记录)")
                
                # 准备批量数据
                documents = []
                metadatas = []
                ids = []
                
                for record in batch_records:
                    # 创建文档文本
                    doc_text = f"银行名称: {record['bank_name']} | 联行号: {record['bank_code']}"
                    documents.append(doc_text)
                    
                    # 创建元数据
                    keywords = self._extract_bank_keywords(record['bank_name'])
                    metadata = {
                        "bank_id": record['id'],
                        "bank_name": record['bank_name'],
                        "bank_code": record['bank_code'],
                        "clearing_code": record['clearing_code'],
                        "keywords": ",".join(keywords),
                        "dataset_id": record['dataset_id']
                    }
                    metadatas.append(metadata)
                    
                    # 创建唯一ID
                    ids.append(f"file_bank_{record['id']}")
                
                # 生成嵌入向量
                embeddings = self.embedding_model.encode(documents, convert_to_tensor=False)
                embeddings_list = embeddings.tolist()
                
                # 添加到向量数据库
                self.collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids,
                    embeddings=embeddings_list
                )
                
                logger.info(f"已添加批次 {batch_idx + 1}/{total_batches} 到向量数据库")
            
            final_count = self.collection.count()
            logger.info(f"从文件加载完成，向量数据库现有 {final_count} 条记录")
            return True
            
        except Exception as e:
            logger.error(f"从文件加载银行数据失败: {e}")
            return False
    
    async def update_vector_db(self) -> bool:
        """
        更新向量数据库（增量更新）
        
        Returns:
            是否成功更新
        """
        try:
            logger.info("Checking for vector database updates...")
            
            # 获取向量数据库中的所有银行ID
            all_results = self.collection.get(include=["metadatas"])
            existing_bank_ids = set()
            
            if all_results["metadatas"]:
                existing_bank_ids = {
                    int(metadata["bank_id"]) 
                    for metadata in all_results["metadatas"]
                }
            
            # 获取数据库中的所有有效银行记录
            current_bank_records = self.db.query(BankCode).filter(BankCode.is_valid == True).all()
            current_bank_ids = {record.id for record in current_bank_records}
            
            # 找出需要添加的新记录
            new_bank_ids = current_bank_ids - existing_bank_ids
            # 找出需要删除的记录
            deleted_bank_ids = existing_bank_ids - current_bank_ids
            
            logger.info(f"Found {len(new_bank_ids)} new banks, {len(deleted_bank_ids)} deleted banks")
            
            # 删除已不存在的记录
            if deleted_bank_ids:
                delete_ids = [f"bank_{bank_id}" for bank_id in deleted_bank_ids]
                self.collection.delete(ids=delete_ids)
                logger.info(f"Deleted {len(delete_ids)} records from vector database")
            
            # 添加新记录
            if new_bank_ids:
                new_records = [
                    record for record in current_bank_records 
                    if record.id in new_bank_ids
                ]
                
                # 批量处理新记录
                documents = []
                metadatas = []
                ids = []
                
                for record in new_records:
                    doc_text = self._create_document_text(record)
                    documents.append(doc_text)
                    
                    keywords = self._extract_bank_keywords(record.bank_name)
                    metadata = {
                        "bank_id": record.id,
                        "bank_name": record.bank_name,
                        "bank_code": record.bank_code,
                        "clearing_code": record.clearing_code or "",
                        "keywords": ",".join(keywords),
                        "dataset_id": record.dataset_id
                    }
                    metadatas.append(metadata)
                    ids.append(f"bank_{record.id}")
                
                # 生成嵌入向量
                embeddings = self.embedding_model.encode(documents, convert_to_tensor=False)
                embeddings_list = embeddings.tolist()
                
                # 添加到向量数据库
                self.collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids,
                    embeddings=embeddings_list
                )
                
                logger.info(f"Added {len(new_records)} new records to vector database")
            
            if not new_bank_ids and not deleted_bank_ids:
                logger.info("Vector database is already up to date")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update vector database: {e}")
            return False
    
    async def hybrid_retrieve(
        self,
        question: str,
        top_k: int = 5,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        混合检索：结合向量检索和关键词检索
        
        Args:
            question: 用户问题
            top_k: 返回结果数量
            vector_weight: 向量检索权重
            keyword_weight: 关键词检索权重
        
        Returns:
            混合检索结果
        """
        try:
            logger.info(f"RAG: Starting hybrid retrieval for question: {question[:50]}...")
            
            # 1. 向量检索
            vector_results = await self.retrieve_relevant_banks(
                question, 
                top_k=top_k * 2,  # 获取更多结果用于混合
                similarity_threshold=0.5  # 降低阈值以获取更多候选
            )
            
            # 2. 关键词检索（从原有数据库）
            # 这里可以调用原有的关键词检索逻辑
            # 为了简化，我们直接使用向量检索结果
            
            # 3. 结果融合和重排序
            final_results = []
            seen_banks = set()
            
            for result in vector_results:
                if result["bank_code"] not in seen_banks:
                    # 计算混合分数
                    hybrid_score = (
                        result["similarity_score"] * vector_weight +
                        0.8 * keyword_weight  # 假设关键词匹配度为0.8
                    )
                    
                    result["hybrid_score"] = hybrid_score
                    final_results.append(result)
                    seen_banks.add(result["bank_code"])
            
            # 按混合分数排序
            final_results.sort(key=lambda x: x["hybrid_score"], reverse=True)
            final_results = final_results[:top_k]
            
            logger.info(f"RAG: Hybrid retrieval returning {len(final_results)} results")
            
            return final_results
            
        except Exception as e:
            logger.error(f"Hybrid retrieval failed: {e}")
            return await self.retrieve_relevant_banks(question, top_k)  # 降级到纯向量检索
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        获取向量数据库统计信息
        
        Returns:
            数据库统计信息
        """
        try:
            collection_count = self.collection.count()
            db_count = self.db.query(BankCode).filter(BankCode.is_valid == True).count()
            
            # 使用固定的嵌入模型维度，避免网络请求
            embedding_dimension = 384  # paraphrase-multilingual-MiniLM-L12-v2的固定维度
            
            return {
                "vector_db_count": collection_count,
                "source_db_count": db_count,
                "is_synced": collection_count == db_count,
                "collection_name": self.collection_name,
                "embedding_model": embedding_dimension,
                "vector_db_path": str(self.vector_db_path)
            }
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {"error": str(e)}