"""
小模型服务 - 智能问题识别和答案生成

本服务实现了多种小模型的集成，用于：
1. 问题意图识别和分类
2. 实体提取和结构化
3. 答案生成和优化
4. 模型选择和管理

支持的模型：
    - OpenAI GPT系列 (gpt-3.5-turbo, gpt-4)
    - Anthropic Claude系列 (claude-3-haiku, claude-3-sonnet)
    - 本地模型 (通过transformers)

主要功能：
    - 智能问题分析
    - 银行信息实体提取
    - 基于上下文的答案生成
    - 多模型性能对比

使用示例：
    >>> model_service = SmallModelService()
    >>> 
    >>> # 分析问题
    >>> analysis = await model_service.analyze_question("工商银行西单支行联行号")
    >>> 
    >>> # 生成答案
    >>> answer = await model_service.generate_answer(question, context)
"""

import json
import asyncio
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum

import openai
import anthropic
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from loguru import logger


class ModelType(Enum):
    """支持的模型类型"""
    OPENAI_GPT35 = "gpt-3.5-turbo"
    OPENAI_GPT4 = "gpt-4"
    ANTHROPIC_HAIKU = "claude-3-haiku-20240307"
    ANTHROPIC_SONNET = "claude-3-sonnet-20240229"
    LOCAL_MODEL = "local"


class QuestionType(Enum):
    """问题类型分类"""
    BANK_CODE_QUERY = "bank_code_query"      # 联行号查询
    BANK_NAME_QUERY = "bank_name_query"      # 银行名称查询
    BRANCH_QUERY = "branch_query"            # 支行查询
    GENERAL_QUERY = "general_query"          # 一般查询
    UNCLEAR_QUERY = "unclear_query"          # 不明确查询


class SmallModelService:
    """
    小模型服务 - 智能问题处理和答案生成
    
    本类实现了多种小模型的统一接口，包括：
    1. 模型管理和选择
    2. 问题分析和分类
    3. 实体提取和结构化
    4. 答案生成和优化
    5. 性能监控和统计
    
    属性：
        current_model: 当前使用的模型
        openai_client: OpenAI客户端
        anthropic_client: Anthropic客户端
        local_model: 本地模型
        config: 模型配置参数
    """
    
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        default_model: ModelType = ModelType.OPENAI_GPT35,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化小模型服务
        
        Args:
            openai_api_key: OpenAI API密钥
            anthropic_api_key: Anthropic API密钥
            default_model: 默认使用的模型
            config: 模型配置参数
        """
        self.current_model = default_model
        self.openai_client = None
        self.anthropic_client = None
        self.local_model = None
        self.local_tokenizer = None
        
        # 默认配置
        self.config = {
            "temperature": 0.1,
            "max_tokens": 512,
            "timeout": 30,
            "retry_attempts": 3,
            "enable_caching": True,
            "cache_ttl": 3600,
            "local_model_name": "microsoft/DialoGPT-medium",
            "device": "cuda" if torch.cuda.is_available() else "cpu"
        }
        
        if config:
            self.config.update(config)
        
        # 初始化客户端
        if openai_api_key:
            self.openai_client = openai.AsyncOpenAI(api_key=openai_api_key)
        
        if anthropic_api_key:
            self.anthropic_client = anthropic.AsyncAnthropic(api_key=anthropic_api_key)
        
        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "model_usage": {},
            "average_response_time": 0.0,
            "last_request_time": None
        }
    
    async def initialize_local_model(self, model_name: Optional[str] = None) -> bool:
        """
        初始化本地模型
        
        Args:
            model_name: 模型名称
        
        Returns:
            是否成功初始化
        """
        try:
            model_name = model_name or self.config["local_model_name"]
            logger.info(f"Initializing local model: {model_name}")
            
            self.local_tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.local_model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if self.config["device"] == "cuda" else torch.float32,
                device_map="auto" if self.config["device"] == "cuda" else None
            )
            
            # 设置pad_token
            if self.local_tokenizer.pad_token is None:
                self.local_tokenizer.pad_token = self.local_tokenizer.eos_token
            
            logger.info(f"Local model initialized successfully on {self.config['device']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize local model: {e}")
            return False
    
    def set_model(self, model_type: ModelType) -> bool:
        """
        设置当前使用的模型
        
        Args:
            model_type: 模型类型
        
        Returns:
            是否成功设置
        """
        try:
            if model_type in [ModelType.OPENAI_GPT35, ModelType.OPENAI_GPT4]:
                if not self.openai_client:
                    logger.error("OpenAI client not initialized")
                    return False
            
            elif model_type in [ModelType.ANTHROPIC_HAIKU, ModelType.ANTHROPIC_SONNET]:
                if not self.anthropic_client:
                    logger.error("Anthropic client not initialized")
                    return False
            
            elif model_type == ModelType.LOCAL_MODEL:
                if not self.local_model:
                    logger.error("Local model not initialized")
                    return False
            
            self.current_model = model_type
            logger.info(f"Model set to: {model_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set model: {e}")
            return False
    
    async def analyze_question(self, question: str) -> Dict[str, Any]:
        """
        分析问题并提取结构化信息
        
        Args:
            question: 用户问题
        
        Returns:
            分析结果字典
        """
        try:
            start_time = datetime.now()
            
            # 构建分析提示
            analysis_prompt = self._build_analysis_prompt(question)
            
            # 调用模型进行分析
            response = await self._call_model(analysis_prompt)
            
            # 解析响应
            analysis_result = self._parse_analysis_response(response, question)
            
            # 更新统计信息
            self._update_stats(start_time, True)
            
            logger.info(f"Question analysis completed: {analysis_result['question_type']}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Failed to analyze question: {e}")
            self._update_stats(start_time, False)
            
            # 返回基础分析结果
            return self._fallback_analysis(question)
    
    def _build_analysis_prompt(self, question: str) -> str:
        """构建问题分析提示"""
        return f"""
