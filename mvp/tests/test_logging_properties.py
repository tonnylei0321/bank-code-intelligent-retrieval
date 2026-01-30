"""
Property-based tests for logging functionality
日志功能的属性测试

Tests correctness properties for log filtering and anomaly detection.
"""
import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, timedelta
from typing import List

from app.api.logs import LogEntry, filter_logs


# Strategies for generating test data
@st.composite
def log_entry_strategy(draw):
    """Generate a random log entry"""
    # Generate timestamp
    base_time = datetime(2026, 1, 1, 0, 0, 0)
    hours_offset = draw(st.integers(min_value=0, max_value=720))  # 30 days
    timestamp = base_time + timedelta(hours=hours_offset)
    
    # Generate level
    level = draw(st.sampled_from(["INFO", "WARNING", "ERROR", "DEBUG"]))
    
    # Generate module, function, line
    module = draw(st.sampled_from(["app.api.training", "app.services.model_trainer", "app.core.database"]))
    function = draw(st.sampled_from(["train_model", "evaluate", "query", "upload_data"]))
    line = draw(st.integers(min_value=1, max_value=1000))
    
    # Generate message with optional task ID
    task_id = draw(st.integers(min_value=1, max_value=100))
    message_templates = [
        f"Training started for job {task_id}",
        f"Job {task_id} completed successfully",
        f"Processing dataset {task_id}",
        "Database connection established",
        "User authentication successful",
        f"Error in training job {task_id}",
    ]
    message = draw(st.sampled_from(message_templates))
    
    return LogEntry(
        timestamp=timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        level=level,
        module=module,
        function=function,
        line=line,
        message=message
    )


# Property 17: Log filtering accuracy
# Feature: bank-code-retrieval, Property 17: 日志筛选准确性

@given(
    logs=st.lists(log_entry_strategy(), min_size=10, max_size=100),
    level_filter=st.sampled_from([None, "INFO", "WARNING", "ERROR"])
)
@settings(max_examples=100, deadline=None)
def test_log_filter_by_level_accuracy(logs: List[LogEntry], level_filter: str):
    """
    Property 17: Log filtering accuracy - Level filter
    
    For any list of log entries and level filter,
    all returned logs should match the specified level.
    
    Validates: Requirements 7.3
    """
    # Filter logs
    filtered = filter_logs(logs, level=level_filter)
    
    # Verify all filtered logs match the level
    if level_filter:
        for log in filtered:
            assert log.level == level_filter, (
                f"Filtered log has level {log.level}, expected {level_filter}"
            )
    else:
        # No filter means all logs should be returned
        assert len(filtered) == len(logs)


@given(
    logs=st.lists(log_entry_strategy(), min_size=10, max_size=100),
    task_id=st.integers(min_value=1, max_value=100)
)
@settings(max_examples=100, deadline=None)
def test_log_filter_by_task_id_accuracy(logs: List[LogEntry], task_id: int):
    """
    Property 17: Log filtering accuracy - Task ID filter
    
    For any list of log entries and task ID filter,
    all returned logs should contain the task ID in their message.
    
    Validates: Requirements 7.3
    """
    # Filter logs
    filtered = filter_logs(logs, task_id=task_id)
    
    # Verify all filtered logs contain the task ID
    task_str = f"job {task_id}"
    for log in filtered:
        assert task_str.lower() in log.message.lower() or str(task_id) in log.message, (
            f"Filtered log message '{log.message}' does not contain task ID {task_id}"
        )


@given(
    logs=st.lists(log_entry_strategy(), min_size=10, max_size=100),
    search_text=st.sampled_from(["training", "error", "completed", "job", "dataset"])
)
@settings(max_examples=100, deadline=None)
def test_log_filter_by_search_accuracy(logs: List[LogEntry], search_text: str):
    """
    Property 17: Log filtering accuracy - Search text filter
    
    For any list of log entries and search text,
    all returned logs should contain the search text in their message.
    
    Validates: Requirements 7.3
    """
    # Filter logs
    filtered = filter_logs(logs, search=search_text)
    
    # Verify all filtered logs contain the search text
    search_lower = search_text.lower()
    for log in filtered:
        assert search_lower in log.message.lower(), (
            f"Filtered log message '{log.message}' does not contain search text '{search_text}'"
        )


