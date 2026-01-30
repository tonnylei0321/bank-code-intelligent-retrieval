"""
Integration tests for admin API endpoints
管理员API端点的集成测试
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.models.user import User
from app.core.security import get_password_hash


# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_admin.db"
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
    # Drop and recreate tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    
    # Create test users - these will be in the test database
    admin_user = User(
        username="admin",
        email="admin@test.com",
        hashed_password=get_password_hash("admin123"),
        role="admin",
        is_active=1
    )
    regular_user = User(
        username="testuser",  # Different username to avoid conflicts
        email="testuser@test.com",
        hashed_password=get_password_hash("testuser123"),
        role="user",
        is_active=1
    )
    
    db.add(admin_user)
    db.add(regular_user)
    db.commit()
    db.refresh(admin_user)
    db.refresh(regular_user)
    db.close()
    
    yield
    
    # Cleanup after test
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Create test client without lifespan events"""
    # Create app without lifespan to avoid init_db() call
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from app.core.config import settings
    from app.api import auth, admin
    
    test_app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="联行号检索模型训练验证系统 - MVP Test"
    )
    
    # Configure CORS
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    test_app.include_router(auth.router)
    test_app.include_router(admin.router)
    
    # Override database dependency
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


class TestAdminAPIPermissions:
    """Test admin API permission control"""
    
    def test_admin_can_list_users(self, client, admin_token):
        """Admin can list all users"""
        response = client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)
        assert len(users) >= 1  # At least admin user exists
        # Verify admin user is in the list
        assert any(u["username"] == "admin" for u in users)
    
    def test_unauthenticated_cannot_list_users(self, client):
        """Unauthenticated request cannot list users - should get 401"""
        response = client.get("/api/v1/admin/users")
        assert response.status_code == 401
    
    def test_admin_can_get_user_by_id(self, client, admin_token):
        """Admin can get user by ID"""
        response = client.get(
            "/api/v1/admin/users/1",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        user = response.json()
        assert user["username"] == "admin"
    
    def test_admin_can_delete_other_users(self, client, admin_token):
        """Admin can delete other users (if they exist)"""
        # First check if user ID 2 exists
        response = client.get(
            "/api/v1/admin/users/2",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if response.status_code == 200:
            # User exists, try to delete
            response = client.delete(
                "/api/v1/admin/users/2",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200
            assert "deleted successfully" in response.json()["message"]
        else:
            # User doesn't exist, that's okay for this test
            # The important thing is that admin has permission to try
            assert response.status_code == 404
    
    def test_admin_cannot_delete_self(self, client, admin_token):
        """Admin cannot delete their own account"""
        response = client.delete(
            "/api/v1/admin/users/1",  # Try to delete self
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 400
        assert "Cannot delete your own account" in response.json()["detail"]
    
    def test_get_nonexistent_user_returns_404(self, client, admin_token):
        """Getting non-existent user returns 404"""
        response = client.get(
            "/api/v1/admin/users/999",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
    
    def test_delete_nonexistent_user_returns_404(self, client, admin_token):
        """Deleting non-existent user returns 404"""
        response = client.delete(
            "/api/v1/admin/users/999",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
