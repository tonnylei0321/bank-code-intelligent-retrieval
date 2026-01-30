"""
Tests for database models
数据库模型测试
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from app.core.database import Base
from app.models.user import User
from app.models.dataset import Dataset
from app.models.bank_code import BankCode
from app.core.security import get_password_hash


# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_models.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def test_db():
    """Create test database and tables"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


class TestUserModel:
    """Test User model"""
    
    def test_create_user(self, test_db):
        """Test creating a user"""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=get_password_hash("password123"),
            role="user",
            is_active=1
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == "user"
        assert user.is_active == 1
        assert user.created_at is not None
    
    def test_user_properties(self, test_db):
        """Test user property methods"""
        admin = User(
            username="admin",
            email="admin@example.com",
            hashed_password=get_password_hash("admin123"),
            role="admin",
            is_active=1
        )
        test_db.add(admin)
        test_db.commit()
        
        assert admin.is_admin is True
        assert admin.is_user is False


class TestDatasetModel:
    """Test Dataset model"""
    
    def test_create_dataset(self, test_db):
        """Test creating a dataset"""
        # Create user first
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=get_password_hash("password123"),
            role="user",
            is_active=1
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        # Create dataset
        dataset = Dataset(
            filename="test_data.csv",
            file_path="/uploads/test_data.csv",
            file_size=1024,
            total_records=100,
            valid_records=95,
            invalid_records=5,
            status="uploaded",
            uploaded_by=user.id
        )
        test_db.add(dataset)
        test_db.commit()
        test_db.refresh(dataset)
        
        assert dataset.id is not None
        assert dataset.filename == "test_data.csv"
        assert dataset.file_path == "/uploads/test_data.csv"
        assert dataset.file_size == 1024
        assert dataset.total_records == 100
        assert dataset.valid_records == 95
        assert dataset.invalid_records == 5
        assert dataset.status == "uploaded"
        assert dataset.uploaded_by == user.id
        assert dataset.created_at is not None
    
    def test_dataset_properties(self, test_db):
        """Test dataset property methods"""
        dataset = Dataset(
            filename="test.csv",
            file_path="/uploads/test.csv",
            file_size=1024,
            total_records=100,
            valid_records=100,
            invalid_records=0,
            status="validated"
        )
        test_db.add(dataset)
        test_db.commit()
        
        assert dataset.is_uploaded is False
        assert dataset.is_validated is True
        assert dataset.is_indexed is False
    
    def test_dataset_relationship_with_user(self, test_db):
        """Test dataset relationship with user"""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=get_password_hash("password123"),
            role="user",
            is_active=1
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        dataset = Dataset(
            filename="test.csv",
            file_path="/uploads/test.csv",
            file_size=1024,
            total_records=100,
            valid_records=100,
            invalid_records=0,
            uploaded_by=user.id
        )
        test_db.add(dataset)
        test_db.commit()
        test_db.refresh(dataset)
        
        # Test relationship
        assert dataset.uploader is not None
        assert dataset.uploader.username == "testuser"


