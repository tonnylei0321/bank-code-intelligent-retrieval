"""
应用配置管理模块

本模块使用Pydantic Settings管理应用配置，支持从环境变量和.env文件加载配置。
所有配置项都有类型注解和默认值，确保配置的类型安全。
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    应用配置类
    
    从环境变量加载应用配置。配置项包括：
    - 应用基本信息（名称、版本、调试模式）
    - 数据库连接配置
    - 安全认证配置（JWT密钥、算法）
    - 大模型API配置（通义千问）
    - Elasticsearch配置
    - 模型路径配置
    - 训练参数配置
    - API限流配置
    - 文件上传配置
    
    所有配置项都可以通过环境变量或.env文件设置。
    """
    
    # 应用基本配置
    APP_NAME: str = "Bank Code Retrieval System"  # 应用名称
    APP_VERSION: str = "1.0.0"  # 应用版本
    DEBUG: bool = False  # 调试模式开关
    LOG_LEVEL: str = "INFO"  # 日志级别（DEBUG/INFO/WARNING/ERROR）
    
    # 数据库配置
    DATABASE_URL: str = "sqlite:///./data/bank_code.db"  # 数据库连接URL（SQLite）
    
    # 安全认证配置
    SECRET_KEY: str  # JWT密钥（必须通过环境变量设置）
    ALGORITHM: str = "HS256"  # JWT加密算法
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24  # 访问令牌过期时间（小时）
    
    # 大模型API配置（通义千问）
    QWEN_API_KEY: str = ""  # 通义千问API密钥
    QWEN_API_URL: str = ""  # API端点（优先使用）
    QWEN_ENDPOINT: str = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"  # API端点（兼容旧配置）
    
    @property
    def qwen_api_url(self) -> str:
        """获取通义千问API URL，优先使用QWEN_API_URL，否则使用QWEN_ENDPOINT"""
        return self.QWEN_API_URL or self.QWEN_ENDPOINT
    
    # Elasticsearch配置（基准检索系统）
    ELASTICSEARCH_URL: str = "http://localhost:9200"  # Elasticsearch服务地址
    ELASTICSEARCH_INDEX: str = "bank_codes"  # 索引名称
    
    # 模型路径配置
    BASE_MODEL_PATH: str = "./models/base/qwen3-0.6b"  # 基础模型路径（Qwen3-0.6B）
    FINETUNED_MODEL_PATH: str = "./models/finetuned"  # 微调模型保存路径
    
    # 训练参数配置
    MAX_CONCURRENT_TRAINING: int = 1  # 最大并发训练任务数
    DEFAULT_BATCH_SIZE: int = 16  # 默认批次大小
    DEFAULT_LEARNING_RATE: float = 2e-4  # 默认学习率
    DEFAULT_LORA_R: int = 16  # LoRA秩（rank）
    DEFAULT_LORA_ALPHA: int = 32  # LoRA缩放参数
    
    # API配置
    API_RATE_LIMIT: int = 100  # API限流（请求数/分钟）
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]  # 允许的跨域来源
    
    # 文件上传配置
    UPLOAD_DIR: str = "./uploads"  # 上传文件保存目录
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 最大上传文件大小（100MB）
    
    model_config = SettingsConfigDict(
        env_file=".env",  # 从.env文件加载配置
        env_file_encoding="utf-8",  # 文件编码
        case_sensitive=True,  # 环境变量名称区分大小写
        extra="ignore"  # 忽略额外的环境变量
    )


# 全局配置实例
# 在应用启动时自动加载环境变量和.env文件中的配置
settings = Settings()
