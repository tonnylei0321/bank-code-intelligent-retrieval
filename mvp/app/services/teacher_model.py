"""
大模型API客户端模块

提供与通义千问（Qwen）大模型API的交互功能，用于：
1. 生成问答对训练数据
2. 自动重试机制（指数退避）
3. API调用日志记录
4. 错误分类和处理
5. 批量生成支持

特性：
- 最多3次重试，指数退避策略
- 详细的API调用日志
- 速率限制处理
- 超时处理
- 认证错误处理
"""
import time
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
import httpx
from loguru import logger

from app.core.config import settings
from app.models.bank_code import BankCode
from app.core.database import SessionLocal


class TeacherModelAPIError(Exception):
    """大模型API错误的基础异常类"""
    pass


class APIRateLimitError(TeacherModelAPIError):
    """API速率限制超出时抛出的异常"""
    pass


class APITimeoutError(TeacherModelAPIError):
    """API请求超时时抛出的异常"""
    pass


class APIAuthenticationError(TeacherModelAPIError):
    """API认证失败时抛出的异常"""
    pass


class TeacherModelAPI:
    """
    通义千问（Qwen/Tongyi Qianwen）大模型API客户端
    
    提供与阿里云通义千问API的交互功能，用于生成高质量的问答对训练数据。
    
    特性：
    - 自动重试机制（最多3次，指数退避）
    - 详细的API调用日志
    - 速率限制处理
    - 超时处理
    - 错误分类和处理
    
    支持的问题类型：
    - exact: 精确查询（完整银行名称查联行号）
    - fuzzy: 模糊查询（简称或不完整名称）
    - reverse: 反向查询（联行号查银行名称）
    - natural: 自然语言查询（口语化表达）
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 30,
        model: str = "qwen-turbo",
        provider: str = "auto"
    ):
        """
        初始化大模型API客户端
        
        Args:
            api_key: API密钥，用于认证（自动检测可用的API）
            api_url: API端点URL（自动检测可用的API）
            max_retries: 最大重试次数，默认3次
            timeout: 请求超时时间（秒），默认30秒
            model: 使用的模型名称，默认"qwen-turbo"
            provider: API提供商（auto/qwen/deepseek/volces）
        """
        self.max_retries = max_retries
        self.timeout = timeout
        self.provider = provider
        
        # 自动检测可用的API配置
        self.api_configs = self._detect_available_apis()
        
        if not self.api_configs:
            logger.error("❌ 没有找到可用的API配置 - QA对生成将使用本地模板！")
            logger.error("请在.env文件中配置至少一个API密钥:")
            logger.error("  QWEN_API_KEY=your_qwen_api_key")
            logger.error("  DEEPSEEK_API_KEY=your_deepseek_api_key")
            logger.error("  VOLCES_API_KEY=your_volces_api_key")
            self.api_key = None
            self.api_url = None
            self.model = model
        else:
            # 根据指定的provider选择API配置
            selected_config = None
            
            if provider == "auto":
                # 自动选择第一个可用的
                selected_config = self.api_configs[0]
            elif provider == "local":
                # 使用本地模板，不需要API
                self.api_key = None
                self.api_url = None
                self.model = "local"
                self.provider = "local"
                logger.info("✅ 使用本地模板生成器")
                return
            else:
                # 查找指定的provider
                for config in self.api_configs:
                    if config['provider'] == provider:
                        selected_config = config
                        break
                
                # 如果找不到指定的provider，使用第一个可用的
                if not selected_config:
                    logger.warning(f"⚠️  未找到 {provider} API配置，使用第一个可用的API")
                    selected_config = self.api_configs[0]
            
            self.api_key = selected_config['api_key']
            self.api_url = selected_config['api_url']
            self.model = selected_config['model']
            self.provider = selected_config['provider']
            
            logger.info(f"✅ 使用 {self.provider.upper()} API")
            logger.info(f"✅ API密钥已配置（长度: {len(self.api_key)}）")
            logger.info(f"✅ API URL: {self.api_url}")
            logger.info(f"✅ 模型: {self.model}")
        
        logger.info(
            f"大模型API客户端已初始化 - 提供商: {self.provider}, "
            f"最大重试次数: {self.max_retries}, 超时: {self.timeout}秒"
        )
    
    def _detect_available_apis(self) -> List[Dict[str, str]]:
        """
        检测可用的API配置
        
        Returns:
            可用API配置列表，按优先级排序
        """
        configs = []
        
        # 检查通义千问API
        if hasattr(settings, 'QWEN_API_KEY') and settings.QWEN_API_KEY:
            configs.append({
                'provider': 'qwen',
                'api_key': settings.QWEN_API_KEY,
                'api_url': getattr(settings, 'QWEN_API_URL', None) or settings.qwen_api_url,
                'model': 'qwen-turbo'
            })
            logger.info("🔍 检测到通义千问API配置")
        
        # 检查DeepSeek API
        if hasattr(settings, 'DEEPSEEK_API_KEY') and settings.DEEPSEEK_API_KEY:
            configs.append({
                'provider': 'deepseek',
                'api_key': settings.DEEPSEEK_API_KEY,
                'api_url': getattr(settings, 'DEEPSEEK_API_URL', 'https://api.deepseek.com'),
                'model': 'deepseek-chat'
            })
            logger.info("🔍 检测到DeepSeek API配置")
        
        # 检查火山引擎API
        if hasattr(settings, 'VOLCES_API_KEY') and settings.VOLCES_API_KEY:
            configs.append({
                'provider': 'volces',
                'api_key': settings.VOLCES_API_KEY,
                'api_url': getattr(settings, 'VOLCES_API_URL', 'https://ark.cn-beijing.volces.com'),
                'model': 'doubao-lite-4k'
            })
            logger.info("🔍 检测到火山引擎API配置")
        
        return configs
    
    def _get_prompt_template_from_db(self, question_type: str) -> Optional[str]:
        """
        从数据库获取提示词模板
        
        Args:
            question_type: 问题类型（exact/fuzzy/reverse/natural）
        
        Returns:
            提示词模板字符串，如果未找到则返回None
        """
        try:
            from app.models.llm_prompt_template import LLMPromptTemplate
            
            db = SessionLocal()
            try:
                # 查询对应提供商和问题类型的活跃模板
                template = db.query(LLMPromptTemplate).filter(
                    LLMPromptTemplate.provider == self.provider,
                    LLMPromptTemplate.prompt_type == "sample_generation",
                    LLMPromptTemplate.question_type == question_type,
                    LLMPromptTemplate.is_active == True
                ).first()
                
                if template:
                    logger.debug(f"从数据库加载提示词模板: {self.provider} - {question_type}")
                    return template.template
                else:
                    logger.debug(f"数据库中未找到提示词模板: {self.provider} - {question_type}")
                    return None
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"从数据库加载提示词模板失败: {e}")
            return None
    
    def _build_prompt(self, bank_record: BankCode, question_type: str) -> str:
        """
        构建生成问答对的提示词
        
        优先从数据库加载用户自定义的提示词模板，如果未找到则使用默认模板。
        提示词包含银行信息和生成要求。
        
        Args:
            bank_record: 联行号记录对象
            question_type: 问题类型（exact/fuzzy/reverse/natural）
        
        Returns:
            格式化的提示词字符串
        
        Raises:
            ValueError: 问题类型未知
        """
        bank_name = bank_record.bank_name
        bank_code = bank_record.bank_code
        clearing_code = bank_record.clearing_code
        
        # 尝试从数据库加载提示词模板
        template = self._get_prompt_template_from_db(question_type)
        
        if template:
            # 使用数据库中的模板，替换变量
            try:
                prompt = template.format(
                    bank_name=bank_name,
                    bank_code=bank_code,
                    clearing_code=clearing_code
                )
                return prompt
            except Exception as e:
                logger.warning(f"格式化数据库提示词模板失败: {e}，使用默认模板")
        
        # 如果数据库中没有或格式化失败，使用默认模板
        logger.debug(f"使用默认提示词模板: {question_type}")
        
        if question_type == "exact":
            # 精确查询：使用完整银行名称查询联行号
            prompt = f"""请根据以下银行信息生成一个精确查询的问答对：
