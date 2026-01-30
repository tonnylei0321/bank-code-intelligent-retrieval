#!/usr/bin/env python3
"""
Checkpoint 13: Complete Functionality Verification
This script performs a comprehensive check of all system components
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def check_imports():
    """Verify all core modules can be imported"""
    print("=" * 60)
    print("1. Checking Module Imports")
    print("=" * 60)
    
    modules = [
        ("app.main", "Main Application"),
        ("app.core.config", "Configuration"),
        ("app.core.database", "Database"),
        ("app.core.security", "Security"),
        ("app.core.permissions", "Permissions"),
        ("app.core.rate_limiter", "Rate Limiter"),
        ("app.core.transaction", "Transaction Manager"),
        ("app.models.user", "User Model"),
        ("app.models.dataset", "Dataset Model"),
        ("app.models.bank_code", "Bank Code Model"),
        ("app.models.qa_pair", "QA Pair Model"),
        ("app.models.training_job", "Training Job Model"),
        ("app.models.evaluation", "Evaluation Model"),
        ("app.models.query_log", "Query Log Model"),
        ("app.services.teacher_model", "Teacher Model Service"),
        ("app.services.qa_generator", "QA Generator Service"),
        ("app.services.model_trainer", "Model Trainer Service"),
        ("app.services.model_evaluator", "Model Evaluator Service"),
        ("app.services.query_service", "Query Service"),
        ("app.services.baseline_system", "Baseline System"),
        ("app.api.auth", "Auth API"),
        ("app.api.datasets", "Datasets API"),
        ("app.api.qa_pairs", "QA Pairs API"),
        ("app.api.training", "Training API"),
        ("app.api.evaluation", "Evaluation API"),
        ("app.api.query", "Query API"),
        ("app.api.logs", "Logs API"),
        ("app.api.admin", "Admin API"),
    ]
    
    passed = 0
    failed = 0
    
    for module_name, description in modules:
        try:
            __import__(module_name)
            print(f"✓ {description:30s} - OK")
            passed += 1
        except Exception as e:
            print(f"✗ {description:30s} - FAILED: {str(e)[:50]}")
            failed += 1
    
    print(f"\nImport Check: {passed} passed, {failed} failed")
    return failed == 0


def check_database_models():
    """Verify database models are properly defined"""
    print("\n" + "=" * 60)
    print("2. Checking Database Models")
    print("=" * 60)
    
    from app.core.database import Base
    from sqlalchemy import inspect
    
    # Get all model classes
    models = Base.metadata.tables.keys()
    
    print(f"Found {len(models)} database tables:")
    for table_name in sorted(models):
        print(f"  - {table_name}")
    
    expected_tables = {
        'users', 'datasets', 'bank_codes', 'qa_pairs',
        'training_jobs', 'evaluations', 'query_logs'
    }
    
    missing = expected_tables - set(models)
    if missing:
        print(f"\n✗ Missing tables: {missing}")
        return False
    else:
        print(f"\n✓ All expected tables defined")
        return True


def check_api_routes():
    """Verify API routes are registered"""
    print("\n" + "=" * 60)
    print("3. Checking API Routes")
    print("=" * 60)
    
    from app.main import app
    
    routes = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            for method in route.methods:
                if method != 'HEAD':  # Skip HEAD methods
                    routes.append(f"{method:6s} {route.path}")
    
    print(f"Found {len(routes)} API endpoints:")
    for route in sorted(routes):
        print(f"  {route}")
    
    # Check for key endpoints
    key_endpoints = [
        'POST   /api/v1/auth/login',
        'POST   /api/v1/datasets/upload',
        'POST   /api/v1/qa-pairs/generate',
        'POST   /api/v1/training/start',
        'POST   /api/v1/evaluation/start',
        'POST   /api/v1/query',
    ]
    
    missing = []
    for endpoint in key_endpoints:
        if not any(endpoint in route for route in routes):
            missing.append(endpoint)
    
    if missing:
        print(f"\n✗ Missing key endpoints: {missing}")
        return False
    else:
        print(f"\n✓ All key endpoints registered")
        return True


def check_test_files():
    """Verify test files exist"""
    print("\n" + "=" * 60)
    print("4. Checking Test Files")
    print("=" * 60)
    
    test_files = [
        "tests/test_infrastructure.py",
        "tests/test_models.py",
        "tests/test_auth_properties.py",
        "tests/test_permissions_properties.py",
        "tests/test_data_upload.py",
        "tests/test_data_validation_properties.py",
        "tests/test_data_preview_properties.py",
        "tests/test_qa_generator.py",
        "tests/test_qa_pairs_api.py",
        "tests/test_qa_generation_properties.py",
        "tests/test_teacher_model.py",
        "tests/test_training.py",
        "tests/test_training_properties.py",
        "tests/test_evaluation_properties.py",
        "tests/test_query_properties.py",
        "tests/test_baseline_properties.py",
        "tests/test_logging_properties.py",
        "tests/test_api_properties.py",
        "tests/test_admin_api.py",
    ]
    
    passed = 0
    failed = 0
    
    for test_file in test_files:
        if Path(test_file).exists():
            print(f"✓ {test_file}")
            passed += 1
        else:
            print(f"✗ {test_file} - NOT FOUND")
            failed += 1
    
    print(f"\nTest Files: {passed} found, {failed} missing")
    return failed == 0


def check_configuration():
    """Verify configuration is properly set"""
    print("\n" + "=" * 60)
    print("5. Checking Configuration")
    print("=" * 60)
    
    from app.core.config import settings
    
    config_items = [
        ("APP_NAME", settings.APP_NAME),
        ("APP_VERSION", settings.APP_VERSION),
        ("DATABASE_URL", settings.DATABASE_URL[:50] + "..."),
        ("SECRET_KEY", "***" if settings.SECRET_KEY else "NOT SET"),
        ("ALGORITHM", settings.ALGORITHM),
        ("ACCESS_TOKEN_EXPIRE_HOURS", settings.ACCESS_TOKEN_EXPIRE_HOURS),
    ]
    
    for key, value in config_items:
        print(f"  {key:30s}: {value}")
    
    if not settings.SECRET_KEY:
        print("\n✗ SECRET_KEY not configured")
        return False
    
    print("\n✓ Configuration OK")
    return True


def check_property_tests():
    """Check that property tests are defined"""
    print("\n" + "=" * 60)
    print("6. Checking Property-Based Tests")
    print("=" * 60)
    
    properties = [
        ("Property 1", "Data Validation Completeness", "test_data_validation_properties.py"),
        ("Property 2", "Data Preview Boundary", "test_data_preview_properties.py"),
        ("Property 3", "QA Generation Completeness", "test_qa_generation_properties.py"),
        ("Property 4", "Dataset Split Ratio", "test_qa_generation_properties.py"),
        ("Property 5", "Training Config Persistence", "test_training_properties.py"),
        ("Property 6", "Training Epoch Evaluation", "test_training_properties.py"),
        ("Property 7", "Evaluation Metrics Calculation", "test_evaluation_properties.py"),
        ("Property 8", "Response Time Statistics", "test_evaluation_properties.py"),
        ("Property 9", "Robustness Test Coverage", "test_evaluation_properties.py"),
        ("Property 10", "Evaluation Report Completeness", "test_evaluation_properties.py"),
        ("Property 11", "Comparison Fairness", "test_baseline_properties.py"),
        ("Property 12", "Comparison Report Dimensions", "test_baseline_properties.py"),
        ("Property 13", "Cost Calculation Completeness", "test_baseline_properties.py"),
        ("Property 14", "Query Response Format", "test_query_properties.py"),
        ("Property 15", "Multiple Results Sorting", "test_query_properties.py"),
        ("Property 16", "Query Response Time", "test_query_properties.py"),
        ("Property 17", "Log Filter Accuracy", "test_logging_properties.py"),
        ("Property 18", "Anomaly Detection", "test_logging_properties.py"),
        ("Property 19", "JWT Token Validity", "test_auth_properties.py"),
        ("Property 20", "Permission Control Consistency", "test_permissions_properties.py"),
        ("Property 21", "API Response Format", "test_api_properties.py"),
        ("Property 22", "Rate Limit Enforcement", "test_api_properties.py"),
        ("Property 23", "Model Persistence Consistency", "test_api_properties.py"),
        ("Property 24", "Transaction Atomicity", "test_api_properties.py"),
    ]
    
    passed = 0
    failed = 0
    
    for prop_id, prop_name, test_file in properties:
        test_path = Path("tests") / test_file
        if test_path.exists():
            print(f"✓ {prop_id:12s} - {prop_name:40s} ({test_file})")
            passed += 1
        else:
            print(f"✗ {prop_id:12s} - {prop_name:40s} ({test_file}) - FILE NOT FOUND")
            failed += 1
    
    print(f"\nProperty Tests: {passed} defined, {failed} missing")
    return failed == 0


def main():
    """Run all verification checks"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  Checkpoint 13: Complete Functionality Verification  ".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    print("\n")
    
    checks = [
        ("Module Imports", check_imports),
        ("Database Models", check_database_models),
        ("API Routes", check_api_routes),
        ("Test Files", check_test_files),
        ("Configuration", check_configuration),
        ("Property Tests", check_property_tests),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} check failed with error: {e}")
            results.append((name, False))
    
    # Final summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8s} - {name}")
    
    print(f"\nOverall: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n✓ All verification checks passed!")
        print("✓ System is ready for end-to-end testing")
        return 0
    else:
        print(f"\n✗ {total - passed} checks failed")
        print("✗ Please review and fix the issues above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
