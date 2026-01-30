"""
Tests for QA Generator Service
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.services.qa_generator import QAGenerator, QAGenerationError
from app.models.bank_code import BankCode
from app.models.qa_pair import QAPair
from app.models.dataset import Dataset


@pytest.fixture
def mock_db():
    """Create a mock database session"""
    db = Mock()
    db.query = Mock()
    db.add = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    return db


@pytest.fixture
def mock_teacher_api():
    """Create a mock teacher API"""
    api = Mock()
    api.generate_qa_pair = Mock()
    return api


@pytest.fixture
def mock_dataset():
    """Create a mock dataset"""
    dataset = Mock(spec=Dataset)
    dataset.id = 1
    dataset.filename = "test_data.csv"
    dataset.status = "validated"
    return dataset


@pytest.fixture
def mock_bank_records():
    """Create mock bank code records"""
    records = []
    for i in range(3):
        record = Mock(spec=BankCode)
        record.id = i + 1
        record.dataset_id = 1
        record.bank_name = f"测试银行{i+1}"
        record.bank_code = f"10210000000{i+1}"
        record.clearing_code = f"10210000000{i}"
        record.is_valid = 1
        records.append(record)
    return records


@pytest.fixture
def qa_generator(mock_db, mock_teacher_api):
    """Create QA Generator instance"""
    return QAGenerator(db=mock_db, teacher_api=mock_teacher_api)


class TestQAGenerator:
    """Test suite for QAGenerator"""
    
    def test_initialization(self, mock_db, mock_teacher_api):
        """Test QA generator initialization"""
        generator = QAGenerator(db=mock_db, teacher_api=mock_teacher_api)
        
        assert generator.db == mock_db
        assert generator.teacher_api == mock_teacher_api
    
    def test_initialization_with_default_api(self, mock_db):
        """Test QA generator initialization with default teacher API"""
        with patch('app.services.qa_generator.TeacherModelAPI') as mock_api_class:
            mock_api_instance = Mock()
            mock_api_class.return_value = mock_api_instance
            
            generator = QAGenerator(db=mock_db)
            
            assert generator.db == mock_db
            assert generator.teacher_api == mock_api_instance
            mock_api_class.assert_called_once()
    
    def test_generate_for_dataset_not_found(self, qa_generator, mock_db):
        """Test generation with non-existent dataset"""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(QAGenerationError, match="Dataset .* not found"):
            qa_generator.generate_for_dataset(dataset_id=999)
    
    def test_generate_for_dataset_no_records(self, qa_generator, mock_db, mock_dataset):
        """Test generation with dataset that has no valid records"""
        # Mock dataset query
        mock_db.query.return_value.filter.return_value.first.return_value = mock_dataset
        
        # Mock empty bank records query
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        with pytest.raises(QAGenerationError, match="No valid bank code records found"):
            qa_generator.generate_for_dataset(dataset_id=1)
    
    def test_generate_for_dataset_success(
        self,
        qa_generator,
        mock_db,
        mock_dataset,
        mock_bank_records,
        mock_teacher_api
    ):
        """Test successful QA pair generation"""
        # Setup mocks
        mock_db.query.return_value.filter.return_value.first.return_value = mock_dataset
        mock_db.query.return_value.filter.return_value.all.return_value = mock_bank_records
        
        # Mock successful QA generation
        mock_teacher_api.generate_qa_pair.return_value = ("Question?", "Answer")
        
        # Mock QA pair count query
        mock_db.query.return_value.filter.return_value.count.return_value = 12  # 3 records * 4 types
        
        # Generate
        results = qa_generator.generate_for_dataset(dataset_id=1)
        
        # Verify results
        assert results["dataset_id"] == 1
        assert results["total_records"] == 3
        assert results["question_types"] == ["exact", "fuzzy", "reverse", "natural"]
        assert results["total_attempts"] == 12  # 3 records * 4 types
        assert results["successful"] == 12
        assert results["failed"] == 0
        assert results["qa_pairs_created"] == 12
        assert len(results["failed_records"]) == 0
        
        # Verify database operations
        assert mock_db.add.call_count == 12
        mock_db.commit.assert_called_once()
    
    def test_generate_for_dataset_with_failures(
        self,
        qa_generator,
        mock_db,
        mock_dataset,
        mock_bank_records,
        mock_teacher_api
    ):
        """Test QA generation with some failures"""
        # Setup mocks
        mock_db.query.return_value.filter.return_value.first.return_value = mock_dataset
        mock_db.query.return_value.filter.return_value.all.return_value = mock_bank_records
        
        # Mock alternating success and failure
        mock_teacher_api.generate_qa_pair.side_effect = [
            ("Q1", "A1"),  # Success
            None,          # Failure
            ("Q2", "A2"),  # Success
            None,          # Failure
            ("Q3", "A3"),  # Success
            ("Q4", "A4"),  # Success
            None,          # Failure
            ("Q5", "A5"),  # Success
            ("Q6", "A6"),  # Success
            ("Q7", "A7"),  # Success
            ("Q8", "A8"),  # Success
            None,          # Failure
        ]
        
        # Mock QA pair count
        mock_db.query.return_value.filter.return_value.count.return_value = 8
        
        # Generate
        results = qa_generator.generate_for_dataset(dataset_id=1)
        
        # Verify results
        assert results["total_attempts"] == 12
        assert results["successful"] == 8
        assert results["failed"] == 4
        assert results["qa_pairs_created"] == 8
        assert len(results["failed_records"]) == 3  # All 3 records had at least one failure
        
        # Verify database operations
        assert mock_db.add.call_count == 8
        mock_db.commit.assert_called_once()
    
    def test_generate_for_dataset_with_custom_question_types(
        self,
        qa_generator,
        mock_db,
        mock_dataset,
        mock_bank_records,
        mock_teacher_api
    ):
        """Test generation with custom question types"""
        # Setup mocks
        mock_db.query.return_value.filter.return_value.first.return_value = mock_dataset
        mock_db.query.return_value.filter.return_value.all.return_value = mock_bank_records
        
        mock_teacher_api.generate_qa_pair.return_value = ("Q", "A")
        mock_db.query.return_value.filter.return_value.count.return_value = 6
        
        # Generate with only 2 question types
        results = qa_generator.generate_for_dataset(
            dataset_id=1,
            question_types=["exact", "fuzzy"]
        )
        
        # Verify
        assert results["question_types"] == ["exact", "fuzzy"]
        assert results["total_attempts"] == 6  # 3 records * 2 types
        assert mock_db.add.call_count == 6
    
    def test_generate_for_dataset_with_progress_callback(
        self,
        qa_generator,
        mock_db,
        mock_dataset,
        mock_bank_records,
        mock_teacher_api
    ):
        """Test generation with progress callback"""
        # Setup mocks
        mock_db.query.return_value.filter.return_value.first.return_value = mock_dataset
        mock_db.query.return_value.filter.return_value.all.return_value = mock_bank_records
        
        mock_teacher_api.generate_qa_pair.return_value = ("Q", "A")
        mock_db.query.return_value.filter.return_value.count.return_value = 12
        
        # Create progress callback
        progress_calls = []
        def progress_callback(current, total, record_id):
            progress_calls.append((current, total, record_id))
        
        # Generate
        qa_generator.generate_for_dataset(
            dataset_id=1,
            progress_callback=progress_callback
        )
        
        # Verify progress callback was called for each record
        assert len(progress_calls) == 3
        assert progress_calls[0] == (1, 3, 1)
        assert progress_calls[1] == (2, 3, 2)
        assert progress_calls[2] == (3, 3, 3)
    
    def test_generate_for_dataset_commit_failure(
        self,
        qa_generator,
        mock_db,
        mock_dataset,
        mock_bank_records,
        mock_teacher_api
    ):
        """Test handling of database commit failure"""
        # Setup mocks
        mock_db.query.return_value.filter.return_value.first.return_value = mock_dataset
        mock_db.query.return_value.filter.return_value.all.return_value = mock_bank_records
        
        mock_teacher_api.generate_qa_pair.return_value = ("Q", "A")
        
        # Mock commit failure
        mock_db.commit.side_effect = Exception("Database error")
        
        # Generate should raise error
        with pytest.raises(QAGenerationError, match="Database commit failed"):
            qa_generator.generate_for_dataset(dataset_id=1)
        
        # Verify rollback was called
        mock_db.rollback.assert_called_once()
    
    def test_split_dataset_invalid_ratios(self, qa_generator):
        """Test dataset split with invalid ratios"""
        with pytest.raises(QAGenerationError, match="Split ratios must sum to 1.0"):
            qa_generator.split_dataset(
                dataset_id=1,
                train_ratio=0.7,
                val_ratio=0.2,
                test_ratio=0.2  # Sum = 1.1
            )
    
    def test_split_dataset_no_qa_pairs(self, qa_generator, mock_db):
        """Test dataset split with no QA pairs"""
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        with pytest.raises(QAGenerationError, match="No QA pairs found"):
            qa_generator.split_dataset(dataset_id=1)
    
    def test_split_dataset_success(self, qa_generator, mock_db):
        """Test successful dataset split"""
        # Create mock QA pairs
        qa_pairs = []
        for i in range(40):  # 10 of each type
            qa = Mock(spec=QAPair)
            qa.id = i + 1
            qa.dataset_id = 1
            qa.question_type = ["exact", "fuzzy", "reverse", "natural"][i % 4]
            qa.split_type = "train"  # Will be updated
            qa_pairs.append(qa)
        
        mock_db.query.return_value.filter.return_value.all.return_value = qa_pairs
        
        # Split dataset
        results = qa_generator.split_dataset(
            dataset_id=1,
            train_ratio=0.8,
            val_ratio=0.1,
            test_ratio=0.1,
            random_seed=42
        )
        
        # Verify results
        assert results["dataset_id"] == 1
        assert results["total_qa_pairs"] == 40
        assert results["train_count"] == 32  # 8 per type * 4 types
        assert results["val_count"] == 4    # 1 per type * 4 types
        assert results["test_count"] == 4   # 1 per type * 4 types
        assert abs(results["train_ratio"] - 0.8) < 0.01
        assert abs(results["val_ratio"] - 0.1) < 0.01
        assert abs(results["test_ratio"] - 0.1) < 0.01
        assert results["random_seed"] == 42
        
        # Verify commit was called
        mock_db.commit.assert_called_once()
    
    def test_split_dataset_even_distribution(self, qa_generator, mock_db):
        """Test that split maintains even distribution across question types"""
        # Create QA pairs with different question types
        qa_pairs = []
        for q_type in ["exact", "fuzzy", "reverse", "natural"]:
            for i in range(10):
                qa = Mock(spec=QAPair)
                qa.question_type = q_type
                qa.split_type = "train"
                qa_pairs.append(qa)
        
        mock_db.query.return_value.filter.return_value.all.return_value = qa_pairs
        
        # Split
        results = qa_generator.split_dataset(dataset_id=1, random_seed=42)
        
        # Count split types per question type
        split_counts = {"exact": {}, "fuzzy": {}, "reverse": {}, "natural": {}}
        for qa in qa_pairs:
            if qa.split_type not in split_counts[qa.question_type]:
                split_counts[qa.question_type][qa.split_type] = 0
            split_counts[qa.question_type][qa.split_type] += 1
        
        # Verify each question type has similar distribution
        for q_type in ["exact", "fuzzy", "reverse", "natural"]:
            assert "train" in split_counts[q_type]
            assert "val" in split_counts[q_type]
            assert "test" in split_counts[q_type]
            # Each type should have 8 train, 1 val, 1 test
            assert split_counts[q_type]["train"] == 8
            assert split_counts[q_type]["val"] == 1
            assert split_counts[q_type]["test"] == 1
    
    def test_split_dataset_reproducibility(self, qa_generator, mock_db):
        """Test that split is reproducible with same random seed"""
        # Create QA pairs
        qa_pairs = []
        for i in range(20):
            qa = Mock(spec=QAPair)
            qa.id = i + 1
            qa.question_type = ["exact", "fuzzy"][i % 2]
            qa.split_type = "train"
            qa_pairs.append(qa)
        
        mock_db.query.return_value.filter.return_value.all.return_value = qa_pairs
        
        # First split
        results1 = qa_generator.split_dataset(dataset_id=1, random_seed=42)
        split_types_1 = [qa.split_type for qa in qa_pairs]
        
        # Reset split types
        for qa in qa_pairs:
            qa.split_type = "train"
        
        # Second split with same seed
        results2 = qa_generator.split_dataset(dataset_id=1, random_seed=42)
        split_types_2 = [qa.split_type for qa in qa_pairs]
        
        # Verify same results
        assert split_types_1 == split_types_2
        assert results1["train_count"] == results2["train_count"]
        assert results1["val_count"] == results2["val_count"]
        assert results1["test_count"] == results2["test_count"]
    
    def test_split_dataset_commit_failure(self, qa_generator, mock_db):
        """Test handling of commit failure during split"""
        # Create QA pairs
        qa_pairs = [Mock(spec=QAPair, question_type="exact", split_type="train") for _ in range(10)]
        mock_db.query.return_value.filter.return_value.all.return_value = qa_pairs
        
        # Mock commit failure
        mock_db.commit.side_effect = Exception("Database error")
        
        # Split should raise error
        with pytest.raises(QAGenerationError, match="Database commit failed"):
            qa_generator.split_dataset(dataset_id=1)
        
        # Verify rollback was called
        mock_db.rollback.assert_called_once()
    
    def test_get_generation_stats_no_qa_pairs(self, qa_generator, mock_db):
        """Test getting stats when no QA pairs exist"""
        mock_db.query.return_value.filter.return_value.count.return_value = 0
        
        stats = qa_generator.get_generation_stats(dataset_id=1)
        
        assert stats["dataset_id"] == 1
        assert stats["total_qa_pairs"] == 0
        assert stats["by_question_type"] == {}
        assert stats["by_split_type"] == {}
    
    def test_get_generation_stats_with_qa_pairs(self, qa_generator, mock_db):
        """Test getting stats with QA pairs"""
        # Mock total count
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        
        # Setup count returns for different queries
        count_values = [
            40,  # Total
            10,  # exact
            10,  # fuzzy
            10,  # reverse
            10,  # natural
            32,  # train
            4,   # val
            4,   # test
        ]
        mock_query.filter.return_value.count.side_effect = count_values
        
        stats = qa_generator.get_generation_stats(dataset_id=1)
        
        assert stats["dataset_id"] == 1
        assert stats["total_qa_pairs"] == 40
        assert stats["by_question_type"]["exact"] == 10
        assert stats["by_question_type"]["fuzzy"] == 10
        assert stats["by_question_type"]["reverse"] == 10
        assert stats["by_question_type"]["natural"] == 10
        assert stats["by_split_type"]["train"] == 32
        assert stats["by_split_type"]["val"] == 4
        assert stats["by_split_type"]["test"] == 4