银行名称：{bank_name}
联行号：{bank_code}
清算行行号：{clearing_code}

要求：
1. 问题应该是完整的银行名称查询联行号
2. 答案应该直接给出联行号
3. 格式：问题|答案

示例：
中国工商银行北京分行的联行号是什么？|{bank_code}

请生成："""
        
        elif question_type == "fuzzy":
            # 模糊查询：使用简称或不完整名称
            prompt = f"""请根据以下银行信息生成一个模糊查询的问答对：
银行名称：{bank_name}
联行号：{bank_code}
清算行行号：{clearing_code}

要求：
1. 问题应该使用简称或不完整的银行名称
2. 答案应该包含完整的银行名称和联行号
3. 格式：问题|答案

示例：
工行北京分行的联行号|{bank_name}的联行号是{bank_code}

请生成："""
        
        elif question_type == "reverse":
            # 反向查询：根据联行号查询银行名称
            prompt = f"""请根据以下银行信息生成一个反向查询的问答对：
银行名称：{bank_name}
联行号：{bank_code}
清算行行号：{clearing_code}

要求：
1. 问题应该是根据联行号查询银行名称
2. 答案应该给出完整的银行名称
3. 格式：问题|答案

示例：
联行号{bank_code}是哪个银行？|{bank_name}

