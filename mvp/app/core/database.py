"""
数据库配置和会话管理模块

本模块负责：
1. 创建SQLAlchemy数据库引擎
2. 配置数据库会话工厂
3. 提供数据库会话依赖注入函数
4. 提供数据库初始化函数

使用SQLite作为数据库，支持调试模式下的SQL查询日志。
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from typing import Generator

from app.core.config import settings

# 创建SQLite数据库引擎
# check_same_thread=False: 允许多线程访问（SQLite默认限制）
# echo: 在调试模式下打印SQL查询语句
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite多线程支持
    echo=settings.DEBUG  # 调试模式下记录SQL查询
)

# 创建会话工厂
# autocommit=False: 需要显式提交事务
# autoflush=False: 需要显式刷新会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 数据模型基类
# 所有数据模型都应继承此基类
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话的依赖注入函数
    
    这是一个生成器函数，用于FastAPI的依赖注入系统。
    会话在请求处理完成后自动关闭，确保资源正确释放。
    
    使用示例:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    
    Yields:
        Session: SQLAlchemy数据库会话对象
    """
    db = SessionLocal()
    try:
        yield db  # 提供会话给请求处理函数
    finally:
        db.close()  # 请求处理完成后关闭会话


def init_db() -> None:
    """
    初始化数据库 - 创建所有数据表
    
    根据所有继承自Base的模型类定义，创建对应的数据库表。
    如果表已存在则不会重复创建。
    
    应在应用启动时调用此函数，通常在main.py的startup事件中。
    
    注意:
        - 此函数不会删除已存在的表
        - 不会自动迁移表结构变更
        - 生产环境建议使用Alembic进行数据库迁移
    """
    Base.metadata.create_all(bind=engine)