请分析以下银行相关问题，提取关键信息并分类：

问题：{question}

请按以下JSON格式返回分析结果：
{{
    "question_type": "问题类型(bank_code_query/bank_name_query/branch_query/general_query/unclear_query)",
    "bank_name": "银行名称(如果有)",
    "branch_name": "支行名称(如果有)", 
    "location": "地理位置(如果有)",
    "bank_code": "联行号(如果有)",
    "intent": "用户意图描述",
    "keywords": ["关键词列表"],
    "confidence": 0.95
}}

分析要点：
1. 识别问题类型：查询联行号、查询银行名称、查询支行信息等
2. 提取银行名称：完整名称或简称
3. 提取支行信息：支行名称、地理位置
4. 提取其他实体：联行号、清算代码等
5. 评估识别置信度

只返回JSON格式的结果，不要其他内容。
"""
    
    async def _call_model(self, prompt: str) -> str:
        """
        调用当前模型
        
        Args:
            prompt: 输入提示
        
        Returns:
            模型响应
        """
        if self.current_model in [ModelType.OPENAI_GPT35, ModelType.OPENAI_GPT4]:
            return await self._call_openai(prompt)
        
        elif self.current_model in [ModelType.ANTHROPIC_HAIKU, ModelType.ANTHROPIC_SONNET]:
            return await self._call_anthropic(prompt)
        
        elif self.current_model == ModelType.LOCAL_MODEL:
            return await self._call_local_model(prompt)
        
        else:
            raise ValueError(f"Unsupported model type: {self.current_model}")
    
    async def _call_openai(self, prompt: str) -> str:
        """调用OpenAI模型"""
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.current_model.value,
                messages=[
                    {"role": "system", "content": "你是一个专业的银行信息分析助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config["temperature"],
                max_tokens=self.config["max_tokens"],
                timeout=self.config["timeout"]
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
    
    async def _call_anthropic(self, prompt: str) -> str:
        """调用Anthropic模型"""
        try:
            response = await self.anthropic_client.messages.create(
                model=self.current_model.value,
                max_tokens=self.config["max_tokens"],
                temperature=self.config["temperature"],
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            raise
    
    async def _call_local_model(self, prompt: str) -> str:
        """调用本地模型"""
        try:
            if not self.local_model or not self.local_tokenizer:
                raise ValueError("Local model not initialized")
            
            # 编码输入
            inputs = self.local_tokenizer.encode(prompt, return_tensors="pt")
            if self.config["device"] == "cuda":
                inputs = inputs.to("cuda")
            
            # 生成响应
            with torch.no_grad():
                outputs = self.local_model.generate(
                    inputs,
                    max_length=inputs.shape[1] + self.config["max_tokens"],
                    temperature=self.config["temperature"],
                    do_sample=True,
                    pad_token_id=self.local_tokenizer.eos_token_id
                )
            
            # 解码响应
            response = self.local_tokenizer.decode(
                outputs[0][inputs.shape[1]:], 
                skip_special_tokens=True
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Local model call failed: {e}")
            raise
    
    def _parse_analysis_response(self, response: str, original_question: str) -> Dict[str, Any]:
        """
        解析模型分析响应
        
        Args:
            response: 模型响应
            original_question: 原始问题
        
        Returns:
            解析后的分析结果
        """
        try:
            # 尝试解析JSON响应
            if response.strip().startswith('{'):
                result = json.loads(response.strip())
                
                # 验证必要字段
                if "question_type" not in result:
                    result["question_type"] = "general_query"
                
                if "confidence" not in result:
                    result["confidence"] = 0.8
                
                # 添加原始问题
                result["original_question"] = original_question
                result["model_used"] = self.current_model.value
                result["analysis_time"] = datetime.now().isoformat()
                
                return result
            
            else:
                # 如果不是JSON格式，进行基础解析
                return self._fallback_analysis(original_question)
                
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON response: {response[:100]}...")
            return self._fallback_analysis(original_question)
    
    def _fallback_analysis(self, question: str) -> Dict[str, Any]:
        """
        备用分析方法（基于规则）
        
        Args:
            question: 用户问题
        
        Returns:
            基础分析结果
        """
        result = {
            "question_type": "general_query",
            "bank_name": None,
            "branch_name": None,
            "location": None,
            "bank_code": None,
            "intent": "查询银行相关信息",
            "keywords": [],
            "confidence": 0.6,
            "original_question": question,
            "model_used": "fallback_rules",
            "analysis_time": datetime.now().isoformat()
        }
        
        question_lower = question.lower()
        
        # 简单的规则匹配
        if "联行号" in question or "行号" in question:
            result["question_type"] = "bank_code_query"
            result["intent"] = "查询银行联行号"
        
        elif "支行" in question or "分行" in question:
            result["question_type"] = "branch_query"
            result["intent"] = "查询支行信息"
        
        elif any(bank in question for bank in ["工商银行", "农业银行", "中国银行", "建设银行"]):
            result["question_type"] = "bank_name_query"
            result["intent"] = "查询银行信息"
        
        # 改进的银行名称提取逻辑
        bank_name = self._extract_bank_name_from_question(question)
        if bank_name:
            result["bank_name"] = bank_name
            result["question_type"] = "bank_name_query"
            result["confidence"] = 0.8
        
        # 提取联行号
        bank_code = self._extract_bank_code_from_question(question)
        if bank_code:
            result["bank_code"] = bank_code
            result["question_type"] = "bank_code_query"
            result["confidence"] = 0.9
        
        # 提取关键词
        keywords = self._extract_keywords_from_question(question)
        result["keywords"] = keywords
        
        return result
    
    def _extract_bank_name_from_question(self, question: str) -> str:
        """从问题中提取银行名称"""
        import re
        
        # 常见银行名称模式
        bank_patterns = [
            r'(中国工商银行股份有限公司[^的？]*?支行)',
            r'(中国农业银行股份有限公司[^的？]*?支行)',
            r'(中国银行股份有限公司[^的？]*?支行)',
            r'(中国建设银行股份有限公司[^的？]*?支行)',
            r'(交通银行股份有限公司[^的？]*?支行)',
            r'(招商银行股份有限公司[^的？]*?支行)',
            r'(中国民生银行股份有限公司[^的？]*?支行)',
            r'(中信银行股份有限公司[^的？]*?支行)',
            r'(上海浦东发展银行股份有限公司[^的？]*?支行)',
            r'(兴业银行股份有限公司[^的？]*?支行)',
            r'(平安银行股份有限公司[^的？]*?支行)',
            r'(华夏银行股份有限公司[^的？]*?支行)',
            r'(光大银行股份有限公司[^的？]*?支行)',
            r'(广发银行股份有限公司[^的？]*?支行)',
            r'([^，。！？]*?银行[^，。！？]*?支行)',
            r'([^，。！？]*?银行[^，。！？]*?分行)',
        ]
        
        for pattern in bank_patterns:
            match = re.search(pattern, question)
            if match:
                bank_name = match.group(1).strip()
                # 清理银行名称
                bank_name = bank_name.replace('的', '').replace('？', '').replace('?', '')
                if len(bank_name) > 5:  # 确保是有效的银行名称
                    return bank_name
        
        return None
    
    def _extract_bank_code_from_question(self, question: str) -> str:
        """从问题中提取联行号"""
        import re
        
        # 联行号通常是12位数字
        code_pattern = r'(\d{12})'
        match = re.search(code_pattern, question)
        if match:
            return match.group(1)
        return None
    
    def _extract_keywords_from_question(self, question: str) -> list:
        """从问题中提取关键词"""
        # 简单分词
        words = []
        current_word = ""
        for char in question:
            if char.isalnum() or ord(char) > 127:  # 字母数字或中文字符
                current_word += char
            else:
                if current_word:
                    words.append(current_word)
                    current_word = ""
        if current_word:
            words.append(current_word)
        
        # 过滤停用词和短词
        stop_words = {'的', '是', '在', '有', '和', '与', '或', '但', '而', '了', '吗', '呢', '吧', '啊', '什么', '哪个', '怎么', '如何'}
        keywords = []
        for word in words:
            if len(word) >= 2 and word not in stop_words:
                keywords.append(word)
        
        return list(set(keywords))[:10]  # 限制关键词数量
    
    async def generate_answer(
        self,
        question: str,
        context: List[Dict[str, Any]],
        analysis: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        基于上下文生成答案
        
        Args:
            question: 用户问题
            context: 检索到的银行信息上下文
            analysis: 问题分析结果（可选）
        
        Returns:
            生成的答案和相关信息
        """
        try:
            start_time = datetime.now()
            
            # 如果没有分析结果，先进行分析
            if not analysis:
                analysis = await self.analyze_question(question)
            
            # 构建答案生成提示
            answer_prompt = self._build_answer_prompt(question, context, analysis)
            
            # 调用模型生成答案
            response = await self._call_model(answer_prompt)
            
            # 解析答案
            answer_result = self._parse_answer_response(response, question, context, analysis)
            
            # 更新统计信息
            self._update_stats(start_time, True)
            
            logger.info(f"Answer generated successfully for question type: {analysis.get('question_type')}")
            return answer_result
            
        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            self._update_stats(start_time, False)
            
            # 返回备用答案
            return self._fallback_answer(question, context)
    
    def _build_answer_prompt(
        self,
        question: str,
        context: List[Dict[str, Any]],
        analysis: Dict[str, Any]
    ) -> str:
        """构建答案生成提示"""
        
        # 格式化上下文信息
        context_text = ""
        for i, bank in enumerate(context[:5], 1):  # 限制上下文数量
            context_text += f"""
{i}. 银行名称：{bank.get('bank_name', 'N/A')}
   联行号：{bank.get('bank_code', 'N/A')}
   清算代码：{bank.get('clearing_code', 'N/A')}
"""
        
        return f"""
基于以下银行信息，回答用户问题：

用户问题：{question}

问题分析：
- 问题类型：{analysis.get('question_type', 'general_query')}
- 用户意图：{analysis.get('intent', '查询银行信息')}
- 关键词：{', '.join(analysis.get('keywords', []))}

相关银行信息：
{context_text}

请按以下要求生成回答：
1. 直接回答用户问题，提供准确的银行信息
2. 如果找到精确匹配，优先提供该信息
3. 如果有多个匹配结果，列出最相关的几个
4. 如果没有找到匹配，说明原因并提供建议
5. 保持回答简洁、准确、专业

回答格式：
{{
    "answer": "具体回答内容",
    "confidence": 0.95,
    "matched_banks": [
        {{
            "bank_name": "银行名称",
            "bank_code": "联行号",
            "clearing_code": "清算代码"
        }}
    ],
    "suggestions": ["建议列表(如果需要)"]
}}

只返回JSON格式的结果。
"""
    
    def _parse_answer_response(
        self,
        response: str,
        question: str,
        context: List[Dict[str, Any]],
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """解析答案响应"""
        try:
            if response.strip().startswith('{'):
                result = json.loads(response.strip())
                
                # 添加元信息
                result["original_question"] = question
                result["model_used"] = self.current_model.value
                result["generation_time"] = datetime.now().isoformat()
                result["context_count"] = len(context)
                result["analysis"] = analysis
                
                return result
            
            else:
                # 非JSON响应的处理
                return {
                    "answer": response.strip(),
                    "confidence": 0.7,
                    "matched_banks": context[:3] if context else [],
                    "suggestions": [],
                    "original_question": question,
                    "model_used": self.current_model.value,
                    "generation_time": datetime.now().isoformat(),
                    "context_count": len(context),
                    "analysis": analysis
                }
                
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse answer JSON: {response[:100]}...")
            return self._fallback_answer(question, context)
    
    def _fallback_answer(self, question: str, context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """备用答案生成"""
        if not context:
            answer = "抱歉，没有找到相关的银行信息。请检查您的查询条件或尝试使用更具体的银行名称。"
            matched_banks = []
        else:
            bank = context[0]
            answer = f"根据您的查询，找到以下银行信息：\n银行名称：{bank.get('bank_name', 'N/A')}\n联行号：{bank.get('bank_code', 'N/A')}"
            if bank.get('clearing_code'):
                answer += f"\n清算代码：{bank['clearing_code']}"
            
            matched_banks = context[:3]
        
        return {
            "answer": answer,
            "confidence": 0.6,
            "matched_banks": matched_banks,
            "suggestions": ["请尝试使用完整的银行名称", "确认支行名称是否正确"],
            "original_question": question,
            "model_used": "fallback_rules",
            "generation_time": datetime.now().isoformat(),
            "context_count": len(context),
            "analysis": None
        }
    
    def _update_stats(self, start_time: datetime, success: bool):
        """更新统计信息"""
        self.stats["total_requests"] += 1
        
        if success:
            self.stats["successful_requests"] += 1
        else:
            self.stats["failed_requests"] += 1
        
        # 更新模型使用统计
        model_name = self.current_model.value
        if model_name not in self.stats["model_usage"]:
            self.stats["model_usage"][model_name] = 0
        self.stats["model_usage"][model_name] += 1
        
        # 更新平均响应时间
        response_time = (datetime.now() - start_time).total_seconds()
        if self.stats["total_requests"] == 1:
            self.stats["average_response_time"] = response_time
        else:
            self.stats["average_response_time"] = (
                self.stats["average_response_time"] * (self.stats["total_requests"] - 1) + response_time
            ) / self.stats["total_requests"]
        
        self.stats["last_request_time"] = datetime.now().isoformat()
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """获取可用的模型列表"""
        models = []
        
        if self.openai_client:
            models.extend([
                {
                    "type": ModelType.OPENAI_GPT35.value,
                    "name": "GPT-3.5 Turbo",
                    "provider": "OpenAI",
                    "status": "available",
                    "description": "快速、经济的对话模型"
                },
                {
                    "type": ModelType.OPENAI_GPT4.value,
                    "name": "GPT-4",
                    "provider": "OpenAI", 
                    "status": "available",
                    "description": "更强大的推理能力"
                }
            ])
        
        if self.anthropic_client:
            models.extend([
                {
                    "type": ModelType.ANTHROPIC_HAIKU.value,
                    "name": "Claude 3 Haiku",
                    "provider": "Anthropic",
                    "status": "available",
                    "description": "快速、轻量的模型"
                },
                {
                    "type": ModelType.ANTHROPIC_SONNET.value,
                    "name": "Claude 3 Sonnet",
                    "provider": "Anthropic",
                    "status": "available",
                    "description": "平衡性能和速度"
                }
            ])
        
        if self.local_model:
            models.append({
                "type": ModelType.LOCAL_MODEL.value,
                "name": "Local Model",
                "provider": "Local",
                "status": "available",
                "description": "本地部署的模型"
            })
        
        return models
    
    def get_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        return {
            **self.stats,
            "current_model": self.current_model.value,
            "available_models": len(self.get_available_models()),
            "config": self.config
        }