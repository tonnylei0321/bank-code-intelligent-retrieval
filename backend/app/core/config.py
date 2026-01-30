"""
应用配置管理

本模块使用Pydantic Settings管理应用配置，支持从环境变量和.env文件读取配置。

配置分类：
    - 基础配置：项目名称、版本、环境、日志级别
    - 安全配置：密钥、JWT配置
    - 数据库配置：数据库连接URL
    - Redis配置：Redis连接URL
    - CORS配置：允许的主机列表
    - 文件存储配置：上传限制、存储路径
    - 大模型API配置：通义千问、DeepSeek、豆包API
    - 训练配置：并发数、批次大小、学习率、轮数
    - LoRA配置：秩、alpha、dropout、目标模块
    - 模型配置：基础模型名称、准确率阈值
    - Celery配置：消息队列配置
    - 监控配置：指标收集、Prometheus端口

使用方式：
    from app.core.config import settings
    print(settings.PROJECT_NAME)
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """应用配置"""
    
    # 基础配置
    PROJECT_NAME: str = "企业级小模型训练平台"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # 安全配置
    SECRET_KEY: str = "your_secret_key_here"
    JWT_SECRET_KEY: str = "jwt_secret_key_here"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # 数据库配置
    DATABASE_URL: str = "sqlite:///./data/training_platform.db"
    
    # Redis配置
    REDIS_URL: str = "redis://:redis_password_123@localhost:6379/0"
    
    # CORS配置
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # 文件存储配置
    UPLOAD_MAX_SIZE: int = 104857600  # 100MB
    UPLOAD_ALLOWED_EXTENSIONS: List[str] = [".csv", ".txt", ".xlsx", ".xls"]
    DATA_STORAGE_PATH: str = "/app/uploads"
    MODEL_STORAGE_PATH: str = "/app/models"
    LOG_STORAGE_PATH: str = "/app/logs"
    
    # 大模型API配置
    QWEN_API_KEY: Optional[str] = None
    QWEN_API_URL: str = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_API_URL: str = "https://api.deepseek.com/v1/chat/completions"
    
    DOUBAO_API_KEY: Optional[str] = None
    DOUBAO_API_URL: str = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    
    # 训练配置
    MAX_CONCURRENT_TRAINING: int = 5
    DEFAULT_BATCH_SIZE: int = 16
    DEFAULT_LEARNING_RATE: float = 2e-4
    DEFAULT_NUM_EPOCHS: int = 3
    DEFAULT_WARMUP_STEPS: int = 100
    
    # LoRA配置
    DEFAULT_LORA_R: int = 16
    DEFAULT_LORA_ALPHA: int = 32
    DEFAULT_LORA_DROPOUT: float = 0.1
    DEFAULT_LORA_TARGET_MODULES: List[str] = ["q_proj", "v_proj", "k_proj", "o_proj"]
    
    # 模型配置
    BASE_MODEL_NAME: str = "Qwen/Qwen2-0.5B"
    MODEL_ACCURACY_THRESHOLD: float = 0.999
    
    # Celery配置
    CELERY_BROKER_URL: str = "redis://:redis_password_123@localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://:redis_password_123@localhost:6379/0"
    
    # 监控配置
    METRICS_ENABLED: bool = True
    PROMETHEUS_PORT: int = 9090
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建配置实例
settings = Settings()


# 确保目录存在
def ensure_directories():
    """确保必要的目录存在"""
    directories = [
        settings.DATA_STORAGE_PATH,
        settings.MODEL_STORAGE_PATH,
        settings.LOG_STORAGE_PATH,
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


# 初始化时创建目录
ensure_directories()