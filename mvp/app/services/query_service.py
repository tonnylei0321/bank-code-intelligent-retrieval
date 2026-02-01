"""
Query Service - 查询推理服务

本服务负责使用训练好的模型进行实时推理，处理用户的银行联行号查询请求。

主要功能：
    - 模型加载：启动时加载训练好的模型（LoRA权重）
    - 答案生成：使用模型为用户查询生成答案
    - 信息提取：从生成的答案中提取银行联行号信息
    - 置信度计算：评估答案的可信度
    - 查询日志：记录所有查询到数据库
    - 批量查询：支持批量处理多个查询
    - 历史记录：查询历史记录管理

技术栈：
    - transformers: HuggingFace模型推理
    - peft: LoRA权重加载
    - torch: PyTorch推理引擎
    - SQLAlchemy: 数据库操作

使用示例：
    >>> from app.services.query_service import QueryService
    >>> service = QueryService(db_session, model_path="models/job_1/final_model")
    >>> 
    >>> # 单个查询
    >>> response = service.query("工商银行的联行号是多少？")
    >>> print(response["answer"])
    >>> 
    >>> # 批量查询
    >>> questions = ["工商银行的联行号？", "建设银行的联行号？"]
    >>> responses = service.batch_query(questions)
    >>> 
    >>> # 查询历史
    >>> history = service.get_query_history(user_id=1, limit=10)

推理流程：
    1. 接收用户查询
    2. 格式化为模型输入（添加提示词）
    3. 使用模型生成答案
    4. 从答案中提取银行联行号
    5. 在数据库中查找完整信息
    6. 计算置信度分数
    7. 记录查询日志
    8. 返回结构化响应
"""
import os
import re
import time
import hashlib
from functools import lru_cache
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    GenerationConfig
)
from peft import PeftModel
from sqlalchemy.orm import Session
from loguru import logger

from app.models.bank_code import BankCode
from app.models.training_job import TrainingJob
from app.models.query_log import QueryLog


class QueryServiceError(Exception):
    """
    查询服务异常基类
    
    用于标识查询服务中的所有错误，包括：
    - 模型加载失败
    - 答案生成失败
    - 查询处理失败
    """
    pass


