"""
数据库初始化脚本
"""

from sqlalchemy.orm import Session
from app.core.database import engine, Base
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.system import SystemConfig
import logging

logger = logging.getLogger(__name__)


def init_database():
    """初始化数据库"""
    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        logger.info("✅ 数据库表创建成功")
        
        # 导入所有模型以确保表被创建
        from app.models import user, dataset, training, model, qa, system
        
        return True
    except Exception as e:
        logger.error(f"❌ 数据库表创建失败: {e}")
        return False


def create_default_admin(db: Session):
    """创建默认管理员用户"""
    try:
        # 检查是否已存在管理员
        admin = db.query(User).filter(User.username == "admin").first()
        if admin:
            logger.info("管理员用户已存在")
            return
        
        # 创建默认管理员
        admin_user = User(
            username="admin",
            email="admin@example.com",
            password_hash=get_password_hash("admin123"),
            role=UserRole.ADMIN,
            is_active=True
        )
        
        db.add(admin_user)
        db.commit()
        logger.info("✅ 默认管理员用户创建成功 (admin/admin123)")
        
    except Exception as e:
        logger.error(f"❌ 创建默认管理员失败: {e}")
        db.rollback()


def create_default_configs(db: Session):
    """创建默认系统配置"""
    try:
        default_configs = [
            {
                "config_key": "max_concurrent_training",
                "config_value": "5",
                "config_type": "number",
                "description": "最大并发训练任务数"
            },
            {
                "config_key": "default_batch_size",
                "config_value": "16",
                "config_type": "number",
                "description": "默认批处理大小"
            },
            {
                "config_key": "default_learning_rate",
                "config_value": "2e-4",
                "config_type": "string",
                "description": "默认学习率"
            },
            {
                "config_key": "upload_max_size",
                "config_value": "104857600",
                "config_type": "number",
                "description": "文件上传最大大小(字节)"
            },
            {
                "config_key": "model_accuracy_threshold",
                "config_value": "0.999",
                "config_type": "string",
                "description": "模型准确率阈值"
            }
        ]
        
        for config_data in default_configs:
            # 检查配置是否已存在
            existing = db.query(SystemConfig).filter(
                SystemConfig.config_key == config_data["config_key"]
            ).first()
            
            if not existing:
                config = SystemConfig(**config_data)
                db.add(config)
        
        db.commit()
        logger.info("✅ 默认系统配置创建成功")
        
    except Exception as e:
        logger.error(f"❌ 创建默认配置失败: {e}")
        db.rollback()


def initialize_database():
    """完整的数据库初始化流程"""
    from app.core.database import SessionLocal
    
    logger.info("=" * 50)
    logger.info("开始初始化数据库")
    logger.info("=" * 50)
    
    # 1. 创建表
    if not init_database():
        return False
    
    # 2. 创建默认数据
    db = SessionLocal()
    try:
        create_default_admin(db)
        create_default_configs(db)
        
        logger.info("=" * 50)
        logger.info("数据库初始化完成！")
        logger.info("=" * 50)
        return True
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    initialize_database()