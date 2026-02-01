"""
智能问答系统配置

管理Redis、小模型和智能问答服务的配置参数
"""

import os
from typing import Dict, Any, Optional
from pydantic import BaseSettings, Field


class RedisConfig(BaseSettings):
    """Redis配置"""
    
    # Redis连接配置
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL",
        description="Redis连接URL"
    )
    
    # Redis连接参数
    connection_timeout: int = Field(
        default=10,
        env="REDIS_CONNECTION_TIMEOUT",
        description="连接超时时间（秒）"
    )
    
    socket_timeout: int = Field(
        default=5,
        env="REDIS_SOCKET_TIMEOUT",
        description="Socket超时时间（秒）"
    )
    
    max_connections: int = Field(
        default=20,
        env="REDIS_MAX_CONNECTIONS",
        description="最大连接数"
    )
    
    # Redis数据管理
    key_prefix: str = Field(
        default="bank_code:",
        env="REDIS_KEY_PREFIX",
        description="Redis键前缀"
    )
    
    default_ttl: int = Field(
        default=86400,
        env="REDIS_DEFAULT_TTL",
        description="默认过期时间（秒）"
    )
    
    batch_size: int = Field(
        default=1000,
        env="REDIS_BATCH_SIZE",
        description="批处理大小"
    )
    
    class Config:
        env_file = ".env"


class SmallModelConfig(BaseSettings):
    """小模型配置"""
    
    # OpenAI配置
    openai_api_key: Optional[str] = Field(
        default=None,
        env="OPENAI_API_KEY",
        description="OpenAI API密钥"
    )
    
    openai_base_url: Optional[str] = Field(
        default=None,
        env="OPENAI_BASE_URL",
        description="OpenAI API基础URL"
    )
    
    # Anthropic配置
    anthropic_api_key: Optional[str] = Field(
        default=None,
        env="ANTHROPIC_API_KEY",
        description="Anthropic API密钥"
    )
    
    # 本地模型配置
    local_model_name: str = Field(
        default="microsoft/DialoGPT-medium",
        env="LOCAL_MODEL_NAME",
        description="本地模型名称"
    )
    
    local_model_cache_dir: str = Field(
        default="./models/cache",
        env="LOCAL_MODEL_CACHE_DIR",
        description="本地模型缓存目录"
    )
    
    # 模型参数
    default_temperature: float = Field(
        default=0.1,
        env="MODEL_DEFAULT_TEMPERATURE",
        description="默认生成温度"
    )
    
    default_max_tokens: int = Field(
        default=512,
        env="MODEL_DEFAULT_MAX_TOKENS",
        description="默认最大生成长度"
    )
    
    request_timeout: int = Field(
        default=30,
        env="MODEL_REQUEST_TIMEOUT",
        description="请求超时时间（秒）"
    )
    
    retry_attempts: int = Field(
        default=3,
        env="MODEL_RETRY_ATTEMPTS",
        description="重试次数"
    )
    
    # 设备配置
    device: str = Field(
        default="auto",
        env="MODEL_DEVICE",
        description="计算设备 (auto, cpu, cuda)"
    )
    
    class Config:
        env_file = ".env"


class IntelligentQAConfig(BaseSettings):
    """智能问答服务配置"""
    
    # 检索配置
    default_retrieval_strategy: str = Field(
        default="intelligent",
        env="QA_DEFAULT_RETRIEVAL_STRATEGY",
        description="默认检索策略"
    )
    
    max_context_results: int = Field(
        default=5,
        env="QA_MAX_CONTEXT_RESULTS",
        description="最大上下文结果数量"
    )
    
    redis_search_limit: int = Field(
        default=10,
        env="QA_REDIS_SEARCH_LIMIT",
        description="Redis搜索结果限制"
    )
    
    rag_search_limit: int = Field(
        default=5,
        env="QA_RAG_SEARCH_LIMIT",
        description="RAG搜索结果限制"
    )
    
    # 答案质量配置
    answer_confidence_threshold: float = Field(
        default=0.7,
        env="QA_ANSWER_CONFIDENCE_THRESHOLD",
        description="答案置信度阈值"
    )
    
    quality_threshold: float = Field(
        default=0.8,
        env="QA_QUALITY_THRESHOLD",
        description="质量阈值"
    )
    
    # 历史记录配置
    enable_history: bool = Field(
        default=True,
        env="QA_ENABLE_HISTORY",
        description="是否启用历史记录"
    )
    
    history_limit: int = Field(
        default=100,
        env="QA_HISTORY_LIMIT",
        description="历史记录限制"
    )
    
    # 缓存配置
    cache_answers: bool = Field(
        default=True,
        env="QA_CACHE_ANSWERS",
        description="是否缓存答案"
    )
    
    cache_ttl: int = Field(
        default=3600,
        env="QA_CACHE_TTL",
        description="缓存过期时间（秒）"
    )
    
    # 性能配置
    enable_learning: bool = Field(
        default=True,
        env="QA_ENABLE_LEARNING",
        description="是否启用学习功能"
    )
    
    fallback_to_rag: bool = Field(
        default=True,
        env="QA_FALLBACK_TO_RAG",
        description="是否回退到RAG"
    )
    
    class Config:
        env_file = ".env"


