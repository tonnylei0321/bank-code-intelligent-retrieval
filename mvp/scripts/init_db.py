"""
Database initialization script
初始化数据库并创建默认管理员账户
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine, Base, SessionLocal
from app.core.logging import setup_logging, logger
from app.models.user import User
from app.core.security import get_password_hash


def init_database():
    """Initialize database and create tables"""
    logger.info("Initializing database...")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")


def create_default_admin():
    """Create default admin user if not exists"""
    db = SessionLocal()
    try:
        # Check if admin already exists
        admin = db.query(User).filter(User.username == "admin").first()
        if admin:
            logger.info("Admin user already exists")
            return
        
        # Create admin user
        admin = User(
            username="admin",
            email="admin@example.com",
            hashed_password=get_password_hash("admin123"),
            role="admin",
            is_active=1
        )
        db.add(admin)
        db.commit()
        logger.info("Default admin user created (username: admin, password: admin123)")
        logger.warning("⚠️  Please change the default admin password after first login!")
        
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()


def main():
    """Main initialization function"""
    setup_logging()
    logger.info("Starting database initialization...")
    
    try:
        init_database()
        create_default_admin()
        logger.info("✅ Database initialization completed successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
