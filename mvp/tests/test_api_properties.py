"""
Property-based tests for API features
API功能的属性测试

Tests:
- Property 21: API响应格式统一性
- Property 22: 频率限制执行
- Property 23: 模型持久化一致性
- Property 24: 事务原子性
"""
import pytest
from hypothesis import given, strategies as st, settings
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import time
import os
from pathlib import Path

from app.main import app
from app.core.database import Base, get_db
from app.core.rate_limiter import RateLimiter
from app.models.user import User
from app.models.training_job import TrainingJob
from app.core.security import get_password_hash
from app.core.transaction import verify_model_consistency


# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_api_properties.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Setup test database before each test"""
    # Remove existing test database
    if os.path.exists("test_api_properties.db"):
        os.remove("test_api_properties.db")
    
    Base.metadata.create_all(bind=engine)
    
    # Create test users
    db = TestingSessionLocal()
    try:
        # Create admin user
        admin = User(
            username="test_admin",
            email="admin@test.com",
            hashed_password=get_password_hash("admin123"),
            role="admin",
            is_active=1
        )
        db.add(admin)
        
        # Create regular user
        user = User(
            username="test_user",
            email="user@test.com",
            hashed_password=get_password_hash("user123"),
            role="user",
            is_active=1
        )
        db.add(user)
        
        db.commit()
    except Exception as e:
        print(f"Error setting up database: {e}")
        db.rollback()
    finally:
        db.close()
    
    yield
    
    # Cleanup
    try:
        Base.metadata.drop_all(bind=engine)
        if os.path.exists("test_api_properties.db"):
            os.remove("test_api_properties.db")
    except Exception as e:
        print(f"Error cleaning up database: {e}")


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def admin_token(client):
    """Get admin authentication token"""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "test_admin", "password": "admin123"}
    )
    return response.json()["access_token"]


@pytest.fixture
def user_token(client):
    """Get user authentication token"""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "test_user", "password": "user123"}
    )
    return response.json()["access_token"]


# Property 22: 频率限制执行
# Feature: bank-code-retrieval, Property 22: 频率限制执行
@settings(max_examples=10, deadline=None)
@given(
    request_count=st.integers(min_value=95, max_value=110)
)
def test_rate_limit_enforcement(client, admin_token, request_count):
    """
    Property 22: 频率限制执行
    Validates: Requirements 9.4
    
    For any user, after exceeding 100 requests per minute,
    the 101st request should return 429 status code.
    """
    # Reset rate limiter before test
    from app.main import rate_limiter
    rate_limiter.reset_all()
    
    # Make requests
    responses = []
    for i in range(request_count):
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        responses.append(response)
        
        # Small delay to avoid overwhelming the system
        if i % 10 == 0:
            time.sleep(0.01)
    
    # Count status codes
    status_200_count = sum(1 for r in responses if r.status_code == 200)
    status_429_count = sum(1 for r in responses if r.status_code == 429)
    
    # Property: If request_count > 100, there should be 429 responses
    if request_count > 100:
        assert status_429_count > 0, \
            f"Expected 429 responses after 100 requests, got {status_429_count}"
        
        # Check that 429 responses have proper format
        for response in responses:
            if response.status_code == 429:
                data = response.json()
                assert "error_code" in data
                assert data["error_code"] == "RATE_LIMIT_EXCEEDED"
                assert "retry_after" in data
                assert isinstance(data["retry_after"], int)
                assert data["retry_after"] > 0
    else:
        # All requests should succeed if under limit
        assert status_429_count == 0, \
            f"No 429 responses expected for {request_count} requests"


