"""
Property-based tests for baseline system and comparison functionality

Feature: bank-code-retrieval
Tests Properties 11, 12, 13 related to baseline comparison and cost calculation
"""
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.core.database import get_db, engine, Base
from app.models.dataset import Dataset
from app.models.bank_code import BankCode
from app.models.qa_pair import QAPair
from app.models.training_job import TrainingJob
from app.models.evaluation import Evaluation
from app.services.model_evaluator import ModelEvaluator


# Test fixtures
@pytest.fixture(scope="function")
def db_session():
    """Create a test database session"""
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def evaluator(db_session):
    """Create ModelEvaluator instance"""
    return ModelEvaluator(db_session)


# Helper strategies
@st.composite
def evaluation_metrics(draw):
    """Generate evaluation metrics"""
    accuracy = draw(st.floats(min_value=0.0, max_value=1.0))
    precision = draw(st.floats(min_value=0.0, max_value=1.0))
    recall = draw(st.floats(min_value=0.0, max_value=1.0))
    
    # Calculate F1 score
    if precision + recall > 0:
        f1_score = 2 * (precision * recall) / (precision + recall)
    else:
        f1_score = 0.0
    
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
        "avg_response_time": draw(st.floats(min_value=10.0, max_value=1000.0)),
        "p95_response_time": draw(st.floats(min_value=50.0, max_value=2000.0)),
        "total": draw(st.integers(min_value=10, max_value=1000))
    }


