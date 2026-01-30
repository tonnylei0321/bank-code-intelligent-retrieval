"""
数据库连接和会话管理

本模块负责SQLAlchemy数据库引擎和会话的创建和管理。

功能：
    - 创建SQLite数据库引擎
    - 配置连接池和会话工厂
    - 提供数据库会话依赖注入
    - 数据库初始化

使用方式：
    # 在API端点中使用
    from app.core.database import get_db
    
    @router.get("/items")
    def get_items(db: Session = Depends(get_db)):
        return db.query(Item).all()
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import logging
import os

from app.core.config import settings

logger = logging.getLogger(__name__)

# 确保数据目录存在
os.makedirs("./data", exist_ok=True)

# 创建数据库引擎（SQLite配置）
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite特定配置
    pool_pre_ping=True,
    echo=settings.DEBUG
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"数据库会话错误: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    初始化数据库
    """
    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        logger.info("数据库初始化成功")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise