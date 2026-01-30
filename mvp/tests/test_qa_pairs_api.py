"""
Tests for QA Pairs API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.models.qa_pair import QAPair
from app.core.deps import get_db, get_current_user, get_current_admin_user


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Create mock database session"""
    db = Mock(spec=Session)
    db.query = Mock()
    db.add = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    return db


@pytest.fixture
def mock_admin_user():
    """Create mock admin user"""
    user = Mock(spec=User)
    user.id = 1
    user.username = "admin"
    user.email = "admin@test.com"
    user.role = "admin"
    user.is_active = 1
    user.is_admin = True
    return user


@pytest.fixture
def mock_regular_user():
    """Create mock regular user"""
    user = Mock(spec=User)
    user.id = 2
    user.username = "user"
    user.email = "user@test.com"
    user.role = "user"
    user.is_active = 1
    user.is_admin = False
    return user


@pytest.fixture
def mock_qa_pairs():
    """Create mock QA pairs"""
    pairs = []
    for i in range(10):
        qa = Mock(spec=QAPair)
        qa.id = i + 1
        qa.dataset_id = 1
        qa.source_record_id = i + 1
        qa.question = f"Question {i+1}?"
        qa.answer = f"Answer {i+1}"
        qa.question_type = ["exact", "fuzzy", "reverse", "natural"][i % 4]
        qa.split_type = ["train", "val", "test"][i % 3]
        qa.generated_at = "2024-01-01T00:00:00"
        pairs.append(qa)
    return pairs


