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
from typing import Optional, Dict, Any
from datetime import datetime
import httpx
from loguru import logger

from app.core.config import settings
from app.models.bank_code import BankCode


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
        model: str = "qwen-turbo"
    ):
        """
        初始化大模型API客户端
        
        Args:
            api_key: API密钥，用于认证（默认使用settings.QWEN_API_KEY）
            api_url: API端点URL（默认使用settings.qwen_api_url）
            max_retries: 最大重试次数，默认3次
            timeout: 请求超时时间（秒），默认30秒
            model: 使用的模型名称，默认"qwen-turbo"
        """
        self.api_key = api_key or settings.QWEN_API_KEY
        self.api_url = api_url or settings.qwen_api_url
        self.max_retries = max_retries
        self.timeout = timeout
        self.model = model
        
        # 验证配置
        if not self.api_key or self.api_key.strip() == "":
            logger.error("❌ QWEN_API_KEY未配置或为空 - QA对生成将失败！")
            logger.error("请在.env文件中设置: QWEN_API_KEY=your_api_key_here")
        else:
            logger.info(f"✅ QWEN_API_KEY已配置（长度: {len(self.api_key)}）")
        
        if not self.api_url or self.api_url.strip() == "":
            logger.error("❌ QWEN API URL未配置 - 请检查QWEN_ENDPOINT或QWEN_API_URL")
        else:
            logger.info(f"✅ QWEN API URL: {self.api_url}")
        
        logger.info(
            f"大模型API客户端已初始化 - 模型: {self.model}, "
            f"最大重试次数: {self.max_retries}, 超时: {self.timeout}秒"
        )
    
    def _build_prompt(self, bank_record: BankCode, question_type: str) -> str:
        """
        构建生成问答对的提示词
        
        根据不同的问题类型，构建相应的提示词模板。
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
        调用通义千问API
        
        发送HTTP POST请求到通义千问API，处理各种错误情况。
        
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
        headers = {
            "Authorization": f"Bearer {self.api_key}",
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
                
                # 检查HTTP错误
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
                
                # 解析响应
                result = response.json()
                
                # 从响应中提取文本
                # 通义千问API响应格式: {"output": {"choices": [{"message": {"content": "..."}}]}}
                if "output" not in result:
                    raise TeacherModelAPIError(f"API响应格式无效: {result}")
                
                output = result["output"]
                if "choices" not in output or len(output["choices"]) == 0:
                    raise TeacherModelAPIError(f"API响应中没有choices: {result}")
                
                message = output["choices"][0].get("message", {})
                content = message.get("content", "")
                
                if not content:
                    raise TeacherModelAPIError(f"API响应内容为空: {result}")
                
                return content
        
        except httpx.TimeoutException as e:
            raise APITimeoutError(f"API请求超时（{self.timeout}秒）") from e
        except httpx.RequestError as e:
            raise TeacherModelAPIError(f"API请求失败: {str(e)}") from e
    
    def generate_qa_pair(
        self,
        bank_record: BankCode,
        question_type: str
    ) -> Optional[tuple[str, str]]:
        """
        为联行号记录生成问答对，带重试机制
        
        使用指数退避策略进行重试：
        - 第1次失败：等待1秒后重试
        - 第2次失败：等待2秒后重试
        - 第3次失败：等待4秒后重试
        
        Args:
            bank_record: 联行号记录对象
            question_type: 问题类型（exact/fuzzy/reverse/natural）
        
        Returns:
            元组 (问题, 答案)，如果所有重试都失败则返回None
        """
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
                # 认证错误不可重试
                logger.error(f"API认证失败: {e}")
                return None
            
            except (APIRateLimitError, APITimeoutError, TeacherModelAPIError) as e:
                logger.warning(
                    f"API调用失败（尝试 {attempt + 1}/{self.max_retries}）: {e}"
                )
                
                if attempt < self.max_retries - 1:
                    # 指数退避：2^attempt 秒
                    wait_time = 2 ** attempt
                    logger.info(f"{wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"问答对生成失败，已重试{self.max_retries}次 - "
                        f"记录ID: {bank_record.id}, 类型: {question_type}"
                    )
                    return None
            
            except ValueError as e:
                # 响应解析错误
                logger.error(f"API响应解析失败: {e}")
                
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"{wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"问答对生成失败，已重试{self.max_retries}次 - "
                        f"记录ID: {bank_record.id}, 类型: {question_type}"
                    )
                    return None
            
            except Exception as e:
                # 意外错误
                logger.exception(
                    f"生成问答对时发生意外错误 - "
                    f"记录ID: {bank_record.id}, 类型: {question_type}: {e}"
                )
                return None
        
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