class IntelligentQASettings:
    """智能问答系统设置管理器"""
    
    def __init__(self):
        self.redis_config = RedisConfig()
        self.model_config = SmallModelConfig()
        self.qa_config = IntelligentQAConfig()
    
    def get_redis_config(self) -> Dict[str, Any]:
        """获取Redis配置字典"""
        return {
            "redis_url": self.redis_config.redis_url,
            "connection_timeout": self.redis_config.connection_timeout,
            "socket_timeout": self.redis_config.socket_timeout,
            "max_connections": self.redis_config.max_connections,
            "key_prefix": self.redis_config.key_prefix,
            "default_ttl": self.redis_config.default_ttl,
            "batch_size": self.redis_config.batch_size,
        }
    
    def get_model_config(self) -> Dict[str, Any]:
        """获取模型配置字典"""
        return {
            "openai_api_key": self.model_config.openai_api_key,
            "openai_base_url": self.model_config.openai_base_url,
            "anthropic_api_key": self.model_config.anthropic_api_key,
            "local_model_name": self.model_config.local_model_name,
            "local_model_cache_dir": self.model_config.local_model_cache_dir,
            "temperature": self.model_config.default_temperature,
            "max_tokens": self.model_config.default_max_tokens,
            "timeout": self.model_config.request_timeout,
            "retry_attempts": self.model_config.retry_attempts,
            "device": self._resolve_device(),
        }
    
    def get_qa_config(self) -> Dict[str, Any]:
        """获取问答服务配置字典"""
        return {
            "default_retrieval_strategy": self.qa_config.default_retrieval_strategy,
            "max_context_results": self.qa_config.max_context_results,
            "redis_search_limit": self.qa_config.redis_search_limit,
            "rag_search_limit": self.qa_config.rag_search_limit,
            "answer_confidence_threshold": self.qa_config.answer_confidence_threshold,
            "quality_threshold": self.qa_config.quality_threshold,
            "enable_history": self.qa_config.enable_history,
            "history_limit": self.qa_config.history_limit,
            "cache_answers": self.qa_config.cache_answers,
            "cache_ttl": self.qa_config.cache_ttl,
            "enable_learning": self.qa_config.enable_learning,
            "fallback_to_rag": self.qa_config.fallback_to_rag,
        }
    
    def _resolve_device(self) -> str:
        """解析计算设备"""
        device = self.model_config.device.lower()
        
        if device == "auto":
            try:
                import torch
                return "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                return "cpu"
        
        return device
    
    def validate_config(self) -> Dict[str, Any]:
        """验证配置并返回验证结果"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # 验证Redis配置
        if not self.redis_config.redis_url:
            validation_result["errors"].append("Redis URL未配置")
            validation_result["valid"] = False
        
        # 验证模型配置
        if not any([
            self.model_config.openai_api_key,
            self.model_config.anthropic_api_key,
            self.model_config.local_model_name
        ]):
            validation_result["warnings"].append("未配置任何模型API密钥，将仅使用本地模型")
        
        # 验证设备配置
        device = self._resolve_device()
        if device == "cuda":
            try:
                import torch
                if not torch.cuda.is_available():
                    validation_result["warnings"].append("CUDA不可用，将使用CPU")
            except ImportError:
                validation_result["warnings"].append("PyTorch未安装，无法使用本地模型")
        
        return validation_result
    
    def get_all_config(self) -> Dict[str, Any]:
        """获取所有配置"""
        return {
            "redis": self.get_redis_config(),
            "model": self.get_model_config(),
            "qa": self.get_qa_config(),
            "validation": self.validate_config()
        }


# 全局配置实例
intelligent_qa_settings = IntelligentQASettings()