请生成："""
        
        elif question_type == "natural":
            # 自然语言查询：口语化表达
            prompt = f"""请根据以下银行信息生成一个自然语言查询的问答对：
银行名称：{bank_name}
联行号：{bank_code}
清算行行号：{clearing_code}

要求：
1. 问题应该是口语化的自然语言表达
2. 答案应该自然地包含银行名称和联行号
3. 格式：问题|答案

示例：
帮我查一下工行北京的联行号|{bank_name}的联行号是{bank_code}

请生成："""
        
        else:
            raise ValueError(f"未知的问题类型: {question_type}")
        
        return prompt
    
    def _parse_response(self, response_text: str) -> tuple[str, str]:
        """
        解析API响应，提取问题和答案
        
        期望的响应格式：问题|答案
        
        Args:
            response_text: API返回的原始文本
        
        Returns:
            元组 (问题, 答案)
        
        Raises:
            ValueError: 响应格式无效
        """
        # 期望格式："问题|答案"
        response_text = response_text.strip()
        
        if "|" not in response_text:
            raise ValueError(f"响应格式无效（缺少分隔符）: {response_text}")
        
        parts = response_text.split("|", 1)
        if len(parts) != 2:
            raise ValueError(f"响应格式无效（部分数量错误）: {response_text}")
        
        question = parts[0].strip()
        answer = parts[1].strip()
        
        if not question or not answer:
            raise ValueError(f"问题或答案为空: {response_text}")
        
        return question, answer
    
    def _call_api(self, prompt: str) -> str:
        """
        调用大模型API（支持多个提供商）
        
        发送HTTP POST请求到配置的API，处理各种错误情况。
        
        Args:
            prompt: 提示词文本
        
        Returns:
            API返回的响应文本
        
        Raises:
            APIAuthenticationError: 认证失败（401）
            APIRateLimitError: 速率限制超出（429）
            APITimeoutError: 请求超时
            TeacherModelAPIError: 其他API错误
        """
        # 验证API密钥
        if not self.api_key or self.api_key.strip() == "":
            raise APIAuthenticationError("API密钥未配置或为空")
        
        # 根据提供商构建请求
        if self.provider == 'qwen':
            return self._call_qwen_api(prompt)
        elif self.provider == 'deepseek':
            return self._call_deepseek_api(prompt)
        elif self.provider == 'volces':
            return self._call_volces_api(prompt)
        else:
            raise TeacherModelAPIError(f"不支持的API提供商: {self.provider}")
    
    def _call_qwen_api(self, prompt: str) -> str:
        """调用通义千问API"""
        clean_api_key = self.api_key.strip()
        
        headers = {
            "Authorization": f"Bearer {clean_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            },
            "parameters": {
                "result_format": "message"
            }
        }
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self.api_url,
                    headers=headers,
                    json=payload
                )
                
                self._check_response_status(response)
                result = response.json()
                
                # 通义千问API响应格式
                if "output" not in result:
                    raise TeacherModelAPIError(f"API响应格式无效: {result}")
                
                output = result["output"]
                if "choices" not in output or len(output["choices"]) == 0:
                    raise TeacherModelAPIError(f"API响应中没有choices: {result}")
                
                message = output["choices"][0].get("message", {})
                content = message.get("content", "")
                
                if not content:
                    raise TeacherModelAPIError("API响应内容为空")
                
                return content.strip()
                
        except httpx.TimeoutException:
            raise APITimeoutError(f"API请求超时（{self.timeout}秒）")
        except httpx.RequestError as e:
            raise TeacherModelAPIError(f"API请求失败: {e}")
    
    def _call_deepseek_api(self, prompt: str) -> str:
        """调用DeepSeek API"""
        clean_api_key = self.api_key.strip()
        
        headers = {
            "Authorization": f"Bearer {clean_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "stream": False
        }
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.api_url}/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                self._check_response_status(response)
                result = response.json()
                
                # OpenAI兼容格式
                if "choices" not in result or len(result["choices"]) == 0:
                    raise TeacherModelAPIError(f"API响应中没有choices: {result}")
                
                content = result["choices"][0]["message"]["content"]
                
                if not content:
                    raise TeacherModelAPIError("API响应内容为空")
                
                return content.strip()
                
        except httpx.TimeoutException:
            raise APITimeoutError(f"API请求超时（{self.timeout}秒）")
        except httpx.RequestError as e:
            raise TeacherModelAPIError(f"API请求失败: {e}")
    
    def _call_volces_api(self, prompt: str) -> str:
        """调用火山引擎API"""
        clean_api_key = self.api_key.strip()
        
        headers = {
            "Authorization": f"Bearer {clean_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.api_url}/api/v3/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                self._check_response_status(response)
                result = response.json()
                
                # OpenAI兼容格式
                if "choices" not in result or len(result["choices"]) == 0:
                    raise TeacherModelAPIError(f"API响应中没有choices: {result}")
                
                content = result["choices"][0]["message"]["content"]
                
                if not content:
                    raise TeacherModelAPIError("API响应内容为空")
                
                return content.strip()
                
        except httpx.TimeoutException:
            raise APITimeoutError(f"API请求超时（{self.timeout}秒）")
        except httpx.RequestError as e:
            raise TeacherModelAPIError(f"API请求失败: {e}")
    
    def _check_response_status(self, response):
        """检查HTTP响应状态"""
        if response.status_code == 401:
            raise APIAuthenticationError("API认证失败 - 请检查API密钥")
        elif response.status_code == 429:
            raise APIRateLimitError("API速率限制超出")
        elif response.status_code >= 500:
            raise TeacherModelAPIError(f"API服务器错误: {response.status_code}")
        elif response.status_code != 200:
            raise TeacherModelAPIError(
                f"API请求失败，状态码 {response.status_code}: {response.text}"
            )
    
    def generate_qa_pair(
        self,
        bank_record: BankCode,
        question_type: str
    ) -> Optional[tuple[str, str]]:
        """
        为联行号记录生成问答对，带重试机制和本地后备
        
        优先使用LLM API生成，如果API不可用则使用本地模板生成器
        
        Args:
            bank_record: 联行号记录对象
            question_type: 问题类型（exact/fuzzy/reverse/natural）
        
        Returns:
            元组 (问题, 答案)，如果所有方法都失败则返回None
        """
        # 首先尝试使用LLM API
        if self.api_key and self.api_key.strip():
            prompt = self._build_prompt(bank_record, question_type)
            
            for attempt in range(self.max_retries):
                try:
                    start_time = time.time()
                    
                    logger.debug(
                        f"生成问答对 - 记录ID: {bank_record.id}, "
                        f"类型: {question_type}, 尝试: {attempt + 1}/{self.max_retries}"
                    )
                    
                    # 调用API
                    response_text = self._call_api(prompt)
                    
                    # 解析响应
                    question, answer = self._parse_response(response_text)
                    
                    elapsed_time = time.time() - start_time
                    
                    logger.info(
                        f"问答对生成成功 - 记录ID: {bank_record.id}, "
                        f"类型: {question_type}, 耗时: {elapsed_time:.2f}秒"
                    )
                    
                    return question, answer
                
                except APIAuthenticationError as e:
                    # 认证错误，跳出循环使用本地生成器
                    logger.warning(f"API认证失败，切换到本地生成器: {e}")
                    break
                
                except (APIRateLimitError, APITimeoutError, TeacherModelAPIError) as e:
                    logger.warning(
                        f"API调用失败（尝试 {attempt + 1}/{self.max_retries}）: {e}"
                    )
                    
                    if attempt < self.max_retries - 1:
                        # 指数退避：1秒、2秒、4秒...
                        wait_time = 2 ** attempt
                        logger.info(f"等待 {wait_time} 秒后重试...")
                        time.sleep(wait_time)
                    else:
                        logger.warning("所有API重试都失败，切换到本地生成器")
        else:
            logger.info("API密钥未配置，使用本地生成器")
        
        # 使用本地模板生成器作为后备
        try:
            return self._generate_local_qa_pair(bank_record, question_type)
        except Exception as e:
            logger.error(f"本地生成器也失败: {e}")
            return None
    
    def generate_batch_qa_pairs(
        self,
        bank_records: list[BankCode],
        question_types: list[str]
    ) -> Dict[str, Any]:
        """
        为多个联行号记录批量生成问答对
        
        遍历所有记录和问题类型的组合，生成问答对。
        记录成功和失败的统计信息。
        
        Args:
            bank_records: 联行号记录列表
            question_types: 问题类型列表
        
        Returns:
            包含生成结果和统计信息的字典：
            - total_records: 总记录数
            - total_attempts: 总尝试次数
            - successful: 成功次数
            - failed: 失败次数
            - qa_pairs: 生成的问答对列表
            - errors: 错误列表
        """
        results = {
            "total_records": len(bank_records),
            "total_attempts": 0,
            "successful": 0,
            "failed": 0,
            "qa_pairs": [],
            "errors": []
        }
        
        logger.info(
            f"开始批量生成问答对 - "
            f"记录数: {len(bank_records)}, 类型: {question_types}"
        )
        
        start_time = time.time()
        
        for record in bank_records:
            for question_type in question_types:
                results["total_attempts"] += 1
                
                qa_pair = self.generate_qa_pair(record, question_type)
                
                if qa_pair:
                    question, answer = qa_pair
                    results["successful"] += 1
                    results["qa_pairs"].append({
                        "record_id": record.id,
                        "question_type": question_type,
                        "question": question,
                        "answer": answer
                    })
                else:
                    results["failed"] += 1
                    results["errors"].append({
                        "record_id": record.id,
                        "question_type": question_type,
                        "error": "所有重试后生成失败"
                    })
        
        elapsed_time = time.time() - start_time
        
        logger.info(
            f"批量问答对生成完成 - "
            f"总计: {results['total_attempts']}, "
            f"成功: {results['successful']}, "
            f"失败: {results['failed']}, "
            f"耗时: {elapsed_time:.2f}秒"
        )
        
        return results
    
    def _generate_local_qa_pair(self, bank_record: BankCode, question_type: str) -> tuple[str, str]:
        """
        使用本地模板生成问答对
        
        Args:
            bank_record: 联行号记录对象
            question_type: 问题类型（exact/fuzzy/reverse/natural）
        
        Returns:
            元组 (问题, 答案)
        """
        import random
        
        # 基本信息
        bank_name = bank_record.bank_name
        bank_code = bank_record.bank_code
        clearing_code = getattr(bank_record, 'clearing_code', bank_code)
        
        # 问题模板
        question_templates = {
            "exact": [
                f"{bank_name}的联行号是什么？",
                f"请问{bank_name}的银行代码是多少？",
                f"{bank_name}的清算代码是什么？",
                f"我需要{bank_name}的联行号信息",
            ],
            "fuzzy": [
                f"{bank_name}的代码",
                f"{bank_name}联行号",
                f"查询{bank_name}",
                f"{bank_name}银行信息",
            ],
            "reverse": [
                f"{bank_code}是哪个银行的联行号？",
                f"联行号{bank_code}对应哪家银行？",
                f"银行代码{bank_code}是什么银行？",
                f"这个联行号{bank_code}属于哪个银行？",
            ],
            "natural": [
                f"我想查询{bank_name}的联行号信息",
                f"请帮我找一下{bank_name}的银行代码",
                f"能告诉我{bank_name}的清算代码吗？",
                f"我需要办理业务，请问{bank_name}的联行号是多少？",
            ]
        }
        
        # 选择问题模板
        templates = question_templates.get(question_type, question_templates["exact"])
        question = random.choice(templates)
        
        # 生成答案
        if question_type == "reverse":
            answer = f"联行号{bank_code}属于{bank_name}。"
        else:
            answer_parts = [f"{bank_name}的相关信息如下："]
            answer_parts.append(f"联行号：{bank_code}")
            
            if clearing_code and clearing_code != bank_code:
                answer_parts.append(f"清算代码：{clearing_code}")
            
            answer = "\n".join(answer_parts)
        
        logger.info(f"本地生成问答对成功 - 记录ID: {bank_record.id}, 类型: {question_type}")
        return question, answer
