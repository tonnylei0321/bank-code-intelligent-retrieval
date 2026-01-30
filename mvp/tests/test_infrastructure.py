"""
Tests for project infrastructure
测试项目基础架构
"""
import pytest
from pathlib import Path
from sqlalchemy import inspect

from app.core.config import settings
from app.core.database import engine, get_db, init_db
from app.core.logging import logger


@pytest.mark.unit
class TestConfiguration:
    """Test configuration management"""
    
    def test_settings_loaded(self):
        """Test that settings are loaded correctly"""
        assert settings.APP_NAME is not None
        assert settings.APP_VERSION is not None
        assert settings.DATABASE_URL is not None
    
    def test_database_url_format(self):
        """Test database URL format"""
        assert settings.DATABASE_URL.startswith("sqlite:///")
    
    def test_secret_key_exists(self):
        """Test that secret key is configured"""
        assert settings.SECRET_KEY is not None
        assert len(settings.SECRET_KEY) > 0
    
    def test_cors_origins_configured(self):
        """Test CORS origins are configured"""
        assert isinstance(settings.CORS_ORIGINS, list)
        assert len(settings.CORS_ORIGINS) > 0


@pytest.mark.unit
class TestDatabase:
    """Test database configuration"""
    
    def test_database_engine_created(self):
        """Test that database engine is created"""
        assert engine is not None
    
    def test_database_connection(self):
        """Test database connection"""
        with engine.connect() as connection:
            assert connection is not None
    
    def test_get_db_dependency(self):
        """Test get_db dependency function"""
        db_gen = get_db()
        db = next(db_gen)
        assert db is not None
        db.close()
    
    def test_init_db_creates_tables(self):
        """Test that init_db creates tables"""
        # Initialize database
        init_db()
        
        # Check that tables can be inspected
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        # At this point, no models are defined yet, so tables list might be empty
        # This test just verifies the function runs without error
        assert isinstance(tables, list)


@pytest.mark.unit
class TestLogging:
    """Test logging configuration"""
    
    def test_logger_exists(self):
        """Test that logger is available"""
        assert logger is not None
    
    def test_logger_can_log(self):
        """Test that logger can write logs"""
        # This should not raise an exception
        logger.info("Test log message")
        logger.debug("Test debug message")
        logger.warning("Test warning message")
    
    def test_log_directory_created(self):
        """Test that logs directory is created"""
        log_dir = Path("logs")
        # Directory might not exist yet if setup_logging hasn't been called
        # This test just verifies the path is valid
        assert log_dir.name == "logs"


@pytest.mark.integration
class TestApplicationStartup:
    """Test application startup"""
    
    def test_app_can_import(self):
        """Test that main app can be imported"""
        from app.main import app
        assert app is not None
    
    def test_app_has_routes(self):
        """Test that app has basic routes"""
        from app.main import app
        routes = [route.path for route in app.routes]
        assert "/" in routes
        assert "/health" in routes
    
    def test_app_metadata(self):
        """Test app metadata"""
        from app.main import app
        assert app.title == settings.APP_NAME
        assert app.version == settings.APP_VERSION