# Property 11: 对比测试公平性
# For any comparison test, Student_Model and Baseline_System should use exactly the same test set
@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    metrics1=evaluation_metrics(),
    metrics2=evaluation_metrics()
)
def test_property_11_comparison_fairness(db_session, evaluator, metrics1, metrics2):
    """
    Feature: bank-code-retrieval, Property 11: 对比测试公平性
    
    For any comparison test, the model and baseline evaluations should use
    the same training job (and thus the same test set).
    
    Validates: Requirements 5.2
    """
    # Create dataset and training job
    dataset = Dataset(
        filename="test.csv",
        file_path="/tmp/test.csv",
        file_size=1000,
        total_records=100,
        valid_records=100,
        invalid_records=0,
        status="validated",
        uploaded_by=1
    )
    db_session.add(dataset)
    db_session.commit()
    
    # Create training job
    job = TrainingJob(
        dataset_id=dataset.id,
        model_name="qwen3-0.6b",
        epochs=3,
        batch_size=16,
        learning_rate=0.0002,
        lora_r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        status="completed",
        created_by=1,
        started_at=datetime.utcnow() - timedelta(hours=2),
        completed_at=datetime.utcnow(),
        model_path="/tmp/model"
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    
    # Create model evaluation
    model_eval = Evaluation(
        training_job_id=job.id,
        evaluation_type="model",
        metrics=metrics1,
        error_cases=[],
        evaluated_at=datetime.utcnow()
    )
    db_session.add(model_eval)
    
    # Create baseline evaluation
    baseline_eval = Evaluation(
        training_job_id=job.id,  # Same training job!
        evaluation_type="baseline",
        metrics=metrics2,
        error_cases=[],
        evaluated_at=datetime.utcnow()
    )
    db_session.add(baseline_eval)
    db_session.commit()
    db_session.refresh(model_eval)
    db_session.refresh(baseline_eval)
    
    # Verify fairness: both evaluations use the same training job
    assert model_eval.training_job_id == baseline_eval.training_job_id, \
        "Model and baseline evaluations must use the same training job for fair comparison"
    
    # Verify comparison can be performed
    comparison = evaluator.compare_evaluations(model_eval.id, baseline_eval.id)
    
    # Verify comparison includes both evaluation IDs
    assert comparison["model_evaluation_id"] == model_eval.id
    assert comparison["baseline_evaluation_id"] == baseline_eval.id


# Property 12: 对比报告维度
# For any comparison test result, the report should include accuracy, response time, and resource consumption dimensions
@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    model_metrics=evaluation_metrics(),
    baseline_metrics=evaluation_metrics()
)
def test_property_12_comparison_report_dimensions(db_session, evaluator, model_metrics, baseline_metrics):
    """
    Feature: bank-code-retrieval, Property 12: 对比报告维度
    
    For any comparison test result, the report should include three dimensions:
    - Accuracy comparison
    - Response time comparison
    - Resource consumption comparison
    
    Validates: Requirements 5.3, 5.4
    """
    # Create dataset and training job
    dataset = Dataset(
        filename="test.csv",
        file_path="/tmp/test.csv",
        file_size=1000,
        total_records=100,
        valid_records=100,
        invalid_records=0,
        status="validated",
        uploaded_by=1
    )
    db_session.add(dataset)
    db_session.commit()
    
    job = TrainingJob(
        dataset_id=dataset.id,
        model_name="qwen3-0.6b",
        epochs=3,
        batch_size=16,
        learning_rate=0.0002,
        lora_r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        status="completed",
        created_by=1,
        started_at=datetime.utcnow() - timedelta(hours=2),
        completed_at=datetime.utcnow(),
        model_path="/tmp/model"
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    
    # Create evaluations
    model_eval = Evaluation(
        training_job_id=job.id,
        evaluation_type="model",
        metrics=model_metrics,
        error_cases=[],
        evaluated_at=datetime.utcnow()
    )
    db_session.add(model_eval)
    
    baseline_eval = Evaluation(
        training_job_id=job.id,
        evaluation_type="baseline",
        metrics=baseline_metrics,
        error_cases=[],
        evaluated_at=datetime.utcnow()
    )
    db_session.add(baseline_eval)
    db_session.commit()
    db_session.refresh(model_eval)
    db_session.refresh(baseline_eval)
    
    # Generate comparison
    comparison = evaluator.compare_evaluations(model_eval.id, baseline_eval.id)
    
    # Verify all three dimensions are present
    assert "accuracy_comparison" in comparison, \
        "Comparison report must include accuracy comparison"
    assert "response_time_comparison" in comparison, \
        "Comparison report must include response time comparison"
    assert "resource_consumption" in comparison, \
        "Comparison report must include resource consumption comparison"
    
    # Verify accuracy comparison has required fields
    acc_comp = comparison["accuracy_comparison"]
    assert "model" in acc_comp
    assert "baseline" in acc_comp
    assert "difference" in acc_comp
    
    # Verify response time comparison has required fields
    time_comp = comparison["response_time_comparison"]
    assert "model_avg" in time_comp
    assert "baseline_avg" in time_comp
    assert "difference" in time_comp
    
    # Verify resource consumption has both model and baseline info
    resource_comp = comparison["resource_consumption"]
    assert "model" in resource_comp
    assert "baseline" in resource_comp


# Property 13: 成本计算完整性
# For any training and inference process, the system should record API calls, token consumption, and compute time
@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    training_hours=st.floats(min_value=0.1, max_value=10.0),
    num_qa_pairs=st.integers(min_value=10, max_value=1000),
    num_queries=st.integers(min_value=10, max_value=1000),
    avg_response_time=st.floats(min_value=10.0, max_value=1000.0)
)
def test_property_13_cost_calculation_completeness(
    db_session,
    evaluator,
    training_hours,
    num_qa_pairs,
    num_queries,
    avg_response_time
):
    """
    Feature: bank-code-retrieval, Property 13: 成本计算完整性
    
    For any training and inference process, the cost calculation should include:
    - API call costs (token consumption)
    - Training costs (compute time and resources)
    - Inference costs (query processing time)
    
    Validates: Requirements 5.5
    """
    # Create dataset
    dataset = Dataset(
        filename="test.csv",
        file_path="/tmp/test.csv",
        file_size=1000,
        total_records=num_qa_pairs,
        valid_records=num_qa_pairs,
        invalid_records=0,
        status="validated",
        uploaded_by=1
    )
    db_session.add(dataset)
    db_session.commit()
    db_session.refresh(dataset)
    
    # Create QA pairs to simulate API usage
    for i in range(num_qa_pairs):
        qa = QAPair(
            dataset_id=dataset.id,
            source_record_id=1,
            question=f"Question {i}",
            answer=f"Answer {i}",
            question_type="exact",
            split_type="train"
        )
        db_session.add(qa)
    db_session.commit()
    
    # Create training job
    started_at = datetime.utcnow() - timedelta(hours=training_hours)
    completed_at = datetime.utcnow()
    
    job = TrainingJob(
        dataset_id=dataset.id,
        model_name="qwen3-0.6b",
        epochs=3,
        batch_size=16,
        learning_rate=0.0002,
        lora_r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        status="completed",
        created_by=1,
        started_at=started_at,
        completed_at=completed_at,
        model_path="/tmp/model"
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    
    # Calculate training cost
    training_cost = evaluator.calculate_training_cost(job.id)
    
    # Verify all cost components are present
    assert "api_cost" in training_cost, \
        "Training cost must include API cost"
    assert "api_tokens" in training_cost, \
        "Training cost must include token count"
    assert "training_cost" in training_cost, \
        "Training cost must include training compute cost"
    assert "training_hours" in training_cost, \
        "Training cost must include training time"
    assert "total_cost" in training_cost, \
        "Training cost must include total cost"
    
    # Verify API cost is calculated based on QA pairs
    assert training_cost["api_tokens"] > 0, \
        "API token count should be positive when QA pairs exist"
    assert training_cost["api_cost"] >= 0, \
        "API cost should be non-negative"
    
    # Verify training cost is calculated based on time
    assert training_cost["training_hours"] > 0, \
        "Training hours should be positive for completed jobs"
    assert training_cost["training_cost"] >= 0, \
        "Training cost should be non-negative"
    
    # Verify total cost is sum of components
    expected_total = (
        training_cost["api_cost"] +
        training_cost["training_cost"] +
        training_cost["storage_cost"]
    )
    assert abs(training_cost["total_cost"] - expected_total) < 0.01, \
        "Total cost should equal sum of all cost components"
    
    # Calculate inference cost
    inference_cost = evaluator.calculate_inference_cost(
        num_queries,
        avg_response_time
    )
    
    # Verify inference cost components
    assert "num_queries" in inference_cost
    assert "total_time_hours" in inference_cost
    assert "inference_cost" in inference_cost
    assert "cost_per_query" in inference_cost
    
    # Verify inference cost calculations
    assert inference_cost["num_queries"] == num_queries
    assert inference_cost["inference_cost"] >= 0
    assert inference_cost["cost_per_query"] >= 0
    
    # Verify cost per query is correctly calculated
    if num_queries > 0:
        expected_cost_per_query = inference_cost["inference_cost"] / num_queries
        assert abs(inference_cost["cost_per_query"] - expected_cost_per_query) < 0.0001, \
            "Cost per query should equal total cost divided by number of queries"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