class TestQAPairsAPI:
    """Test suite for QA Pairs API"""
    
    def test_generate_qa_pairs_success(self, client, mock_db, mock_admin_user):
        """Test successful QA pair generation"""
        # Override dependencies
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_admin_user] = lambda: mock_admin_user
        
        # Mock QA Generator
        with patch('app.api.qa_pairs.QAGenerator') as mock_generator_class:
            mock_generator = Mock()
            mock_generator_class.return_value = mock_generator
            
            # Mock generation results
            mock_generator.generate_for_dataset.return_value = {
                'dataset_id': 1,
                'total_attempts': 40,
                'successful': 40,
                'failed': 0,
                'failed_records': []
            }
            
            # Mock split results
            mock_generator.split_dataset.return_value = {
                'train_count': 32,
                'val_count': 4,
                'test_count': 4
            }
            
            # Mock stats
            mock_generator.get_generation_stats.return_value = {
                'total_qa_pairs': 40,
                'by_question_type': {
                    'exact': 10,
                    'fuzzy': 10,
                    'reverse': 10,
                    'natural': 10
                },
                'by_split_type': {
                    'train': 32,
                    'val': 4,
                    'test': 4
                }
            }
            
            # Make request
            response = client.post(
                "/api/v1/qa-pairs/generate",
                json={
                    "dataset_id": 1,
                    "question_types": ["exact", "fuzzy", "reverse", "natural"],
                    "train_ratio": 0.8,
                    "val_ratio": 0.1,
                    "test_ratio": 0.1
                }
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["dataset_id"] == 1
            assert data["total_generated"] == 40
            assert data["train_count"] == 32
            assert data["val_count"] == 4
            assert data["test_count"] == 4
            assert data["question_type_counts"]["exact"] == 10
        
        # Clean up
        app.dependency_overrides.clear()
    
    def test_generate_qa_pairs_invalid_ratios(self, client, mock_db, mock_admin_user):
        """Test generation with invalid split ratios"""
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_admin_user] = lambda: mock_admin_user
        
        response = client.post(
            "/api/v1/qa-pairs/generate",
            json={
                "dataset_id": 1,
                "question_types": ["exact"],
                "train_ratio": 0.7,
                "val_ratio": 0.2,
                "test_ratio": 0.2  # Sum = 1.1
            }
        )
        
        assert response.status_code == 400
        assert "Split ratios must sum to 1.0" in response.json()["detail"]
        
        app.dependency_overrides.clear()
    
    def test_generate_qa_pairs_not_admin(self, client, mock_db, mock_regular_user):
        """Test generation by non-admin user (should fail)"""
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_regular_user
        
        response = client.post(
            "/api/v1/qa-pairs/generate",
            json={"dataset_id": 1}
        )
        
        # Should fail due to admin requirement
        assert response.status_code in [401, 403]
        
        app.dependency_overrides.clear()
    
    def test_get_qa_pair_stats(self, client, mock_db, mock_regular_user):
        """Test getting QA pair statistics"""
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_regular_user
        
        with patch('app.api.qa_pairs.QAGenerator') as mock_generator_class:
            mock_generator = Mock()
            mock_generator_class.return_value = mock_generator
            
            mock_generator.get_generation_stats.return_value = {
                'total_qa_pairs': 40,
                'by_question_type': {
                    'exact': 10,
                    'fuzzy': 10,
                    'reverse': 10,
                    'natural': 10
                },
                'by_split_type': {
                    'train': 32,
                    'val': 4,
                    'test': 4
                }
            }
            
            response = client.get("/api/v1/qa-pairs/1/stats")
            
            assert response.status_code == 200
            data = response.json()
            assert data["dataset_id"] == 1
            assert data["total_pairs"] == 40
            assert data["train_pairs"] == 32
            assert data["val_pairs"] == 4
            assert data["test_pairs"] == 4
            assert data["exact_pairs"] == 10
        
        app.dependency_overrides.clear()
    
    def test_get_qa_pairs_with_pagination(self, client, mock_db, mock_regular_user, mock_qa_pairs):
        """Test getting QA pairs with pagination"""
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_regular_user
        
        # Mock query chain
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_qa_pairs[:5]
        
        response = client.get("/api/v1/qa-pairs/1?skip=0&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
        
        app.dependency_overrides.clear()
    
    def test_get_qa_pairs_with_filters(self, client, mock_db, mock_regular_user, mock_qa_pairs):
        """Test getting QA pairs with filters"""
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_regular_user
        
        # Mock query chain
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        # Filter by question_type
        filtered_pairs = [qa for qa in mock_qa_pairs if qa.question_type == "exact"]
        mock_query.all.return_value = filtered_pairs
        
        response = client.get("/api/v1/qa-pairs/1?question_type=exact")
        
        assert response.status_code == 200
        data = response.json()
        assert all(qa["question_type"] == "exact" for qa in data)
        
        app.dependency_overrides.clear()
    
    def test_get_qa_pairs_invalid_question_type(self, client, mock_db, mock_regular_user):
        """Test getting QA pairs with invalid question type"""
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_regular_user
        
        response = client.get("/api/v1/qa-pairs/1?question_type=invalid")
        
        assert response.status_code == 400
        assert "Invalid question_type" in response.json()["detail"]
        
        app.dependency_overrides.clear()
    
    def test_get_qa_pairs_invalid_split_type(self, client, mock_db, mock_regular_user):
        """Test getting QA pairs with invalid split type"""
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_regular_user
        
        response = client.get("/api/v1/qa-pairs/1?split_type=invalid")
        
        assert response.status_code == 400
        assert "Invalid split_type" in response.json()["detail"]
        
        app.dependency_overrides.clear()
    
    def test_delete_qa_pairs_success(self, client, mock_db, mock_admin_user):
        """Test successful deletion of QA pairs"""
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_admin_user] = lambda: mock_admin_user
        
        # Mock query chain
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 40
        mock_query.delete.return_value = 40
        
        response = client.delete("/api/v1/qa-pairs/1")
        
        assert response.status_code == 204
        mock_db.commit.assert_called_once()
        
        app.dependency_overrides.clear()
    
    def test_delete_qa_pairs_not_found(self, client, mock_db, mock_admin_user):
        """Test deletion when no QA pairs exist"""
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_admin_user] = lambda: mock_admin_user
        
        # Mock query chain
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        
        response = client.delete("/api/v1/qa-pairs/1")
        
        assert response.status_code == 404
        assert "No QA pairs found" in response.json()["detail"]
        
        app.dependency_overrides.clear()
    
    def test_delete_qa_pairs_not_admin(self, client, mock_db, mock_regular_user):
        """Test deletion by non-admin user (should fail)"""
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_regular_user
        
        response = client.delete("/api/v1/qa-pairs/1")
        
        # Should fail due to admin requirement
        assert response.status_code in [401, 403]
        
        app.dependency_overrides.clear()
    
    def test_export_qa_pairs_all(self, client, mock_db, mock_admin_user, mock_qa_pairs):
        """Test exporting all QA pairs"""
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_admin_user] = lambda: mock_admin_user
        
        # Mock query chain
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_qa_pairs
        
        response = client.get("/api/v1/qa-pairs/1/export")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10
        
        app.dependency_overrides.clear()
    
    def test_export_qa_pairs_by_split(self, client, mock_db, mock_admin_user, mock_qa_pairs):
        """Test exporting QA pairs filtered by split type"""
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_admin_user] = lambda: mock_admin_user
        
        # Mock query chain
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        
        # Filter by split_type
        train_pairs = [qa for qa in mock_qa_pairs if qa.split_type == "train"]
        mock_query.all.return_value = train_pairs
        
        response = client.get("/api/v1/qa-pairs/1/export?split_type=train")
        
        assert response.status_code == 200
        data = response.json()
        assert all(qa["split_type"] == "train" for qa in data)
        
        app.dependency_overrides.clear()
    
    def test_export_qa_pairs_invalid_split(self, client, mock_db, mock_admin_user):
        """Test exporting with invalid split type"""
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_admin_user] = lambda: mock_admin_user
        
        response = client.get("/api/v1/qa-pairs/1/export?split_type=invalid")
        
        assert response.status_code == 400
        assert "Invalid split_type" in response.json()["detail"]
        
        app.dependency_overrides.clear()
    
    def test_export_qa_pairs_not_admin(self, client, mock_db, mock_regular_user):
        """Test export by non-admin user (should fail)"""
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_regular_user
        
        response = client.get("/api/v1/qa-pairs/1/export")
        
        # Should fail due to admin requirement
        assert response.status_code in [401, 403]
        
        app.dependency_overrides.clear()