@given(
    logs=st.lists(log_entry_strategy(), min_size=10, max_size=100)
)
@settings(max_examples=100, deadline=None)
def test_log_filter_by_time_range_accuracy(logs: List[LogEntry]):
    """
    Property 17: Log filtering accuracy - Time range filter
    
    For any list of log entries and time range,
    all returned logs should fall within the specified time range.
    
    Validates: Requirements 7.3
    """
    if not logs:
        return
    
    # Sort logs by timestamp
    sorted_logs = sorted(logs, key=lambda x: x.timestamp)
    
    # Use middle timestamps as filter range
    if len(sorted_logs) >= 3:
        start_time = sorted_logs[len(sorted_logs) // 3].timestamp
        end_time = sorted_logs[2 * len(sorted_logs) // 3].timestamp
        
        # Filter logs
        filtered = filter_logs(logs, start_time=start_time, end_time=end_time)
        
        # Verify all filtered logs are within time range
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
        
        for log in filtered:
            log_dt = datetime.fromisoformat(log.timestamp)
            assert start_dt <= log_dt <= end_dt, (
                f"Filtered log timestamp {log.timestamp} is outside range "
                f"[{start_time}, {end_time}]"
            )


@given(
    logs=st.lists(log_entry_strategy(), min_size=10, max_size=100),
    level_filter=st.sampled_from([None, "INFO", "WARNING", "ERROR"]),
    task_id=st.integers(min_value=1, max_value=100)
)
@settings(max_examples=100, deadline=None)
def test_log_filter_multiple_criteria_accuracy(
    logs: List[LogEntry],
    level_filter: str,
    task_id: int
):
    """
    Property 17: Log filtering accuracy - Multiple criteria
    
    For any list of log entries and multiple filter criteria,
    all returned logs should satisfy ALL specified criteria.
    
    Validates: Requirements 7.3
    """
    # Filter logs with multiple criteria
    filtered = filter_logs(logs, level=level_filter, task_id=task_id)
    
    # Verify all filtered logs match all criteria
    task_str = f"job {task_id}"
    for log in filtered:
        # Check level
        if level_filter:
            assert log.level == level_filter, (
                f"Filtered log has level {log.level}, expected {level_filter}"
            )
        
        # Check task ID
        assert task_str.lower() in log.message.lower() or str(task_id) in log.message, (
            f"Filtered log message '{log.message}' does not contain task ID {task_id}"
        )


# Unit tests for edge cases
def test_log_filter_empty_list():
    """Test filtering empty log list"""
    filtered = filter_logs([], level="INFO")
    assert filtered == []


def test_log_filter_no_matches():
    """Test filtering with no matches"""
    logs = [
        LogEntry(
            timestamp="2026-01-10 12:00:00",
            level="INFO",
            module="test",
            function="test",
            line=1,
            message="Test message"
        )
    ]
    
    filtered = filter_logs(logs, level="ERROR")
    assert filtered == []


def test_log_filter_invalid_time_format():
    """Test filtering with invalid time format"""
    logs = [
        LogEntry(
            timestamp="2026-01-10 12:00:00",
            level="INFO",
            module="test",
            function="test",
            line=1,
            message="Test message"
        )
    ]
    
    # Invalid time format should be ignored
    filtered = filter_logs(logs, start_time="invalid-time")
    assert len(filtered) == 1  # Should return all logs


def test_log_filter_case_insensitive_search():
    """Test that search is case-insensitive"""
    logs = [
        LogEntry(
            timestamp="2026-01-10 12:00:00",
            level="INFO",
            module="test",
            function="test",
            line=1,
            message="Training Started"
        )
    ]
    
    # Search with lowercase should match uppercase
    filtered = filter_logs(logs, search="training")
    assert len(filtered) == 1
    
    # Search with uppercase should match lowercase
    filtered = filter_logs(logs, search="TRAINING")
    assert len(filtered) == 1


# Property 18: Anomaly detection marking
# Feature: bank-code-retrieval, Property 18: 异常检测标记

@given(
    loss_values=st.lists(
        st.floats(min_value=0.01, max_value=10.0, allow_nan=False, allow_infinity=False),
        min_size=3,
        max_size=10
    )
)
@settings(max_examples=100, deadline=None)
def test_anomaly_detection_fluctuation_threshold(loss_values: List[float]):
    """
    Property 18: Anomaly detection marking - Fluctuation threshold
    
    For any sequence of loss values, if the MOST RECENT 3 consecutive values
    have changes that both exceed 50%, an anomaly should be detected.
    
    Note: The implementation only checks the most recent 3 epochs, not all
    possible 3-consecutive windows in the training history.
    
    Validates: Requirements 7.4
    """
    from app.models.training_job import TrainingJob
    from app.services.model_trainer import ModelTrainer
    from sqlalchemy.orm import Session
    from unittest.mock import Mock
    
    # Create mock database session
    mock_db = Mock(spec=Session)
    mock_db.commit = Mock()
    
    # Create trainer
    trainer = ModelTrainer(db=mock_db)
    
    # Create mock training job with logs
    job = Mock(spec=TrainingJob)
    job.id = 1
    job.training_logs = []
    
    # Add loss values as log entries
    for i, loss in enumerate(loss_values):
        log_entry = {
            "timestamp": f"2026-01-10 12:{i:02d}:00",
            "level": "info",
            "message": f"Epoch {i+1}/{len(loss_values)} completed - Loss: {loss:.4f}"
        }
        job.training_logs.append(log_entry)
    
    # Check for anomaly
    has_anomaly = trainer._detect_anomaly(job)
    
    # Verify anomaly detection logic
    # The detector reads logs in reverse order and stops after finding 3 loss values
    # So we only check the MOST RECENT 3 epochs
    reversed_losses = list(reversed(loss_values))
    
    # Only check the first 3 values (most recent 3 epochs)
    expected_anomaly = False
    if len(reversed_losses) >= 3:
        loss1, loss2, loss3 = reversed_losses[0], reversed_losses[1], reversed_losses[2]
        
        if loss1 > 0 and loss2 > 0:
            change1 = abs(loss2 - loss1) / loss1
            change2 = abs(loss3 - loss2) / loss2
            
            # Both changes must exceed 50%
            if change1 > 0.5 and change2 > 0.5:
                expected_anomaly = True
    
    assert has_anomaly == expected_anomaly, (
        f"Anomaly detection mismatch: detected={has_anomaly}, expected={expected_anomaly} "
        f"for loss values {loss_values} (most recent 3: {reversed_losses[:3]})"
    )


def test_anomaly_detection_no_anomaly_stable_loss():
    """Test that stable loss does not trigger anomaly"""
    from app.models.training_job import TrainingJob
    from app.services.model_trainer import ModelTrainer
    from sqlalchemy.orm import Session
    from unittest.mock import Mock
    
    # Create mock database session
    mock_db = Mock(spec=Session)
    mock_db.commit = Mock()
    
    # Create trainer
    trainer = ModelTrainer(db=mock_db)
    
    # Create mock training job with stable loss
    job = Mock(spec=TrainingJob)
    job.id = 1
    job.training_logs = [
        {"timestamp": "2026-01-10 12:00:00", "level": "info", "message": "Epoch 1/5 completed - Loss: 1.0000"},
        {"timestamp": "2026-01-10 12:01:00", "level": "info", "message": "Epoch 2/5 completed - Loss: 0.9500"},
        {"timestamp": "2026-01-10 12:02:00", "level": "info", "message": "Epoch 3/5 completed - Loss: 0.9000"},
        {"timestamp": "2026-01-10 12:03:00", "level": "info", "message": "Epoch 4/5 completed - Loss: 0.8500"},
        {"timestamp": "2026-01-10 12:04:00", "level": "info", "message": "Epoch 5/5 completed - Loss: 0.8000"},
    ]
    
    # Check for anomaly
    has_anomaly = trainer._detect_anomaly(job)
    
    # Should not detect anomaly for stable decreasing loss
    assert not has_anomaly, "Stable loss should not trigger anomaly detection"


def test_anomaly_detection_with_large_fluctuation():
    """Test that large fluctuation triggers anomaly"""
    from app.models.training_job import TrainingJob
    from app.services.model_trainer import ModelTrainer
    from sqlalchemy.orm import Session
    from unittest.mock import Mock
    
    # Create mock database session
    mock_db = Mock(spec=Session)
    mock_db.commit = Mock()
    
    # Create trainer
    trainer = ModelTrainer(db=mock_db)
    
    # Create mock training job with large fluctuation in MOST RECENT 3 epochs
    # Most recent 3 (reversed): [1.0, 0.25, 1.0]
    # Change 1: |0.25 - 1.0| / 1.0 = 75% (> 50%)
    # Change 2: |1.0 - 0.25| / 0.25 = 300% (> 50%)
    # Both changes exceed 50%, so anomaly should be detected
    job = Mock(spec=TrainingJob)
    job.id = 1
    job.training_logs = [
        {"timestamp": "2026-01-10 12:00:00", "level": "info", "message": "Epoch 1/5 completed - Loss: 0.5000"},
        {"timestamp": "2026-01-10 12:01:00", "level": "info", "message": "Epoch 2/5 completed - Loss: 1.0000"},
        {"timestamp": "2026-01-10 12:02:00", "level": "info", "message": "Epoch 3/5 completed - Loss: 0.2500"},  # 75% decrease
        {"timestamp": "2026-01-10 12:03:00", "level": "info", "message": "Epoch 4/5 completed - Loss: 1.0000"},  # 300% increase
    ]
    
    # Check for anomaly
    has_anomaly = trainer._detect_anomaly(job)
    
    # Should detect anomaly for large fluctuation in most recent 3 epochs
    assert has_anomaly, "Large fluctuation (>50% in most recent 3 epochs) should trigger anomaly detection"


def test_anomaly_detection_insufficient_data():
    """Test that insufficient data does not trigger anomaly"""
    from app.models.training_job import TrainingJob
    from app.services.model_trainer import ModelTrainer
    from sqlalchemy.orm import Session
    from unittest.mock import Mock
    
    # Create mock database session
    mock_db = Mock(spec=Session)
    mock_db.commit = Mock()
    
    # Create trainer
    trainer = ModelTrainer(db=mock_db)
    
    # Create mock training job with only 2 epochs
    job = Mock(spec=TrainingJob)
    job.id = 1
    job.training_logs = [
        {"timestamp": "2026-01-10 12:00:00", "level": "info", "message": "Epoch 1/2 completed - Loss: 1.0000"},
        {"timestamp": "2026-01-10 12:01:00", "level": "info", "message": "Epoch 2/2 completed - Loss: 2.0000"},
    ]
    
    # Check for anomaly
    has_anomaly = trainer._detect_anomaly(job)
    
    # Should not detect anomaly with insufficient data
    assert not has_anomaly, "Insufficient data (<3 epochs) should not trigger anomaly detection"


def test_anomaly_detection_empty_logs():
    """Test that empty logs do not trigger anomaly"""
    from app.models.training_job import TrainingJob
    from app.services.model_trainer import ModelTrainer
    from sqlalchemy.orm import Session
    from unittest.mock import Mock
    
    # Create mock database session
    mock_db = Mock(spec=Session)
    mock_db.commit = Mock()
    
    # Create trainer
    trainer = ModelTrainer(db=mock_db)
    
    # Create mock training job with no logs
    job = Mock(spec=TrainingJob)
    job.id = 1
    job.training_logs = []
    
    # Check for anomaly
    has_anomaly = trainer._detect_anomaly(job)
    
    # Should not detect anomaly with no logs
    assert not has_anomaly, "Empty logs should not trigger anomaly detection"
