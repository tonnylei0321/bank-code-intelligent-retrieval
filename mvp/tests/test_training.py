"""
Unit tests for training functionality
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.models.training_job import TrainingJob
from app.models.dataset import Dataset
from app.models.qa_pair import QAPair
from app.services.model_trainer import ModelTrainer, TrainingError


class TestTrainingJobModel:
    """Test TrainingJob model"""
    
    def test_training_job_creation(self):
        """Test creating a training job"""
        job = TrainingJob(
            dataset_id=1,
            created_by=1,
            status="pending",
            model_name="Qwen/Qwen2.5-0.5B",
            epochs=3,
            batch_size=8,
            learning_rate=2e-4,
            lora_r=16,
            lora_alpha=32,
            lora_dropout=0.05
        )
        
        assert job.dataset_id == 1
        assert job.created_by == 1
        assert job.status == "pending"
        assert job.model_name == "Qwen/Qwen2.5-0.5B"
        assert job.epochs == 3
        assert job.batch_size == 8
        assert job.learning_rate == 2e-4
        assert job.lora_r == 16
        assert job.lora_alpha == 32
        assert job.lora_dropout == 0.05
    
    def test_training_job_to_dict(self):
        """Test converting training job to dictionary"""
        job = TrainingJob(
            id=1,
            dataset_id=1,
            created_by=1,
            status="completed",
            model_name="Qwen/Qwen2.5-0.5B",
            epochs=3,
            batch_size=8,
            learning_rate=2e-4,
            current_epoch=3,
            progress_percentage=100.0,
            train_loss=0.5,
            val_loss=0.6,
            model_path="/path/to/model"
        )
        
        job_dict = job.to_dict()
        
        assert job_dict["id"] == 1
        assert job_dict["dataset_id"] == 1
        assert job_dict["status"] == "completed"
        assert job_dict["current_epoch"] == 3
        assert job_dict["progress_percentage"] == 100.0
        assert job_dict["train_loss"] == 0.5
        assert job_dict["val_loss"] == 0.6
        assert job_dict["model_path"] == "/path/to/model"


class TestModelTrainer:
    """Test ModelTrainer service"""
    
    def test_trainer_initialization(self):
        """Test trainer initialization"""
        mock_db = Mock()
        trainer = ModelTrainer(db=mock_db, models_dir="test_models")
        
        assert trainer.db == mock_db
        assert trainer.device in ["cuda", "cpu"]
    
    def test_prepare_training_data_no_data(self):
        """Test data preparation with no QA pairs"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        trainer = ModelTrainer(db=mock_db)
        mock_tokenizer = Mock()
        
        with pytest.raises(TrainingError, match="No training data found"):
            trainer.prepare_training_data(1, mock_tokenizer)
    
    def test_prepare_training_data_success(self):
        """Test successful data preparation"""
        # Create mock QA pairs
        train_qa = [
            Mock(spec=QAPair, question="Q1?", answer="A1", split_type="train"),
            Mock(spec=QAPair, question="Q2?", answer="A2", split_type="train")
        ]
        val_qa = [
            Mock(spec=QAPair, question="Q3?", answer="A3", split_type="val")
        ]
        
        mock_db = Mock()
        
        # Mock query results
        def mock_filter(*args, **kwargs):
            mock_result = Mock()
            # Check which filter is being applied based on call count
            if not hasattr(mock_filter, 'call_count'):
                mock_filter.call_count = 0
            mock_filter.call_count += 1
            
            if mock_filter.call_count == 1:  # train
                mock_result.all.return_value = train_qa
            elif mock_filter.call_count == 2:  # val
                mock_result.all.return_value = val_qa
            else:  # test
                mock_result.all.return_value = []
            
            return mock_result
        
        mock_db.query.return_value.filter.side_effect = mock_filter
        
        # Mock tokenizer
        mock_tokenizer = Mock()
        mock_tokenizer.return_value = {
            "input_ids": [[1, 2, 3]],
            "attention_mask": [[1, 1, 1]]
        }
        
        trainer = ModelTrainer(db=mock_db)
        
        # Mock HFDataset to avoid actual dataset operations
        with patch('app.services.model_trainer.HFDataset') as mock_dataset:
            mock_train_ds = Mock()
            mock_train_ds.map.return_value = mock_train_ds
            mock_val_ds = Mock()
            mock_val_ds.map.return_value = mock_val_ds
            
            mock_dataset.from_dict.side_effect = [mock_train_ds, mock_val_ds, None]
            
            datasets = trainer.prepare_training_data(1, mock_tokenizer)
            
            assert datasets["train"] is not None
            assert datasets["val"] is not None
    
    def test_stop_training_not_running(self):
        """Test stopping a non-running job"""
        mock_job = Mock(spec=TrainingJob)
        mock_job.id = 1
        mock_job.status = "completed"
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job
        
        trainer = ModelTrainer(db=mock_db)
        
        with pytest.raises(TrainingError, match="is not running"):
            trainer.stop_training(1)
    
    def test_stop_training_success(self):
        """Test successfully stopping a running job"""
        mock_job = Mock(spec=TrainingJob)
        mock_job.id = 1
        mock_job.status = "running"
        mock_job.training_logs = []
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job
        
        trainer = ModelTrainer(db=mock_db)
        result = trainer.stop_training(1)
        
        assert result["job_id"] == 1
        assert result["status"] == "stopped"
        assert mock_job.status == "stopped"
        assert mock_job.completed_at is not None
    
    def test_add_log(self):
        """Test adding log entries"""
        mock_job = Mock(spec=TrainingJob)
        mock_job.id = 1
        mock_job.training_logs = []
        
        mock_db = Mock()
        
        trainer = ModelTrainer(db=mock_db)
        trainer._add_log(mock_job, "info", "Test message")
        
        assert len(mock_job.training_logs) == 1
        assert mock_job.training_logs[0]["level"] == "info"
        assert mock_job.training_logs[0]["message"] == "Test message"
        assert "timestamp" in mock_job.training_logs[0]
