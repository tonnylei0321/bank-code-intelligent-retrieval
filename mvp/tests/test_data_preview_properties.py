"""
Property-based tests for data preview
数据预览的属性测试

Feature: bank-code-retrieval, Property 2: 数据预览边界
"""
import pytest
import tempfile
import os
from hypothesis import given, strategies as st, settings, HealthCheck
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

from app.core.database import Base
from app.models.dataset import Dataset
from app.models.bank_code import BankCode
from app.services.data_manager import DataManager


# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_preview_properties.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_test_db():
    """Context manager for test database"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def create_test_dataset_with_records(db, record_count: int) -> Dataset:
    """
    Create a test dataset with specified number of records
    
    Args:
        db: Database session
        record_count: Number of records to create
        
    Returns:
        Dataset object
    """
    # Create dataset
    dataset = Dataset(
        filename="test.csv",
        file_path="/tmp/test.csv",
        file_size=1000,
        total_records=record_count,
        valid_records=record_count,
        invalid_records=0,
        status='validated'
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    
    # Create bank code records
    for i in range(record_count):
        bank_code = BankCode(
            dataset_id=dataset.id,
            bank_name=f"中国工商银行分行{i}",
            bank_code=f"{102100000000 + i:012d}",
            clearing_code=f"{102100000000:012d}",
            is_valid=1
        )
        db.add(bank_code)
    
    db.commit()
    
    return dataset


@pytest.mark.property
class TestDataPreviewProperties:
    """Property-based tests for data preview"""
    
    @given(
        record_count=st.integers(min_value=0, max_value=200)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_preview_boundary(self, record_count):
        """
        Feature: bank-code-retrieval, Property 2: 数据预览边界
        
        For any dataset, the number of records returned by preview should equal
        min(total_records, 100).
        
        Property: Preview returns at most 100 records
        """
        with get_test_db() as test_db:
            # Create dataset with specified number of records
            dataset = create_test_dataset_with_records(test_db, record_count)
            
            # Preview data
            data_manager = DataManager(test_db)
            preview_records = data_manager.preview_data(dataset.id)
            
            # Property: len(preview_records) == min(record_count, 100)
            expected_count = min(record_count, 100)
            assert len(preview_records) == expected_count, \
                f"Preview returned {len(preview_records)} records, expected {expected_count}"
    
    @given(
        record_count=st.integers(min_value=0, max_value=200),
        limit=st.integers(min_value=1, max_value=150)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=500)
    def test_preview_with_custom_limit(self, record_count, limit):
        """
        Feature: bank-code-retrieval, Property 2: 数据预览边界
        
        For any dataset and any limit, the number of records returned should equal
        min(total_records, limit).
        
        Property: Preview respects custom limit
        """
        with get_test_db() as test_db:
            # Create dataset with specified number of records
            dataset = create_test_dataset_with_records(test_db, record_count)
            
            # Preview data with custom limit
            data_manager = DataManager(test_db)
            preview_records = data_manager.preview_data(dataset.id, limit=limit)
            
            # Property: len(preview_records) == min(record_count, limit)
            expected_count = min(record_count, limit)
            assert len(preview_records) == expected_count, \
                f"Preview returned {len(preview_records)} records, expected {expected_count}"
    
    @given(
        record_count=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_preview_returns_valid_records(self, record_count):
        """
        Feature: bank-code-retrieval, Property 2: 数据预览边界
        
        For any dataset, all records returned by preview should be valid
        BankCode records with required fields.
        
        Property: Preview returns valid records
        """
        with get_test_db() as test_db:
            # Create dataset with specified number of records
            dataset = create_test_dataset_with_records(test_db, record_count)
            
            # Preview data
            data_manager = DataManager(test_db)
            preview_records = data_manager.preview_data(dataset.id)
            
            # Verify all records are valid
            for record in preview_records:
                assert record.bank_name is not None
                assert len(record.bank_name) > 0
                assert record.bank_code is not None
                assert len(record.bank_code) == 12
                assert record.bank_code.isdigit()
                assert record.clearing_code is not None
                assert len(record.clearing_code) == 12
                assert record.clearing_code.isdigit()
    
    @given(
        record_count=st.integers(min_value=0, max_value=200)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_preview_empty_dataset(self, record_count):
        """
        Feature: bank-code-retrieval, Property 2: 数据预览边界
        
        For any dataset with 0 records, preview should return an empty list.
        
        Property: Preview of empty dataset returns empty list
        """
        with get_test_db() as test_db:
            # Create dataset with 0 records
            dataset = create_test_dataset_with_records(test_db, 0)
            
            # Preview data
            data_manager = DataManager(test_db)
            preview_records = data_manager.preview_data(dataset.id)
            
            # Should return empty list
            assert len(preview_records) == 0, \
                f"Preview of empty dataset returned {len(preview_records)} records, expected 0"
