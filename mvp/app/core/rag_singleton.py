"""
RAG服务单例管理器

本模块实现RAG服务的单例模式，避免重复初始化嵌入模型，提升性能。
"""
from typing import Optional
from sqlalchemy.orm import Session
from loguru import logger

from app.services.rag_service import RAGService


class RAGServiceSingleton:
    """
    RAG服务单例管理器
    
    确保整个应用中只有一个RAG服务实例，避免重复加载嵌入模型。
    """
    
    _instance: Optional[RAGService] = None
    _initialized: bool = False
    
    @classmethod
    def get_instance(cls, db: Session) -> RAGService:
        """
        获取RAG服务单例实例
        
        Args:
            db: 数据库会话
        
        Returns:
            RAG服务实例
        """
        if cls._instance is None or not cls._initialized:
            logger.info("Creating new RAG service singleton instance...")
            cls._instance = RAGService(db)
            cls._initialized = True
            logger.info("RAG service singleton instance created successfully")
        else:
            # 更新数据库会话（因为每次请求的db会话可能不同）
            cls._instance.db = db
        
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """
        重置单例实例（用于测试或重新初始化）
        """
        logger.info("Resetting RAG service singleton instance...")
        cls._instance = None
        cls._initialized = False
    
    @classmethod
    def is_initialized(cls) -> bool:
        """
        检查是否已初始化
        
        Returns:
            是否已初始化
        """
        return cls._initialized and cls._instance is not None


# 便捷函数
def get_rag_service(db: Session) -> RAGService:
    """
    获取RAG服务实例的便捷函数
    
    Args:
        db: 数据库会话
    
    Returns:
        RAG服务实例
    """
    return RAGServiceSingleton.get_instance(db)