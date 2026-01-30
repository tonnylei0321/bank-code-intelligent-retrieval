"""
Integration tests for data upload and validation
数据上传和验证的集成测试
"""
import pytest
import io
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.models.user import User
from app.models.dataset import Dataset
from app.models.bank_code import BankCode
from app.core.security import get_password_hash


# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_data_upload.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
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
def test_db():
    """Create test database and tables before each test"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    
    # Create admin user
    admin_user = User(
        username="admin",
        email="admin@test.com",
        hashed_password=get_password_hash("admin123"),
        role="admin",
        is_active=1
    )
    
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    db.close()
    
    yield
    
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Create test client"""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from app.core.config import settings
    from app.api import auth, admin, datasets
    
    test_app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Test App"
    )
    
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    test_app.include_router(auth.router)
    test_app.include_router(admin.router)
    test_app.include_router(datasets.router)
    
    test_app.dependency_overrides[get_db] = override_get_db
    
    return TestClient(test_app)


@pytest.fixture
def admin_token(client):
    """Get admin user token"""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def create_test_csv(valid_records: int = 5, invalid_records: int = 2) -> bytes:
    """Create a test CSV file with valid and invalid records"""
    content = io.StringIO()
    
    # Add valid records
    for i in range(valid_records):
        content.write(f"中国工商银行北京分行{i},10210000002{i},10210000000{i}\n")
    
    # Add invalid records
    for i in range(invalid_records):
        if i == 0:
            # Missing column
            content.write(f"中国农业银行,103100000026\n")
        else:
            # Invalid bank code (not 12 digits)
            content.write(f"中国银行,1031,103100000026\n")
    
    return content.getvalue().encode('utf-8')


class TestDataUpload:
    """Test data upload functionality"""
    
    def test_upload_csv_file(self, client, admin_token):
        """Test uploading a valid CSV file"""
        csv_content = create_test_csv(valid_records=5, invalid_records=0)
        
        response = client.post(
            "/api/v1/datasets/upload",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("test_data.csv", csv_content, "text/csv")}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "test_data.csv"
        assert data["status"] == "uploaded"
        assert data["file_size"] > 0
    
    def test_upload_non_csv_file(self, client, admin_token):
        """Test uploading a non-CSV file should fail"""
        response = client.post(
            "/api/v1/datasets/upload",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("test_data.txt", b"some content", "text/plain")}
        )
        
        assert response.status_code == 400
        assert "CSV" in response.json()["detail"]
    
    def test_upload_without_auth(self, client):
        """Test uploading without authentication should fail"""
        csv_content = create_test_csv()
        
        response = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("test_data.csv", csv_content, "text/csv")}
        )
        
        assert response.status_code == 401


class TestDataValidation:
    """Test data validation functionality"""
    
    def test_validate_dataset(self, client, admin_token):
        """Test validating a dataset"""
        # First upload a file
        csv_content = create_test_csv(valid_records=5, invalid_records=2)
        
        upload_response = client.post(
            "/api/v1/datasets/upload",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("test_data.csv", csv_content, "text/csv")}
        )
        
        assert upload_response.status_code == 201
        dataset_id = upload_response.json()["id"]
        
        # Validate the dataset
        validate_response = client.post(
            f"/api/v1/datasets/{dataset_id}/validate",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert validate_response.status_code == 200
        data = validate_response.json()
        assert data["dataset_id"] == dataset_id
        assert data["total_records"] == 7
        assert data["valid_records"] == 5
        assert data["invalid_records"] == 2
        assert data["status"] == "validated"
        assert len(data["errors"]) > 0
    
    def test_validate_nonexistent_dataset(self, client, admin_token):
        """Test validating a non-existent dataset should fail"""
        response = client.post(
            "/api/v1/datasets/999/validate",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 404


class TestDataPreview:
    """Test data preview functionality"""
    
    def test_preview_dataset(self, client, admin_token):
        """Test previewing dataset records"""
        # Upload and validate a dataset
        csv_content = create_test_csv(valid_records=10, invalid_records=0)
        
        upload_response = client.post(
            "/api/v1/datasets/upload",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("test_data.csv", csv_content, "text/csv")}
        )
        dataset_id = upload_response.json()["id"]
        
        client.post(
            f"/api/v1/datasets/{dataset_id}/validate",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Preview the data
        preview_response = client.get(
            f"/api/v1/datasets/{dataset_id}/preview",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert preview_response.status_code == 200
        data = preview_response.json()
        assert len(data) == 10
        assert "bank_name" in data[0]
        assert "bank_code" in data[0]
        assert "clearing_code" in data[0]
    
    def test_preview_with_limit(self, client, admin_token):
        """Test previewing dataset with limit"""
        # Upload and validate a dataset with 10 records
        csv_content = create_test_csv(valid_records=10, invalid_records=0)
        
        upload_response = client.post(
            "/api/v1/datasets/upload",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("test_data.csv", csv_content, "text/csv")}
        )
        dataset_id = upload_response.json()["id"]
        
        client.post(
            f"/api/v1/datasets/{dataset_id}/validate",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Preview with limit of 5
        preview_response = client.get(
            f"/api/v1/datasets/{dataset_id}/preview?limit=5",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert preview_response.status_code == 200
        data = preview_response.json()
        assert len(data) == 5


class TestDatasetStats:
    """Test dataset statistics functionality"""
    
    def test_get_dataset_stats(self, client, admin_token):
        """Test getting dataset statistics"""
        # Upload and validate a dataset
        csv_content = create_test_csv(valid_records=5, invalid_records=2)
        
        upload_response = client.post(
            "/api/v1/datasets/upload",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("test_data.csv", csv_content, "text/csv")}
        )
        dataset_id = upload_response.json()["id"]
        
        client.post(
            f"/api/v1/datasets/{dataset_id}/validate",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Get stats
        stats_response = client.get(
            f"/api/v1/datasets/{dataset_id}/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert stats_response.status_code == 200
        data = stats_response.json()
        assert data["id"] == dataset_id
        assert data["total_records"] == 7
        assert data["valid_records"] == 5
        assert data["invalid_records"] == 2
        assert data["status"] == "validated"