class QueryService:
    """
    查询推理服务 - 用于模型推理和查询处理
    
    本类负责加载训练好的模型并处理用户的实时查询请求。
    支持单个查询和批量查询，自动记录查询日志。
    
    核心功能：
        1. 模型管理：
           - 加载基础模型和LoRA权重
           - 自动检测GPU/CPU设备
           - 设置为评估模式
        
        2. 答案生成：
           - 格式化用户查询为模型输入
           - 使用采样策略生成答案
           - 从生成文本中提取答案部分
        
        3. 信息提取：
           - 使用正则表达式提取12位联行号
           - 在数据库中查找完整的银行信息
           - 支持按bank_code和clearing_code查找
        
        4. 置信度评估：
           - 基于启发式规则计算置信度
           - 考虑是否找到联行号
           - 考虑答案中的关键词
        
        5. 查询日志：
           - 记录所有查询到数据库
           - 包含问题、答案、置信度、响应时间
           - 支持按用户ID过滤
        
        6. 历史管理：
           - 查询历史记录
           - 支持分页
           - 支持按用户过滤
    
    属性：
        db (Session): 数据库会话对象
        base_model_name (str): 基础模型名称
        model_path (str): LoRA权重路径
        model: 加载的模型对象
        tokenizer: 分词器对象
        device (str): 推理设备（"cuda"或"cpu"）
        model_version (str): 模型版本标识
    
    使用流程：
        1. 创建QueryService实例（可选提供model_path）
        2. 如果未在初始化时加载，调用load_model()
        3. 调用query()处理单个查询
        4. 或调用batch_query()处理批量查询
        5. 使用get_query_history()查看历史记录
    """
    
    def __init__(
        self,
        db: Session,
        model_path: Optional[str] = None,
        base_model_name: str = "Qwen/Qwen2.5-0.5B"
    ):
        """
        Initialize Query Service
        
        Args:
            db: Database session
            model_path: Path to trained model weights (LoRA adapters)
            base_model_name: Base model name
        """
        self.db = db
        self.base_model_name = base_model_name
        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        
        # 检查设备可用性（优先使用GPU）
        if torch.cuda.is_available():
            self.device = "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            self.device = "mps"
        else:
            self.device = "cpu"
        
        self.model_version = None
        
        # 性能优化：缓存系统
        self.query_cache = {}
        self.cache_ttl = 3600  # 1小时缓存
        self.max_cache_size = 1000
        self._cache_hits = 0
        self._total_queries = 0
        
        # 初始化RAG服务
        from app.services.rag_service import RAGService
        self.rag_service = RAGService(db)
        
        logger.info(f"QueryService initialized - Device: {self.device}")
        
        # Load model if path provided
        if model_path:
            self.load_model(model_path)
    
    def _get_cache_key(self, question: str) -> str:
        """生成缓存键"""
        normalized = question.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _get_cached_result(self, question: str) -> Optional[Dict]:
        """获取缓存的查询结果"""
        cache_key = self._get_cache_key(question)
        
        if cache_key in self.query_cache:
            result, timestamp = self.query_cache[cache_key]
            
            # 检查缓存是否过期
            if time.time() - timestamp < self.cache_ttl:
                self._cache_hits += 1
                logger.info(f"Cache hit for question: {question[:30]}...")
                return result
            else:
                # 删除过期缓存
                del self.query_cache[cache_key]
        
        return None
    
    def _check_memory_usage(self) -> Dict[str, Any]:
        """检查当前内存使用情况"""
        memory_info = {
            "device": self.device,
            "available": True
        }
        
        try:
            if self.device == "mps":
                # MPS 内存信息
                if torch.backends.mps.is_available():
                    # MPS 没有直接的内存查询API，但我们可以记录状态
                    memory_info["backend"] = "MPS"
                    memory_info["note"] = "MPS memory tracking limited"
            elif self.device == "cuda":
                # CUDA 内存信息
                memory_info["allocated_gb"] = torch.cuda.memory_allocated() / 1024**3
                memory_info["reserved_gb"] = torch.cuda.memory_reserved() / 1024**3
                memory_info["max_allocated_gb"] = torch.cuda.max_memory_allocated() / 1024**3
            
            logger.debug(f"Memory usage: {memory_info}")
        except Exception as e:
            logger.warning(f"Could not check memory usage: {e}")
        
        return memory_info

    
    def _cache_result(self, question: str, result: Dict):
        """缓存查询结果"""
        # 如果缓存已满，删除最旧的条目
        if len(self.query_cache) >= self.max_cache_size:
            oldest_key = min(self.query_cache.keys(), 
                           key=lambda k: self.query_cache[k][1])
            del self.query_cache[oldest_key]
            logger.info("Cache full, removed oldest entry")
        
        cache_key = self._get_cache_key(question)
        self.query_cache[cache_key] = (result, time.time())
        logger.info(f"Cached result for question: {question[:30]}...")
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        hit_rate = self._cache_hits / max(self._total_queries, 1)
        return {
            "cache_size": len(self.query_cache),
            "max_cache_size": self.max_cache_size,
            "cache_ttl": self.cache_ttl,
            "hit_rate": f"{hit_rate:.2%}",
            "total_queries": self._total_queries,
            "cache_hits": self._cache_hits
        }
    
    def load_model(self, model_path: str) -> None:
        """
        Load trained model and tokenizer
        
        Args:
            model_path: Path to trained model weights
        
        Raises:
            QueryServiceError: If model loading fails
        """
        try:
            logger.info(f"Loading model from: {model_path}")
            
            # 清理内存，为新模型腾出空间
            if self.model is not None:
                logger.info("Unloading previous model to free memory")
                del self.model
                del self.tokenizer
                self.model = None
                self.tokenizer = None
            
            # 强制垃圾回收和清理GPU缓存
            import gc
            gc.collect()
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
                logger.info("MPS cache cleared")
            elif torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.info("CUDA cache cleared")
            
            # Determine the base model name from the training job
            # Extract job_id from model_path (e.g., "models/job_20/final_model" -> 20)
            base_model_name = self.base_model_name  # Default
            
            try:
                import re
                match = re.search(r'job_(\d+)', model_path)
                if match:
                    job_id = int(match.group(1))
                    # Query the training job to get the actual model name
                    from app.models.training_job import TrainingJob
                    job = self.db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
                    if job and job.model_name:
                        base_model_name = job.model_name
                        logger.info(f"Using base model from training job: {base_model_name}")
            except Exception as e:
                logger.warning(f"Could not determine base model from training job, using default: {e}")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                base_model_name,
                trust_remote_code=True,
                padding_side="right"
            )
            
            # Set pad token if not exists
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Load base model
            # 根据设备选择合适的数据类型和配置
            if self.device == "cuda":
                torch_dtype = torch.float16
                device_map = "auto"
            elif self.device == "mps":
                torch_dtype = torch.float32  # MPS对float16支持有限
                device_map = None
            else:
                torch_dtype = torch.float32
                device_map = None
            
            base_model = AutoModelForCausalLM.from_pretrained(
                base_model_name,
                trust_remote_code=True,
                torch_dtype=torch_dtype,
                device_map=device_map
            )
            
            # 如果是MPS，手动移动模型到MPS设备
            if self.device == "mps":
                base_model = base_model.to(self.device)
            
            # Load LoRA adapters
            # MPS设备需要特殊处理：先加载到CPU，再移动到MPS
            if self.device == "mps":
                # 在CPU上加载LoRA权重
                self.model = PeftModel.from_pretrained(
                    base_model,
                    model_path,
                    torch_dtype=torch.float32
                )
                # 手动移动到MPS设备
                self.model = self.model.to("mps")
                logger.info("LoRA model loaded on MPS device")
            else:
                # CUDA或CPU直接加载
                lora_dtype = torch.float16 if self.device == "cuda" else torch.float32
                self.model = PeftModel.from_pretrained(
                    base_model,
                    model_path,
                    torch_dtype=lora_dtype
                )
            
            # Set to evaluation mode
            self.model.eval()
            
            # Extract model version from path
            self.model_version = Path(model_path).name
            
            logger.info(f"Model loaded successfully - Base: {base_model_name}, Version: {self.model_version}")
        
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            # 清理内存
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
            elif torch.cuda.is_available():
                torch.cuda.empty_cache()
            import gc
            gc.collect()
            raise QueryServiceError(f"Model loading failed: {e}")
    
    def generate_answer(
        self,
        question: str,
        max_new_tokens: int = 256,
        temperature: float = 0.1,  # 降低温度减少随机性和幻觉
        top_p: float = 0.8,         # 降低top_p使生成更保守
        context: Optional[str] = None  # RAG context
    ) -> str:
        """
        Generate answer for a question using the model
        
        Args:
            question: User's question
            max_new_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
        
        Returns:
            Generated answer
        
        Raises:
            QueryServiceError: If generation fails
        """
        if self.model is None or self.tokenizer is None:
            raise QueryServiceError("Model not loaded. Call load_model() first.")
        
        try:
            # Format prompt - 使用与训练时相同的格式
            # If context provided (RAG mode), include it in the prompt
            if context:
                prompt = f"Reference Information:\n{context}\n\nQuestion: {question}\nAnswer:"
            else:
                prompt = f"Question: {question}\nAnswer:"
            
            # Log the prompt for debugging
            logger.info(f"RAG Prompt being sent to model: {prompt[:500]}...")
            
            # Tokenize
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            )
            
            # Move to device (支持CUDA和MPS)
            if self.device in ["cuda", "mps"]:
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=True,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode
            full_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract answer (remove prompt) - 使用与训练时相同的分隔符
            if "Answer:" in full_text:
                answer = full_text.split("Answer:")[-1].strip()
            else:
                # 如果没有找到Answer:，返回整个生成的文本
                answer = full_text.strip()
            
            return answer
        
        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            raise QueryServiceError(f"Answer generation failed: {e}")
    
    @lru_cache(maxsize=500)
    def format_structured_answer(
        self,
        question: str,
        matched_records: List[Dict[str, str]],
        confidence: float,
        response_time: float
    ) -> str:
        """
        格式化结构化答案输出 - 新增功能
        
        优化内容：
        - 根据查询类型提供不同的答案格式
        - 添加置信度和响应时间信息
        - 提供用户友好的错误提示和建议
        
        Args:
            question: 原始问题
            matched_records: 匹配的银行记录
            confidence: 置信度分数
            response_time: 响应时间（毫秒）
            
        Returns:
            结构化的答案字符串
        """
        try:
            # 如果没有匹配记录
            if not matched_records:
                return self._format_no_match_answer(question)
            
            # 单个匹配记录
            if len(matched_records) == 1:
                return self._format_single_match_answer(matched_records[0], confidence)
            
            # 多个匹配记录
            return self._format_multiple_match_answer(matched_records, confidence)
            
        except Exception as e:
            logger.error(f"答案格式化失败：{e}")
            return "抱歉，答案格式化时出现错误。"
    
    def _format_no_match_answer(self, question: str) -> str:
        """
        格式化无匹配结果的答案
        
        Args:
            question: 原始问题
            
        Returns:
            无匹配结果的友好提示
        """
        suggestions = []
        
        # 分析问题并提供建议
        if len(question) < 3:
            suggestions.append("• 请提供更详细的银行名称或地区信息")
        
        if not any(bank in question for bank in ["银行", "行"]):
            suggestions.append("• 请确认查询的是银行机构")
        
        if not any(char.isdigit() for char in question):
            suggestions.append("• 如果您知道部分联行号，可以包含在查询中")
        
        base_answer = "抱歉，未找到匹配的银行信息。"
        
        if suggestions:
            base_answer += "\n\n建议：\n" + "\n".join(suggestions)
        
        base_answer += "\n\n您也可以尝试：\n• 使用银行全称（如：中国工商银行股份有限公司北京西单支行）\n• 包含具体地区信息（如：北京工商银行）"
        
        return base_answer
    
    def _format_single_match_answer(self, record: Dict[str, str], confidence: float) -> str:
        """
        格式化单个匹配结果的答案
        
        Args:
            record: 银行记录
            confidence: 置信度
            
        Returns:
            格式化的单个匹配答案
        """
        answer = f"🏦 {record['bank_name']}\n📋 联行号：{record['bank_code']}"
        
        if record.get('clearing_code'):
            answer += f"\n🔢 清算代码：{record['clearing_code']}"
        
        # 根据置信度添加不同的提示
        if confidence >= 0.9:
            answer += f"\n✅ 匹配度：{confidence:.1%}（高度匹配）"
        elif confidence >= 0.7:
            answer += f"\n⚠️ 匹配度：{confidence:.1%}（较好匹配）"
        else:
            answer += f"\n❓ 匹配度：{confidence:.1%}（请确认是否为您要查找的银行）"
        
        return answer
    
    def _format_multiple_match_answer(self, records: List[Dict[str, str]], confidence: float) -> str:
        """
        格式化多个匹配结果的答案
        
        Args:
            records: 银行记录列表
            confidence: 整体置信度
            
        Returns:
            格式化的多个匹配答案
        """
        answer = f"找到 {len(records)} 个可能的匹配结果：\n\n"
        
        for i, record in enumerate(records[:5], 1):  # 最多显示5个结果
            answer += f"{i}. 🏦 {record['bank_name']}\n"
            answer += f"   📋 联行号：{record['bank_code']}\n"
            if record.get('clearing_code'):
                answer += f"   🔢 清算代码：{record['clearing_code']}\n"
            answer += "\n"
        
        if len(records) > 5:
            answer += f"... 还有 {len(records) - 5} 个结果未显示\n\n"
        
        answer += "💡 提示：请选择最符合您需求的银行，或提供更具体的信息以获得精确匹配。"
        
        return answer
        """
        使用小模型进行银行实体提取
        
        架构说明：
        1. LLM仅用于训练数据生成
        2. 小模型用于语义和词义解析（NER任务）
        3. 小模型用于最终答案汇总
        
        Args:
            question: 用户问题
            
        Returns:
            Dict包含提取的实体：bank_name, location, branch_name等
        """
        try:
            logger.info(f"Using small model for entity extraction: {question}")
            
            # TODO: 未来可以集成专门的NER小模型（如BERT-NER）
            # 现阶段使用规则提取，但架构已为小模型预留接口
            
            # 使用规则提取，模拟小模型NER的效果
            fallback_keywords = []
            
            # 银行名称实体识别
            bank_entities = {
                "华夏银行": ["华夏银行"],
                "中国农业银行": ["中国农业银行", "农业银行", "农行"],
                "中国工商银行": ["中国工商银行", "工商银行", "工行"],
                "中国建设银行": ["中国建设银行", "建设银行", "建行"],
                "中国银行": ["中国银行", "中行"],
                "交通银行": ["交通银行", "交行"],
                "招商银行": ["招商银行", "招行"],
                "中信银行": ["中信银行"],
                "光大银行": ["光大银行"],
                "民生银行": ["民生银行"],
                "兴业银行": ["兴业银行"],
                "浦发银行": ["浦发银行", "上海浦东发展银行"],
                "平安银行": ["平安银行"],
                "邮储银行": ["邮储银行", "邮政储蓄银行"],
                "广发银行": ["广发银行"],
                "渤海银行": ["渤海银行"],
                "恒丰银行": ["恒丰银行"],
                "浙商银行": ["浙商银行"]
            }
            
            found_bank = None
            for bank_name, aliases in bank_entities.items():
                for alias in aliases:
                    if alias in question:
                        fallback_keywords.append(bank_name)
                        if alias != bank_name:  # 添加别名用于搜索
                            fallback_keywords.append(alias)
                        found_bank = bank_name
                        break
                if found_bank:
                    break
            
            # 地理位置实体识别
            import re
            location_patterns = [
                # 直辖市
                r'(北京|上海|天津|重庆)',
                # 省会城市和重要城市
                r'(厦门|深圳|青岛|大连|宁波|苏州|无锡|常州|南京|杭州|温州|嘉兴|湖州|绍兴|金华|衢州|舟山|台州|丽水)',
                r'(合肥|芜湖|蚌埠|淮南|马鞍山|淮北|铜陵|安庆|黄山|滁州|阜阳|宿州|六安|亳州|池州|宣城)',
                r'(福州|莆田|三明|泉州|漳州|南平|龙岩|宁德)',
                r'(南昌|景德镇|萍乡|九江|新余|鹰潭|赣州|吉安|宜春|抚州|上饶)',
                r'(济南|淄博|枣庄|东营|烟台|潍坊|济宁|泰安|威海|日照|莱芜|临沂|德州|聊城|滨州|菏泽)',
                r'(郑州|开封|洛阳|平顶山|安阳|鹤壁|新乡|焦作|濮阳|许昌|漯河|三门峡|南阳|商丘|信阳|周口|驻马店)',
                r'(武汉|黄石|十堰|宜昌|襄阳|鄂州|荆门|孝感|荆州|黄冈|咸宁|随州|恩施)',
                r'(长沙|株洲|湘潭|衡阳|邵阳|岳阳|常德|张家界|益阳|郴州|永州|怀化|娄底)',
                r'(广州|韶关|珠海|汕头|佛山|江门|湛江|茂名|肇庆|惠州|梅州|汕尾|河源|阳江|清远|东莞|中山|潮州|揭阳|云浮)',
                r'(南宁|柳州|桂林|梧州|北海|防城港|钦州|贵港|玉林|百色|贺州|河池|来宾|崇左)',
                r'(海口|三亚|三沙|儋州)',
                r'(成都|自贡|攀枝花|泸州|德阳|绵阳|广元|遂宁|内江|乐山|南充|眉山|宜宾|广安|达州|雅安|巴中|资阳|江油)',
                r'(贵阳|六盘水|遵义|安顺|毕节|铜仁)',
                r'(昆明|曲靖|玉溪|保山|昭通|丽江|普洱|临沧)',
                r'(拉萨|昌都|山南|日喀则|那曲|阿里|林芝)',
                r'(西安|铜川|宝鸡|咸阳|渭南|延安|汉中|榆林|安康|商洛)',
                r'(兰州|嘉峪关|金昌|白银|天水|武威|张掖|平凉|酒泉|庆阳|定西|陇南)',
                r'(西宁|海东)',
                r'(银川|石嘴山|吴忠|固原|中卫)',
                r'(乌鲁木齐|克拉玛依|吐鲁番|哈密)',
                # 县级市和特殊地名
                r'([^市县区镇]{2,8}[市县区镇])'
            ]
            
            found_location = None
            for pattern in location_patterns:
                location_match = re.search(pattern, question)
                if location_match:
                    found_location = location_match.group(1)
                    fallback_keywords.append(found_location)
                    break
            
            # 支行名称实体识别
            branch_patterns = [
                r'([^银行]{1,10}支行)',
                r'([^银行]{1,10}分行)',
            ]
            
            found_branch = None
            for pattern in branch_patterns:
                branch_match = re.search(pattern, question)
                if branch_match:
                    branch_name = branch_match.group(1)
                    if '支行' in branch_name:
                        found_branch = branch_name.replace('支行', '')
                        fallback_keywords.append(found_branch)
                        fallback_keywords.append('支行')
                    elif '分行' in branch_name:
                        found_branch = branch_name.replace('分行', '')
                        fallback_keywords.append(found_branch)
                        fallback_keywords.append('分行')
                    else:
                        found_branch = branch_name
                        fallback_keywords.append(found_branch)
                    break
            
            # 构建结果
            result = {
                "bank_name": found_bank or "未知银行",
                "location": found_location or "未知地区", 
                "branch_name": found_branch or "未知支行",
                "keywords": fallback_keywords if fallback_keywords else [question]
            }
            
            logger.info(f"Small model entity extraction result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Small model entity extraction failed: {e}")
            return {"keywords": [question]}

    def generate_answer_with_small_model(
        self,
        question: str,
        rag_results: List[Dict[str, str]],
        max_new_tokens: int = 128,
        temperature: float = 0.1
    ) -> str:
        """
        使用小模型基于RAG结果生成最终答案 - 优化版本
        
        优化内容：
        - 改进智能匹配算法，提升多结果场景下的最佳匹配选择
        - 增强相似度计算，支持更精确的银行名称匹配
        - 优化答案格式化和结构化输出
        - 添加置信度评估和质量控制
        
        Args:
            question: 用户问题
            rag_results: RAG检索结果
            max_new_tokens: 最大生成token数
            temperature: 生成温度
            
        Returns:
            格式化的答案
        """
        try:
            if not rag_results:
                return "抱歉，未找到相关银行信息。请尝试使用更具体的银行名称或地区信息。"
            
            # 如果只有一个结果，进行质量检查后返回
            if len(rag_results) == 1:
                bank = rag_results[0]
                confidence = self._calculate_single_result_confidence(question, bank)
                
                if confidence >= 0.7:
                    return self._format_single_answer(bank, confidence)
                else:
                    # 置信度较低时，提供更多信息
                    return self._format_low_confidence_answer(bank, confidence)
            
            # 多个结果时，使用优化的智能匹配算法
            logger.info(f"优化答案生成：从{len(rag_results)}个结果中选择最佳匹配，问题：{question}")
            
            # 提取问题中的关键信息（增强版本）
            question_entities = self._extract_enhanced_entities(question)
            logger.info(f"增强实体提取结果：{question_entities}")
            
            # 计算每个结果的综合匹配分数
            scored_results = []
            for bank in rag_results:
                match_score = self._calculate_comprehensive_match_score(question, question_entities, bank)
                scored_results.append((bank, match_score))
            
            # 按分数排序并选择最佳匹配
            scored_results.sort(key=lambda x: x[1]['total_score'], reverse=True)
            
            best_match, best_score_info = scored_results[0]
            logger.info(f"最佳匹配选择：{best_match['bank_name']} "
                       f"(总分：{best_score_info['total_score']:.2f}，置信度：{best_score_info['confidence']:.2f})")
            
            # 根据匹配质量决定返回策略
            return self._generate_optimized_answer(question, scored_results, best_score_info)
            
        except Exception as e:
            logger.error(f"优化答案生成失败：{e}")
            return "抱歉，生成答案时出现错误。请稍后重试或联系技术支持。"
    
    def _extract_enhanced_entities(self, question: str) -> Dict[str, Any]:
        """
        增强的实体提取，支持更精确的银行信息识别
        
        Args:
            question: 用户问题
            
        Returns:
            增强的实体信息字典
        """
        import re
        
        entities = {
            'bank_names': [],
            'locations': [],
            'branch_types': [],
            'keywords': [],
            'is_full_name': False,
            'query_type': 'general'
        }
        
        # 检测完整银行名称
        if "股份有限公司" in question and ("支行" in question or "分行" in question):
            entities['is_full_name'] = True
            entities['query_type'] = 'full_name'
            entities['keywords'].append(question.strip())
        
        # 银行名称识别（扩展版本）
        bank_patterns = {
            '中国工商银行': ['工商银行', '工行', 'ICBC', '中国工商'],
            '中国农业银行': ['农业银行', '农行', 'ABC', '中国农业'],
            '中国银行': ['中行', 'BOC', '中银'],
            '中国建设银行': ['建设银行', '建行', 'CCB', '中国建设'],
            '交通银行': ['交行', 'BOCOM', '交通'],
            '招商银行': ['招行', 'CMB', '招商'],
            '浦发银行': ['上海浦东发展银行', 'SPDB', '浦东发展'],
            '中信银行': ['中信', 'CITIC'],
            '光大银行': ['中国光大银行', 'CEB', '光大'],
            '华夏银行': ['华夏', 'HXB'],
            '民生银行': ['中国民生银行', 'CMBC', '民生'],
            '广发银行': ['广发', 'CGB', '广东发展银行'],
            '平安银行': ['平安', 'PAB'],
            '兴业银行': ['兴业', 'CIB'],
            '邮储银行': ['邮政储蓄银行', 'PSBC', '邮储', '邮政银行']
        }
        
        for full_name, aliases in bank_patterns.items():
            if full_name in question:
                entities['bank_names'].append(full_name)
                entities['keywords'].extend([full_name] + aliases)
                break
            else:
                for alias in aliases:
                    if alias in question:
                        entities['bank_names'].append(full_name)
                        entities['keywords'].extend([full_name, alias])
                        break
        
        # 地理位置识别（增强版本）
        location_patterns = [
            # 直辖市和省会
            r'(北京|上海|天津|重庆|广州|深圳|成都|武汉|西安|南京|杭州)',
            # 重要城市
            r'(苏州|青岛|大连|宁波|厦门|无锡|常州|温州|佛山|东莞|中山)',
            # 商业区和地标
            r'(西单|王府井|中关村|国贸|金融街|陆家嘴|外滩|珠江新城|福田|南山)'
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, question)
            entities['locations'].extend(matches)
            entities['keywords'].extend(matches)
        
        # 支行类型识别
        branch_patterns = [
            r'([^银行]{1,15}支行)',
            r'([^银行]{1,15}分行)',
            r'(营业部|营业厅|分理处|储蓄所)'
        ]
        
        for pattern in branch_patterns:
            matches = re.findall(pattern, question)
            entities['branch_types'].extend(matches)
            entities['keywords'].extend(matches)
        
        # 查询类型判断
        if entities['is_full_name']:
            entities['query_type'] = 'full_name'
        elif entities['bank_names'] and entities['locations']:
            entities['query_type'] = 'bank_location'
        elif entities['bank_names']:
            entities['query_type'] = 'bank_only'
        elif entities['locations']:
            entities['query_type'] = 'location_only'
        
        return entities
    
    def _calculate_comprehensive_match_score(
        self, 
        question: str, 
        entities: Dict[str, Any], 
        bank: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        计算综合匹配分数，考虑多个维度
        
        Args:
            question: 原始问题
            entities: 提取的实体信息
            bank: 银行记录
            
        Returns:
            包含详细分数信息的字典
        """
        bank_name = bank['bank_name']
        bank_name_lower = bank_name.lower()
        question_lower = question.lower()
        
        score_info = {
            'exact_match_score': 0,
            'semantic_score': 0,
            'location_score': 0,
            'branch_score': 0,
            'penalty_score': 0,
            'rag_score': 0,
            'total_score': 0,
            'confidence': 0,
            'matched_features': []
        }
        
        # 1. 精确匹配分数（最高权重）
        if entities['is_full_name'] and question.strip() == bank_name:
            score_info['exact_match_score'] = 10000
            score_info['matched_features'].append('完全匹配')
        else:
            # 关键词精确匹配
            for keyword in entities['keywords']:
                if len(keyword) >= 2 and keyword.lower() in bank_name_lower:
                    score_info['exact_match_score'] += len(keyword) * 100
                    score_info['matched_features'].append(f'关键词:{keyword}')
        
        # 2. 语义匹配分数
        for bank_name_entity in entities['bank_names']:
            if bank_name_entity in bank_name:
                score_info['semantic_score'] += 1000
                score_info['matched_features'].append(f'银行匹配:{bank_name_entity}')
        
        # 3. 地理位置匹配分数
        for location in entities['locations']:
            if location in bank_name:
                score_info['location_score'] += 500
                score_info['matched_features'].append(f'地理位置:{location}')
        
        # 4. 支行类型匹配分数
        for branch_type in entities['branch_types']:
            if branch_type in bank_name:
                score_info['branch_score'] += 300
                score_info['matched_features'].append(f'支行类型:{branch_type}')
        
        # 5. 惩罚分数（长度差异过大、无关匹配等）
        length_diff = abs(len(question) - len(bank_name))
        if length_diff > 30:
            score_info['penalty_score'] -= length_diff * 2
        
        # 6. RAG检索分数
        if 'final_score' in bank:
            score_info['rag_score'] = bank['final_score'] * 50
            score_info['matched_features'].append(f'RAG分数:{bank["final_score"]:.3f}')
        
        # 计算总分
        score_info['total_score'] = (
            score_info['exact_match_score'] +
            score_info['semantic_score'] +
            score_info['location_score'] +
            score_info['branch_score'] +
            score_info['penalty_score'] +
            score_info['rag_score']
        )
        
        # 计算置信度
        score_info['confidence'] = min(1.0, max(0.0, score_info['total_score'] / 2000))
        
        return score_info
    
    def _calculate_single_result_confidence(self, question: str, bank: Dict[str, str]) -> float:
        """
        计算单个结果的置信度
        
        Args:
            question: 用户问题
            bank: 银行记录
            
        Returns:
            置信度分数 (0.0-1.0)
        """
        question_lower = question.lower()
        bank_name_lower = bank['bank_name'].lower()
        
        confidence = 0.0
        
        # 完全匹配
        if question.strip() == bank['bank_name']:
            confidence = 1.0
        # 高度相似
        elif question_lower in bank_name_lower or bank_name_lower in question_lower:
            confidence = 0.9
        # 关键词匹配
        else:
            common_chars = set(question_lower) & set(bank_name_lower)
            if len(common_chars) > 0:
                confidence = len(common_chars) / max(len(set(question_lower)), len(set(bank_name_lower)))
        
        # RAG分数加成
        if 'final_score' in bank and bank['final_score'] > 0:
            confidence = min(1.0, confidence + bank['final_score'] * 0.1)
        
        return confidence
    
    def _format_single_answer(self, bank: Dict[str, str], confidence: float) -> str:
        """
        格式化单个结果的答案
        
        Args:
            bank: 银行记录
            confidence: 置信度
            
        Returns:
            格式化的答案
        """
        if confidence >= 0.9:
            return f"{bank['bank_name']}: {bank['bank_code']}"
        else:
            return f"{bank['bank_name']}: {bank['bank_code']} (匹配度: {confidence:.1%})"
    
    def _format_low_confidence_answer(self, bank: Dict[str, str], confidence: float) -> str:
        """
        格式化低置信度答案
        
        Args:
            bank: 银行记录
            confidence: 置信度
            
        Returns:
            格式化的答案
        """
        return (f"找到可能匹配的银行：{bank['bank_name']}: {bank['bank_code']}\n"
                f"匹配度较低 ({confidence:.1%})，请确认是否为您要查找的银行。")
    
    def _generate_optimized_answer(
        self, 
        question: str, 
        scored_results: List[Tuple[Dict[str, str], Dict[str, Any]]], 
        best_score_info: Dict[str, Any]
    ) -> str:
        """
        生成优化的答案
        
        Args:
            question: 原始问题
            scored_results: 评分结果列表
            best_score_info: 最佳匹配的分数信息
            
        Returns:
            优化的答案
        """
        best_match = scored_results[0][0]
        
        # 高置信度：直接返回最佳匹配
        if best_score_info['confidence'] >= 0.8:
            return f"{best_match['bank_name']}: {best_match['bank_code']}"
        
        # 中等置信度：返回最佳匹配并标注置信度
        elif best_score_info['confidence'] >= 0.5:
            return (f"{best_match['bank_name']}: {best_match['bank_code']}\n"
                   f"(匹配度: {best_score_info['confidence']:.1%})")
        
        # 低置信度：返回多个候选结果
        else:
            top_results = scored_results[:min(3, len(scored_results))]
            answer_parts = ["找到以下可能的匹配结果："]
            
            for i, (bank, score_info) in enumerate(top_results):
                confidence_str = f"匹配度: {score_info['confidence']:.1%}"
                answer_parts.append(f"{i+1}. {bank['bank_name']}: {bank['bank_code']} ({confidence_str})")
            
            answer_parts.append("请选择最符合您需求的银行。")
            return "\n".join(answer_parts)

    def retrieve_relevant_banks(self, question: str, top_k: int = 5) -> List[Dict[str, str]]:
        """
        Retrieve relevant bank records from database based on question
        
        This is the "Retrieval" part of RAG (Retrieval-Augmented Generation).
        
        Args:
            question: User's question
            top_k: Number of top results to return
        
        Returns:
            List of relevant bank records with name and code
        """
        try:
            logger.info(f"RAG: Starting retrieval for question: {question[:50]}...")
            
            # 使用小模型提取银行实体
            entities = self.extract_bank_entities_with_small_model(question)
            keywords = entities.get("keywords", [])
            
            logger.info(f"RAG: LLM extracted entities: {entities}")
            logger.info(f"RAG: Using keywords for search: {keywords}")
            
            if not keywords:
                logger.warning("RAG: No keywords extracted")
                return []
            
            # 构建更智能的搜索策略
            results = []
            seen_banks = set()
            
            # 优先搜索组合关键词
            if len(keywords) >= 2:
                for i in range(len(keywords)):
                    for j in range(i+1, len(keywords)):
                        combined_query = f"%{keywords[i]}%{keywords[j]}%"
                        logger.info(f"RAG: Searching with combined pattern: {combined_query}")
                        
                        records = self.db.query(BankCode).filter(
                            BankCode.bank_name.like(combined_query)
                        ).limit(top_k).all()
                        
                        logger.info(f"RAG: Found {len(records)} records for combined pattern")
                        for record in records:
                            if record.bank_name not in seen_banks:
                                results.append({
                                    "bank_name": record.bank_name,
                                    "bank_code": record.bank_code,
                                    "clearing_code": record.clearing_code
                                })
                                seen_banks.add(record.bank_name)
            
            # 如果组合搜索结果不够，使用单个关键词搜索
            if len(results) < top_k:
                for keyword in keywords:
                    if len(keyword) >= 2:  # 只使用2字以上的关键词
                        logger.info(f"RAG: Searching for single keyword: {keyword}")
                        records = self.db.query(BankCode).filter(
                            BankCode.bank_name.contains(keyword)
                        ).limit(top_k).all()
                        
                        logger.info(f"RAG: Found {len(records)} records for keyword '{keyword}'")
                        for record in records:
                            if record.bank_name not in seen_banks and len(results) < top_k:
                                results.append({
                                    "bank_name": record.bank_name,
                                    "bank_code": record.bank_code,
                                    "clearing_code": record.clearing_code
                                })
                                seen_banks.add(record.bank_name)
            
            # 返回结果
            final_results = results[:top_k]
            logger.info(f"RAG: Returning {len(final_results)} results")
            for i, result in enumerate(final_results):
                logger.info(f"RAG: Result {i+1}: {result['bank_name']} -> {result['bank_code']}")
            
            return final_results
        
        except Exception as e:
            logger.error(f"Failed to retrieve relevant banks: {e}")
            return []
    
    def extract_bank_codes(self, answer: str) -> List[Dict[str, str]]:
        """
        Extract bank code information from answer
        
        Args:
            answer: Generated answer text
        
        Returns:
            List of extracted bank code records
        """
        extracted_records = []
        
        # Pattern to match 12-digit bank codes
        code_pattern = r'\b\d{12}\b'
        codes = re.findall(code_pattern, answer)
        
        # Look up codes in database
        for code in codes:
            # Try to find by bank_code
            record = self.db.query(BankCode).filter(
                BankCode.bank_code == code
            ).first()
            
            if record:
                extracted_records.append({
                    "bank_name": record.bank_name,
                    "bank_code": record.bank_code,
                    "clearing_code": record.clearing_code
                })
            else:
                # Try to find by clearing_code
                record = self.db.query(BankCode).filter(
                    BankCode.clearing_code == code
                ).first()
                
                if record:
                    extracted_records.append({
                        "bank_name": record.bank_name,
                        "bank_code": record.bank_code,
                        "clearing_code": record.clearing_code
                    })
        
        return extracted_records
    
    def calculate_confidence(
        self,
        answer: str,
        extracted_records: List[Dict[str, str]]
    ) -> float:
        """
        Calculate confidence score for the answer
        
        Args:
            answer: Generated answer
            extracted_records: Extracted bank code records
        
        Returns:
            Confidence score (0.0-1.0)
        """
        # Simple heuristic-based confidence calculation
        confidence = 0.0
        
        # If we found bank codes, increase confidence
        if extracted_records:
            confidence += 0.5
        
        # If answer contains specific keywords, increase confidence
        positive_keywords = ["联行号", "银行", "清算", "分行"]
        for keyword in positive_keywords:
            if keyword in answer:
                confidence += 0.1
        
        # If answer contains negative keywords, decrease confidence
        negative_keywords = ["不确定", "可能", "也许", "未找到", "不知道"]
        for keyword in negative_keywords:
            if keyword in answer:
                confidence -= 0.2
        
        # Clamp to [0.0, 1.0]
        confidence = max(0.0, min(1.0, confidence))
        
        return confidence
    
    def query(
        self,
        question: str,
        user_id: Optional[int] = None,
        log_query: bool = True,
        use_rag: bool = True  # Enable RAG by default
    ) -> Dict[str, Any]:
        """
        Process a query and return response
        
        Args:
            question: User's question
            user_id: User ID (for logging)
            log_query: Whether to log the query
        
        Returns:
            Query response dictionary
        
        Raises:
            QueryServiceError: If query processing fails
        """
        start_time = time.time()
        self._total_queries += 1
        
        try:
            # 性能优化：检查缓存
            cached_result = self._get_cached_result(question)
            if cached_result:
                # 更新响应时间（缓存命中很快）
                cached_result['response_time'] = (time.time() - start_time) * 1000
                
                # 记录查询日志（如果需要）
                if log_query and user_id:
                    self._log_query(
                        user_id=user_id,
                        question=question,
                        answer=cached_result['answer'],
                        confidence=cached_result['confidence'],
                        response_time=cached_result['response_time']
                    )
                
                return cached_result
            # RAG: Retrieve relevant banks using new vector-based RAG system
            context = None
            retrieved_banks = []
            logger.info(f"RAG enabled: {use_rag}")
            if use_rag:
                # 使用新的向量RAG系统
                import asyncio
                try:
                    # 在同步函数中运行异步RAG检索
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    retrieved_banks = loop.run_until_complete(
                        self.rag_service.retrieve_relevant_banks(question, top_k=5)
                    )
                    loop.close()
                except Exception as rag_error:
                    logger.warning(f"Vector RAG failed, falling back to keyword search: {rag_error}")
                    # 降级到原有的关键词检索
                    retrieved_banks = self.retrieve_relevant_banks(question, top_k=5)
                
                if retrieved_banks:
                    # Format context for the model
                    context_lines = []
                    for bank in retrieved_banks:
                        context_lines.append(
                            f"{bank['bank_name']}: {bank['bank_code']}"
                        )
                    context = "\n".join(context_lines)
                    logger.info(f"RAG: Retrieved {len(retrieved_banks)} relevant banks")
                    logger.info(f"RAG Context: {context[:200]}...")
                else:
                    logger.warning("RAG: No relevant banks found")
            else:
                logger.info("RAG: Disabled by request")
            
            # 使用优化的小模型答案生成算法
            if retrieved_banks:
                logger.info("使用优化的答案生成算法...")
                answer = self.generate_answer_with_small_model(question, retrieved_banks)
            else:
                # 使用优化的无匹配答案格式化
                answer = self._format_no_match_answer(question)
            
            # 记录生成的答案（调试用）
            logger.info(f"优化答案生成完成（前200字符）：{answer[:200]}")
            
            # Extract bank codes
            matched_records = self.extract_bank_codes(answer)
            
            # 记录提取结果
            logger.info(f"从答案中提取了{len(matched_records)}条银行记录")
            
            if len(matched_records) == 0:
                logger.warning("未从答案中提取到银行代码")
                # 如果有RAG结果但未提取到代码，使用RAG结果
                if retrieved_banks:
                    matched_records = retrieved_banks[:1]  # 使用最佳匹配
                    logger.info("使用RAG检索结果作为匹配记录")
            
            # Calculate confidence with RAG enhancement
            confidence = self.calculate_confidence(answer, matched_records)
            
            # 如果有RAG结果，调整置信度
            if retrieved_banks and 'final_score' in retrieved_banks[0]:
                rag_confidence = min(1.0, retrieved_banks[0]['final_score'] / 10.0)
                confidence = max(confidence, rag_confidence)
                logger.info(f"RAG置信度调整：{rag_confidence:.3f}")
            
            # 使用新的结构化答案格式化（如果有匹配记录）
            if matched_records:
                try:
                    formatted_answer = self.format_structured_answer(
                        question, matched_records, confidence, 0
                    )
                    # 如果格式化答案更好，使用格式化版本
                    if len(formatted_answer) > len(answer) and "🏦" in formatted_answer:
                        answer = formatted_answer
                        logger.info("使用结构化格式化答案")
                except Exception as format_error:
                    logger.warning(f"答案格式化失败，使用原始答案：{format_error}")
            
            # Calculate response time
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Prepare response
            response = {
                "question": question,
                "answer": answer,
                "confidence": confidence,
                "response_time": response_time,
                "matched_records": matched_records,
                "timestamp": time.time()
            }
            
            # 性能优化：缓存结果（只缓存成功的查询）
            if matched_records:  # 只缓存有结果的查询
                self._cache_result(question, response)
            
            # Log query to database
            if log_query:
                self._log_query(
                    user_id=user_id,
                    question=question,
                    answer=answer,
                    confidence=confidence,
                    response_time=response_time
                )
            
            return response
        
        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            raise QueryServiceError(f"Query processing failed: {e}")
    
    def batch_query(
        self,
        questions: List[str],
        user_id: Optional[int] = None,
        log_queries: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Process multiple queries in batch
        
        Args:
            questions: List of questions
            user_id: User ID (for logging)
            log_queries: Whether to log the queries
        
        Returns:
            List of query responses
        """
        responses = []
        
        for question in questions:
            try:
                response = self.query(
                    question=question,
                    user_id=user_id,
                    log_query=log_queries
                )
                responses.append(response)
            except Exception as e:
                logger.error(f"Failed to process question '{question}': {e}")
                responses.append({
                    "question": question,
                    "answer": f"查询失败：{str(e)}",
                    "confidence": 0.0,
                    "response_time": 0.0,
                    "matched_records": [],
                    "error": str(e)
                })
        
        return responses
    
    def _log_query(
        self,
        user_id: Optional[int],
        question: str,
        answer: str,
        confidence: float,
        response_time: float
    ) -> None:
        """
        Log query to database
        
        Args:
            user_id: User ID
            question: Question
            answer: Answer
            confidence: Confidence score
            response_time: Response time in milliseconds
        """
        try:
            # 确保数据库会话是活跃的
            if not self.db.is_active:
                logger.warning("Database session is not active, attempting to refresh")
                self.db.rollback()  # 重置会话状态
            
            query_log = QueryLog(
                user_id=user_id,
                question=question,
                answer=answer,
                confidence=confidence,
                response_time=response_time,
                model_version=self.model_version
            )
            self.db.add(query_log)
            self.db.commit()
            logger.info(f"Query logged successfully: user_id={user_id}, question='{question[:50]}...'")
        except Exception as e:
            logger.error(f"Failed to log query: {e}")
            try:
                self.db.rollback()
            except Exception as rollback_error:
                logger.error(f"Failed to rollback transaction: {rollback_error}")
    
    def get_query_history(
        self,
        user_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get query history from database
        
        Args:
            user_id: Filter by user ID (None for all users)
            limit: Maximum number of records to return
            offset: Number of records to skip
        
        Returns:
            List of query log records
        """
        try:
            query = self.db.query(QueryLog)
            
            if user_id is not None:
                query = query.filter(QueryLog.user_id == user_id)
            
            query = query.order_by(QueryLog.created_at.desc())
            query = query.limit(limit).offset(offset)
            
            logs = query.all()
            
            return [log.to_dict() for log in logs]
        
        except Exception as e:
            logger.error(f"Failed to get query history: {e}")
            return []
    
    def get_latest_model_path(self) -> Optional[str]:
        """
        Get the path to the latest trained model
        
        Returns:
            Path to latest model or None if no model found
        """
        try:
            # Find the latest completed training job
            latest_job = self.db.query(TrainingJob).filter(
                TrainingJob.status == "completed",
                TrainingJob.model_path.isnot(None)
            ).order_by(TrainingJob.completed_at.desc()).first()
            
            if latest_job and latest_job.model_path:
                model_path = latest_job.model_path
                if os.path.exists(model_path):
                    return model_path
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to get latest model path: {e}")
            return None