class TestBankCodeModel:
    """Test BankCode model"""
    
    def test_create_bank_code(self, test_db):
        """Test creating a bank code record"""
        # Create dataset first
        dataset = Dataset(
            filename="test.csv",
            file_path="/uploads/test.csv",
            file_size=1024,
            total_records=1,
            valid_records=1,
            invalid_records=0
        )
        test_db.add(dataset)
        test_db.commit()
        test_db.refresh(dataset)
        
        # Create bank code
        bank_code = BankCode(
            dataset_id=dataset.id,
            bank_name="中国工商银行北京分行",
            bank_code="102100000026",
            clearing_code="102100000000",
            is_valid=1
        )
        test_db.add(bank_code)
        test_db.commit()
        test_db.refresh(bank_code)
        
        assert bank_code.id is not None
        assert bank_code.dataset_id == dataset.id
        assert bank_code.bank_name == "中国工商银行北京分行"
        assert bank_code.bank_code == "102100000026"
        assert bank_code.clearing_code == "102100000000"
        assert bank_code.is_valid == 1
        assert bank_code.created_at is not None
    
    def test_bank_code_properties(self, test_db):
        """Test bank code property methods"""
        bank_code = BankCode(
            bank_name="中国工商银行",
            bank_code="102100000026",
            clearing_code="102100000000",
            is_valid=1
        )
        test_db.add(bank_code)
        test_db.commit()
        
        assert bank_code.is_active is True
    
    def test_bank_code_to_dict(self, test_db):
        """Test bank code to_dict method"""
        bank_code = BankCode(
            bank_name="中国工商银行",
            bank_code="102100000026",
            clearing_code="102100000000",
            is_valid=1
        )
        test_db.add(bank_code)
        test_db.commit()
        test_db.refresh(bank_code)
        
        data = bank_code.to_dict()
        assert data["id"] == bank_code.id
        assert data["bank_name"] == "中国工商银行"
        assert data["bank_code"] == "102100000026"
        assert data["clearing_code"] == "102100000000"
        assert data["is_valid"] is True
    
    def test_bank_code_relationship_with_dataset(self, test_db):
        """Test bank code relationship with dataset"""
        dataset = Dataset(
            filename="test.csv",
            file_path="/uploads/test.csv",
            file_size=1024,
            total_records=1,
            valid_records=1,
            invalid_records=0
        )
        test_db.add(dataset)
        test_db.commit()
        test_db.refresh(dataset)
        
        bank_code = BankCode(
            dataset_id=dataset.id,
            bank_name="中国工商银行",
            bank_code="102100000026",
            clearing_code="102100000000"
        )
        test_db.add(bank_code)
        test_db.commit()
        test_db.refresh(bank_code)
        
        # Test relationship
        assert bank_code.dataset is not None
        assert bank_code.dataset.filename == "test.csv"
        
        # Test reverse relationship
        assert len(dataset.bank_codes) == 1
        assert dataset.bank_codes[0].bank_code == "102100000026"
    
    def test_bank_code_cascade_delete(self, test_db):
        """Test that bank codes are deleted when dataset is deleted"""
        dataset = Dataset(
            filename="test.csv",
            file_path="/uploads/test.csv",
            file_size=1024,
            total_records=2,
            valid_records=2,
            invalid_records=0
        )
        test_db.add(dataset)
        test_db.commit()
        test_db.refresh(dataset)
        
        # Add bank codes
        bank_code1 = BankCode(
            dataset_id=dataset.id,
            bank_name="中国工商银行",
            bank_code="102100000026",
            clearing_code="102100000000"
        )
        bank_code2 = BankCode(
            dataset_id=dataset.id,
            bank_name="中国农业银行",
            bank_code="103100000026",
            clearing_code="103100000000"
        )
        test_db.add(bank_code1)
        test_db.add(bank_code2)
        test_db.commit()
        
        # Verify bank codes exist
        assert test_db.query(BankCode).filter(BankCode.dataset_id == dataset.id).count() == 2
        
        # Delete dataset
        test_db.delete(dataset)
        test_db.commit()
        
        # Verify bank codes are also deleted (cascade)
        assert test_db.query(BankCode).filter(BankCode.dataset_id == dataset.id).count() == 0
    
    def test_bank_code_unique_constraint(self, test_db):
        """Test unique constraint on (bank_code, dataset_id)"""
        dataset = Dataset(
            filename="test.csv",
            file_path="/uploads/test.csv",
            file_size=1024,
            total_records=1,
            valid_records=1,
            invalid_records=0
        )
        test_db.add(dataset)
        test_db.commit()
        test_db.refresh(dataset)
        
        # Add first bank code
        bank_code1 = BankCode(
            dataset_id=dataset.id,
            bank_name="中国工商银行",
            bank_code="102100000026",
            clearing_code="102100000000"
        )
        test_db.add(bank_code1)
        test_db.commit()
        
        # Try to add duplicate bank code in same dataset
        bank_code2 = BankCode(
            dataset_id=dataset.id,
            bank_name="中国工商银行北京分行",  # Different name
            bank_code="102100000026",  # Same code
            clearing_code="102100000000"
        )
        test_db.add(bank_code2)
        
        # Should raise integrity error
        with pytest.raises(Exception):  # SQLAlchemy IntegrityError
            test_db.commit()