# Property 21: API响应格式统一性
# Feature: bank-code-retrieval, Property 21: API响应格式统一性
@settings(max_examples=20, deadline=None)
@given(
    endpoint_choice=st.sampled_from([
        "success",  # Successful request
        "not_found",  # 404 error
        "unauthorized",  # 401 error
        "forbidden",  # 403 error
        "validation_error"  # 422 error
    ])
)
def test_api_response_format_consistency(client, admin_token, user_token, endpoint_choice):
    """
    Property 21: API响应格式统一性
    Validates: Requirements 9.2, 9.3
    
    For any API call (success or failure), the response should have
    a unified JSON format with status code, message, and timestamp.
    """
    # Make different types of requests based on choice
    if endpoint_choice == "success":
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        expected_status = 200
        
    elif endpoint_choice == "not_found":
        response = client.get(
            "/api/v1/datasets/99999",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        expected_status = 404
        
    elif endpoint_choice == "unauthorized":
        response = client.get("/api/v1/auth/me")
        expected_status = 401
        
    elif endpoint_choice == "forbidden":
        # Regular user trying to access admin endpoint
        response = client.get(
            "/api/v1/datasets",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        expected_status = 403
        
    elif endpoint_choice == "validation_error":
        # Invalid data
        response = client.post(
            "/api/v1/auth/register",
            json={"username": ""},  # Invalid: empty username
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        expected_status = 422
    
    # Verify response format
    assert response.status_code == expected_status
    data = response.json()
    
    # All responses should have timestamp
    assert "timestamp" in data, "Response missing timestamp field"
    assert isinstance(data["timestamp"], str)
    
    # Check format based on success/failure
    if response.status_code >= 200 and response.status_code < 300:
        # Success response format
        assert "success" in data
        assert data["success"] is True
        # May have "data" field
    else:
        # Error response format
        assert "success" in data
        assert data["success"] is False
        assert "error_code" in data, "Error response missing error_code"
        assert "error_message" in data, "Error response missing error_message"
        assert isinstance(data["error_code"], str)
        assert isinstance(data["error_message"], str)


# Property 23: 模型持久化一致性
# Feature: bank-code-retrieval, Property 23: 模型持久化一致性
@settings(max_examples=10, deadline=None)
@given(
    model_exists=st.booleans(),
    record_exists=st.booleans()
)
def test_model_persistence_consistency(model_exists, record_exists):
    """
    Property 23: 模型持久化一致性
    Validates: Requirements 10.2
    
    For any saved model, the file system should have the corresponding
    weight file, and the database should have the corresponding file path record.
    """
    db = TestingSessionLocal()
    
    try:
        # Create test model path
        test_model_dir = Path("test_models")
        test_model_dir.mkdir(exist_ok=True)
        model_path = test_model_dir / "test_model.bin"
        
        # Create model file if needed
        if model_exists:
            with open(model_path, 'w') as f:
                f.write("test model data")
        
        # Create database record if needed
        if record_exists:
            job = TrainingJob(
                dataset_id=1,
                model_name="test_model",
                batch_size=16,
                learning_rate=0.0002,
                epochs=3,
                lora_r=16,
                lora_alpha=32,
                lora_dropout=0.05,
                status="completed",
                model_path=str(model_path) if model_exists else None
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            
            # Verify consistency
            is_consistent = verify_model_consistency(
                db, str(model_path), job.id, TrainingJob
            )
            
            # Property: Consistency should match expectations
            if model_exists and record_exists:
                assert is_consistent, \
                    "Model file and database record should be consistent"
            elif not model_exists and not record_exists:
                # Both missing is also consistent (no model yet)
                assert is_consistent, \
                    "No model file and no record path should be consistent"
            else:
                # Mismatch is inconsistent
                assert not is_consistent, \
                    "Mismatch between file and record should be detected"
        
        # Cleanup
        if model_path.exists():
            os.remove(model_path)
        if test_model_dir.exists():
            test_model_dir.rmdir()
    
    finally:
        db.close()


# Property 24: 事务原子性
# Feature: bank-code-retrieval, Property 24: 事务原子性
@settings(max_examples=10, deadline=None)
@given(
    should_fail=st.booleans()
)
def test_transaction_atomicity(should_fail):
    """
    Property 24: 事务原子性
    Validates: Requirements 10.3
    
    For any database transaction, if the operation fails,
    all related data changes should be rolled back, and the
    database state should be consistent with before the transaction.
    """
    from app.core.transaction import transaction_scope
    
    db = TestingSessionLocal()
    
    try:
        # Get initial user count
        initial_count = db.query(User).count()
        
        # Attempt transaction
        try:
            with transaction_scope(db) as session:
                # Add a new user
                new_user = User(
                    username=f"test_atomic_{time.time()}",
                    email=f"atomic_{time.time()}@test.com",
                    hashed_password=get_password_hash("test123"),
                    role="user",
                    is_active=1
                )
                session.add(new_user)
                
                # Force failure if needed
                if should_fail:
                    raise Exception("Simulated transaction failure")
                
                # Transaction commits automatically if no exception
        
        except Exception as e:
            # Expected if should_fail is True
            if not should_fail:
                raise
        
        # Check final count
        final_count = db.query(User).count()
        
        # Property: Transaction atomicity
        if should_fail:
            # Count should be unchanged (rollback occurred)
            assert final_count == initial_count, \
                f"Transaction should have rolled back: {initial_count} -> {final_count}"
        else:
            # Count should increase by 1 (commit occurred)
            assert final_count == initial_count + 1, \
                f"Transaction should have committed: {initial_count} -> {final_count}"
    
    finally:
        db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
