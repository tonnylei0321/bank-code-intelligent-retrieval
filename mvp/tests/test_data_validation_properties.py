"""
Property-based tests for data validation
数据验证的属性测试

Feature: bank-code-retrieval, Property 1: 数据验证完整性
"""
import pytest
import io
import tempfile
import os
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

from app.core.database import Base
from app.models.dataset import Dataset
from app.models.bank_code import BankCode
from app.services.data_manager import DataManager


# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_validation_properties.db"
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


def create_csv_content(valid_records: list, invalid_records: list) -> bytes:
    """
    Create CSV content with valid and invalid records
    
    Args:
        valid_records: List of tuples (bank_name, bank_code, clearing_code)
        invalid_records: List of invalid row strings
        
    Returns:
        CSV content as bytes
    """
    content = io.StringIO()
    
    # Add valid records
    for bank_name, bank_code, clearing_code in valid_records:
        # Ensure bank_name doesn't look like a header
        if bank_name and not bank_name.lower().replace('_', '').replace(' ', '') in ['bankname', 'name', '银行名称']:
            content.write(f"{bank_name},{bank_code},{clearing_code}\n")
    
    # Add invalid records
    for invalid_row in invalid_records:
        content.write(f"{invalid_row}\n")
    
    return content.getvalue().encode('utf-8')


