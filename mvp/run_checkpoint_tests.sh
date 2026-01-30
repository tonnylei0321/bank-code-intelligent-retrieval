#!/bin/bash
# Checkpoint 13: Comprehensive Test Suite
# This script runs all tests in groups to verify system functionality

echo "========================================="
echo "Checkpoint 13: Complete Functionality Verification"
echo "========================================="
echo ""

# Track results
TOTAL_PASSED=0
TOTAL_FAILED=0
FAILED_TESTS=""

# Function to run test group
run_test_group() {
    local name=$1
    local path=$2
    echo "Running: $name"
    echo "-----------------------------------"
    
    if python3 -m pytest "$path" -v --tb=line -x 2>&1 | tee /tmp/test_output.txt; then
        passed=$(grep -c "PASSED" /tmp/test_output.txt || echo "0")
        echo "✓ $name: $passed tests passed"
        TOTAL_PASSED=$((TOTAL_PASSED + passed))
    else
        failed=$(grep -c "FAILED\|ERROR" /tmp/test_output.txt || echo "0")
        echo "✗ $name: $failed tests failed"
        TOTAL_FAILED=$((TOTAL_FAILED + failed))
        FAILED_TESTS="$FAILED_TESTS\n  - $name"
    fi
    echo ""
}

# Run test groups
run_test_group "Infrastructure Tests" "tests/test_infrastructure.py"
run_test_group "Model Tests" "tests/test_models.py"
run_test_group "Data Upload Tests" "tests/test_data_upload.py"
run_test_group "Data Validation Properties" "tests/test_data_validation_properties.py"
run_test_group "Data Preview Properties" "tests/test_data_preview_properties.py"
run_test_group "QA Generator Tests" "tests/test_qa_generator.py"
run_test_group "Teacher Model Tests" "tests/test_teacher_model.py"
run_test_group "Training Tests" "tests/test_training.py"

echo "========================================="
echo "Test Summary"
echo "========================================="
echo "Total Passed: $TOTAL_PASSED"
echo "Total Failed: $TOTAL_FAILED"

if [ $TOTAL_FAILED -gt 0 ]; then
    echo ""
    echo "Failed Test Groups:"
    echo -e "$FAILED_TESTS"
    exit 1
else
    echo ""
    echo "✓ All tests passed!"
    exit 0
fi