@pytest.mark.property
class TestDataValidationProperties:
    """Property-based tests for data validation"""
    
    @given(
        valid_count=st.integers(min_value=2, max_value=100),  # At least 2 valid records to avoid header detection
        invalid_count=st.integers(min_value=0, max_value=50)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_validation_completeness(self, valid_count, invalid_count):
        """
        Feature: bank-code-retrieval, Property 1: 数据验证完整性
        
        For any uploaded file, the validation statistics should satisfy:
        total_records = valid_records + invalid_records
        
        Property: Validation statistics are complete and consistent
        """
        # At least one valid record required to avoid header detection issues
        
        with get_test_db() as test_db:
            # Generate valid records
            valid_records = []
            for i in range(valid_count):
                bank_name = f"中国工商银行分行{i}"
                bank_code = f"{102100000000 + i:012d}"
                clearing_code = f"{102100000000 + (i // 10):012d}"
                valid_records.append((bank_name, bank_code, clearing_code))
            
            # Generate invalid records
            invalid_records = []
            for i in range(invalid_count):
                if i % 3 == 0:
                    # Missing column
                    invalid_records.append(f"银行{i},12345")
                elif i % 3 == 1:
                    # Invalid bank code (not 12 digits)
                    invalid_records.append(f"银行{i},123,123456789012")
                else:
                    # Empty bank name
                    invalid_records.append(f",123456789012,123456789012")
            
            # Create CSV file
            csv_content = create_csv_content(valid_records, invalid_records)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as f:
                f.write(csv_content)
                temp_file_path = f.name
            
            try:
                # Create dataset record
                dataset = Dataset(
                    filename="test.csv",
                    file_path=temp_file_path,
                    file_size=len(csv_content),
                    total_records=0,
                    valid_records=0,
                    invalid_records=0,
                    status='uploaded'
                )
                test_db.add(dataset)
                test_db.commit()
                test_db.refresh(dataset)
                
                # Validate data
                data_manager = DataManager(test_db)
                total, valid, invalid, errors = data_manager.validate_data(dataset.id)
                
                # Property 1: total_records = valid_records + invalid_records
                assert total == valid + invalid, \
                    f"Total records ({total}) != valid ({valid}) + invalid ({invalid})"
                
                # Verify counts match expected
                assert total == valid_count + invalid_count, \
                    f"Total records ({total}) != expected ({valid_count + invalid_count})"
                assert valid == valid_count, \
                    f"Valid records ({valid}) != expected ({valid_count})"
                assert invalid == invalid_count, \
                    f"Invalid records ({invalid}) != expected ({invalid_count})"
                
                # Verify all valid records are in database
                db_records = test_db.query(BankCode).filter(
                    BankCode.dataset_id == dataset.id
                ).all()
                assert len(db_records) == valid_count, \
                    f"Database has {len(db_records)} records, expected {valid_count}"
                
                # Verify all valid records have required fields
                for record in db_records:
                    assert record.bank_name is not None and len(record.bank_name) > 0
                    assert record.bank_code is not None and len(record.bank_code) == 12
                    assert record.clearing_code is not None and len(record.clearing_code) == 12
            
            finally:
                # Cleanup temporary file
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
    
    @given(
        valid_count=st.integers(min_value=2, max_value=50)  # At least 2 records to avoid header detection issues
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_all_valid_records_have_required_fields(self, valid_count):
        """
        Feature: bank-code-retrieval, Property 1: 数据验证完整性
        
        For any set of valid records, all records in the database should have
        bank_name, bank_code (12 digits), and clearing_code (12 digits).
        
        Property: All valid records have required fields
        """
        with get_test_db() as test_db:
            # Generate realistic valid records with Chinese bank names
            valid_records = []
            banks = ["中国工商银行", "中国农业银行", "中国银行", "中国建设银行", "交通银行"]
            cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "西安"]
            
            for i in range(valid_count):
                bank = banks[i % len(banks)]
                city = cities[i % len(cities)]
                bank_name = f"{bank}{city}分行{i}"
                bank_code = f"{102100000000 + i:012d}"
                clearing_code = f"{102100000000 + (i // 10):012d}"
                valid_records.append((bank_name, bank_code, clearing_code))
            # Create CSV content
            csv_content = create_csv_content(valid_records, [])
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as f:
                f.write(csv_content)
                temp_file_path = f.name
            
            try:
                # Create dataset
                dataset = Dataset(
                    filename="test.csv",
                    file_path=temp_file_path,
                    file_size=len(csv_content),
                    total_records=0,
                    valid_records=0,
                    invalid_records=0,
                    status='uploaded'
                )
                test_db.add(dataset)
                test_db.commit()
                test_db.refresh(dataset)
                
                # Validate data
                data_manager = DataManager(test_db)
                total, valid, invalid, errors = data_manager.validate_data(dataset.id)
                
                # All records should be valid
                assert valid == len(valid_records)
                assert invalid == 0
                
                # Check all records in database
                db_records = test_db.query(BankCode).filter(
                    BankCode.dataset_id == dataset.id
                ).all()
                
                for record in db_records:
                    # Verify required fields exist and are valid
                    assert record.bank_name is not None
                    assert len(record.bank_name) > 0
                    assert record.bank_code is not None
                    assert len(record.bank_code) == 12
                    assert record.bank_code.isdigit()
                    assert record.clearing_code is not None
                    assert len(record.clearing_code) == 12
                    assert record.clearing_code.isdigit()
            
            finally:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
    
    @given(
        invalid_type=st.sampled_from(['missing_column', 'invalid_code', 'empty_name'])
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_invalid_records_are_rejected(self, invalid_type):
        """
        Feature: bank-code-retrieval, Property 1: 数据验证完整性
        
        For any invalid record type, the validation should reject it and
        count it as invalid.
        
        Property: Invalid records are correctly identified and rejected
        """
        with get_test_db() as test_db:
            # Create two valid records and one invalid record to avoid header detection
            valid_records = [
                ("中国工商银行北京分行", "102100000026", "102100000000"),
                ("中国农业银行上海分行", "103100000027", "103100000000")
            ]
            
            if invalid_type == 'missing_column':
                invalid_records = ["中国农业银行,103100000026"]  # Missing clearing_code
            elif invalid_type == 'invalid_code':
                invalid_records = ["中国银行,1031,103100000026"]  # Invalid bank_code (not 12 digits)
            else:  # empty_name
                invalid_records = [",104100000026,104100000000"]  # Empty bank_name
            
            csv_content = create_csv_content(valid_records, invalid_records)
            
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as f:
                f.write(csv_content)
                temp_file_path = f.name
            
            try:
                dataset = Dataset(
                    filename="test.csv",
                    file_path=temp_file_path,
                    file_size=len(csv_content),
                    total_records=0,
                    valid_records=0,
                    invalid_records=0,
                    status='uploaded'
                )
                test_db.add(dataset)
                test_db.commit()
                test_db.refresh(dataset)
                
                data_manager = DataManager(test_db)
                total, valid, invalid, errors = data_manager.validate_data(dataset.id)
                
                # Should have 2 valid and 1 invalid record
                assert total == 3
                assert valid == 2
                assert invalid == 1
                assert len(errors) > 0
                
                # Only valid records should be in database
                db_records = test_db.query(BankCode).filter(
                    BankCode.dataset_id == dataset.id
                ).all()
                assert len(db_records) == 2
            
            finally:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
    
    @given(
        record_count=st.integers(min_value=2, max_value=100)  # At least 2 records to avoid header detection issues
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_dataset_status_updated_after_validation(self, record_count):
        """
        Feature: bank-code-retrieval, Property 1: 数据验证完整性
        
        For any dataset, after validation the status should be updated to 'validated'.
        
        Property: Dataset status is updated after validation
        """
        with get_test_db() as test_db:
            # Generate valid records
            valid_records = []
            for i in range(record_count):
                valid_records.append((
                    f"银行{i}",
                    f"{102100000000 + i:012d}",
                    f"{102100000000:012d}"
                ))
            
            csv_content = create_csv_content(valid_records, [])
            
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as f:
                f.write(csv_content)
                temp_file_path = f.name
            
            try:
                dataset = Dataset(
                    filename="test.csv",
                    file_path=temp_file_path,
                    file_size=len(csv_content),
                    total_records=0,
                    valid_records=0,
                    invalid_records=0,
                    status='uploaded'
                )
                test_db.add(dataset)
                test_db.commit()
                test_db.refresh(dataset)
                
                # Verify initial status
                assert dataset.status == 'uploaded'
                
                # Validate
                data_manager = DataManager(test_db)
                data_manager.validate_data(dataset.id)
                
                # Refresh dataset from database
                test_db.refresh(dataset)
                
                # Verify status updated
                assert dataset.status == 'validated'
                assert dataset.total_records == record_count
                assert dataset.valid_records == record_count
                assert dataset.invalid_records == 0
            
            finally:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
