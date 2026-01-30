# User Acceptance Test Guide - Task 15
# 联行号检索模型训练验证系统 - 用户验收测试指南

**Version**: 1.0  
**Date**: 2026-01-11  
**Purpose**: Guide for conducting user acceptance testing of the Bank Code Retrieval System

---

## Overview

This guide provides step-by-step instructions for conducting user acceptance testing (UAT) of the Bank Code Retrieval System MVP. The tests verify that the system meets all functional requirements and is ready for production use.

## Prerequisites

Before starting UAT, ensure:

1. ✅ System is installed and running
2. ✅ Database is initialized
3. ✅ Test data is available
4. ✅ Admin and user accounts are created
5. ✅ All environment variables are configured

## Test Environment Setup

### 1. Start the System

```bash
cd mvp
./scripts/start.sh
```

Verify the system is running:
- API should be accessible at `http://localhost:8000`
- Health check: `http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`

### 2. Create Test Accounts

```bash
# Create admin account
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_admin",
    "email": "admin@test.com",
    "password": "Admin123!",
    "role": "admin"
  }'

# Create regular user account
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_user",
    "email": "user@test.com",
    "password": "User123!",
    "role": "user"
  }'
```

---

## Test Scenarios

### Scenario 1: User Authentication (Requirements 8.1-8.5)

**Objective**: Verify user authentication and authorization

#### Test 1.1: User Login
**Steps**:
1. Navigate to login endpoint
2. Enter valid credentials
3. Submit login form

**Expected Result**:
- ✅ Receive JWT token
- ✅ Token is valid for 24 hours
- ✅ Token contains user ID and role

**Test Command**:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test_admin&password=Admin123!"
```

**Pass Criteria**: Response contains `access_token` field

#### Test 1.2: Invalid Credentials
**Steps**:
1. Attempt login with wrong password
2. Verify error response

**Expected Result**:
- ✅ Returns 401 Unauthorized
- ✅ Error message is clear

**Pass Criteria**: Receives 401 status code

#### Test 1.3: Permission Control
**Steps**:
1. Login as regular user
2. Attempt to access admin-only endpoint
3. Verify access denied

**Expected Result**:
- ✅ Returns 403 Forbidden
- ✅ Regular user cannot access admin functions

**Test Command**:
```bash
# Get user token
USER_TOKEN=$(curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test_user&password=User123!" | jq -r '.access_token')

# Try to access admin endpoint
curl -X GET "http://localhost:8000/api/v1/admin/users" \
  -H "Authorization: Bearer $USER_TOKEN"
```

**Pass Criteria**: Receives 403 status code

---

### Scenario 2: Data Management (Requirements 1.1-1.5)

**Objective**: Verify data upload, validation, and preview functionality

#### Test 2.1: Upload Valid Data
**Steps**:
1. Login as admin
2. Upload CSV file with valid bank code data
3. Verify upload success

**Expected Result**:
- ✅ File is uploaded successfully
- ✅ Data is validated
- ✅ Statistics are displayed (total, valid, invalid records)

**Test Command**:
```bash
# Get admin token
ADMIN_TOKEN=$(curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test_admin&password=Admin123!" | jq -r '.access_token')

# Upload test data
curl -X POST "http://localhost:8000/api/v1/datasets/upload" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F "file=@test_data.csv"
```

**Pass Criteria**: Response shows `valid_records > 0`

#### Test 2.2: Data Validation
**Steps**:
1. Upload file with some invalid records
2. Verify system handles errors gracefully
3. Check error records are logged

**Expected Result**:
- ✅ Valid records are processed
- ✅ Invalid records are logged with line numbers
- ✅ System continues processing

**Pass Criteria**: Response shows both `valid_records` and `invalid_records`

#### Test 2.3: Data Preview
**Steps**:
1. Request data preview for uploaded dataset
2. Verify preview shows first 100 records

**Expected Result**:
- ✅ Returns up to 100 records
- ✅ Records contain bank_name, bank_code, clearing_code
- ✅ Data is properly formatted

**Test Command**:
```bash
# Get dataset ID from upload response
DATASET_ID=1

# Preview data
curl -X GET "http://localhost:8000/api/v1/datasets/$DATASET_ID/preview" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Pass Criteria**: Response contains array of records, max 100 items

---

### Scenario 3: Training Data Generation (Requirements 2.1-2.5)

**Objective**: Verify QA pair generation and dataset splitting

#### Test 3.1: Generate QA Pairs
**Steps**:
1. Select uploaded dataset
2. Start QA pair generation
3. Monitor generation progress

**Expected Result**:
- ✅ QA pairs are generated for each record
- ✅ Multiple question types are created (exact, fuzzy, reverse, natural)
- ✅ Generation failures are logged

**Test Command**:
```bash
curl -X POST "http://localhost:8000/api/v1/qa-pairs/generate" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": 1,
    "question_types": ["exact", "fuzzy", "reverse", "natural"]
  }'
```

**Pass Criteria**: Response shows generation started successfully

#### Test 3.2: Dataset Split
**Steps**:
1. Verify generated QA pairs are split into train/val/test
2. Check split ratios are approximately 8:1:1

**Expected Result**:
- ✅ Training set contains ~80% of data
- ✅ Validation set contains ~10% of data
- ✅ Test set contains ~10% of data

**Test Command**:
```bash
curl -X GET "http://localhost:8000/api/v1/qa-pairs/$DATASET_ID/stats" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Pass Criteria**: Split ratios are within ±2% of target

---

### Scenario 4: Model Training (Requirements 3.1-3.5)

**Objective**: Verify model training functionality

#### Test 4.1: Start Training
**Steps**:
1. Configure training parameters
2. Start training job
3. Verify job is created

**Expected Result**:
- ✅ Training job is created
- ✅ Status is "running"
- ✅ Progress is tracked

**Test Command**:
```bash
curl -X POST "http://localhost:8000/api/v1/training/start" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": 1,
    "config": {
      "learning_rate": 0.0002,
      "batch_size": 16,
      "num_epochs": 3,
      "lora_r": 16,
      "lora_alpha": 32
    }
  }'
```

**Pass Criteria**: Response contains `job_id` and status is "running"

#### Test 4.2: Monitor Training Progress
**Steps**:
1. Query training job status
2. Verify progress updates
3. Check training metrics

**Expected Result**:
- ✅ Progress percentage increases
- ✅ Loss values are recorded
- ✅ Validation accuracy is calculated

**Test Command**:
```bash
JOB_ID=1
curl -X GET "http://localhost:8000/api/v1/training/$JOB_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Pass Criteria**: Response shows current progress and metrics

---

### Scenario 5: Model Evaluation (Requirements 4.1-4.5)

**Objective**: Verify model evaluation and reporting

#### Test 5.1: Start Evaluation
**Steps**:
1. Select completed training job
2. Start evaluation
3. Wait for completion

**Expected Result**:
- ✅ Evaluation runs on test set
- ✅ Metrics are calculated (accuracy, precision, recall, F1)
- ✅ Response times are measured

**Test Command**:
```bash
curl -X POST "http://localhost:8000/api/v1/evaluation/start" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "training_job_id": 1,
    "evaluation_type": "model"
  }'
```

**Pass Criteria**: Evaluation completes successfully

#### Test 5.2: View Evaluation Report
**Steps**:
1. Request evaluation report
2. Verify all metrics are present
3. Check error cases are analyzed

**Expected Result**:
- ✅ Report contains accuracy metrics
- ✅ Performance metrics are included
- ✅ Error cases are listed
- ✅ Comparison with baseline is shown

**Test Command**:
```bash
EVAL_ID=1
curl -X GET "http://localhost:8000/api/v1/evaluation/$EVAL_ID/report" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Pass Criteria**: Report contains all required sections

---

### Scenario 6: Query Service (Requirements 6.1-6.5)

**Objective**: Verify query functionality and response quality

#### Test 6.1: Single Query
**Steps**:
1. Submit query for bank code
2. Verify response format
3. Check response time

**Expected Result**:
- ✅ Query returns result within 1 second
- ✅ Response contains bank code information
- ✅ Confidence score is provided

**Test Command**:
```bash
curl -X POST "http://localhost:8000/api/v1/query/" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "中国工商银行北京分行的联行号是什么？"
  }'
```

**Pass Criteria**: Response time < 1000ms, contains bank code

#### Test 6.2: Fuzzy Query
**Steps**:
1. Submit query with abbreviation or typo
2. Verify system handles fuzzy matching
3. Check results are relevant

**Expected Result**:
- ✅ System finds relevant results
- ✅ Multiple matches are ranked by relevance
- ✅ Top 3 results are returned

**Test Command**:
```bash
curl -X POST "http://localhost:8000/api/v1/query/" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "工行北京的联行号"
  }'
```

**Pass Criteria**: Returns relevant results despite abbreviation

#### Test 6.3: No Match Query
**Steps**:
1. Submit query for non-existent bank
2. Verify graceful handling

**Expected Result**:
- ✅ Returns "未找到" message
- ✅ No error is thrown
- ✅ Response is user-friendly

**Test Command**:
```bash
curl -X POST "http://localhost:8000/api/v1/query/" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "不存在的银行联行号"
  }'
```

**Pass Criteria**: Response indicates no results found

---

### Scenario 7: API Rate Limiting (Requirements 9.4-9.5)

**Objective**: Verify rate limiting functionality

#### Test 7.1: Rate Limit Enforcement
**Steps**:
1. Send 101 requests within 1 minute
2. Verify 101st request is rejected
3. Check retry-after header

**Expected Result**:
- ✅ First 100 requests succeed
- ✅ 101st request returns 429
- ✅ Retry-after time is provided

**Test Script**:
```bash
# Send 101 requests
for i in {1..101}; do
  curl -X GET "http://localhost:8000/health" \
    -H "Authorization: Bearer $USER_TOKEN" \
    -w "\n%{http_code}\n"
  sleep 0.5
done
```

**Pass Criteria**: Request 101 returns 429 status code

---

## Performance Acceptance Criteria

### Response Time Requirements

| Operation | Target | Acceptable |
|-----------|--------|------------|
| Simple Query | < 500ms | < 1000ms |
| Complex Query | < 1000ms | < 2000ms |
| Data Upload (1000 records) | < 5s | < 10s |
| QA Generation (100 records) | < 30s | < 60s |
| Model Training (small dataset) | < 5min | < 10min |

### Accuracy Requirements

| Metric | Target | Minimum |
|--------|--------|---------|
| Overall Accuracy | ≥ 95% | ≥ 90% |
| Exact Match Accuracy | ≥ 99% | ≥ 95% |
| Fuzzy Match Accuracy | ≥ 90% | ≥ 85% |

---

## Test Results Template

### Test Execution Summary

**Tester**: _______________  
**Date**: _______________  
**Environment**: _______________

| Scenario | Test | Status | Notes |
|----------|------|--------|-------|
| 1. Authentication | 1.1 User Login | ☐ Pass ☐ Fail | |
| 1. Authentication | 1.2 Invalid Credentials | ☐ Pass ☐ Fail | |
| 1. Authentication | 1.3 Permission Control | ☐ Pass ☐ Fail | |
| 2. Data Management | 2.1 Upload Valid Data | ☐ Pass ☐ Fail | |
| 2. Data Management | 2.2 Data Validation | ☐ Pass ☐ Fail | |
| 2. Data Management | 2.3 Data Preview | ☐ Pass ☐ Fail | |
| 3. Training Data | 3.1 Generate QA Pairs | ☐ Pass ☐ Fail | |
| 3. Training Data | 3.2 Dataset Split | ☐ Pass ☐ Fail | |
| 4. Model Training | 4.1 Start Training | ☐ Pass ☐ Fail | |
| 4. Model Training | 4.2 Monitor Progress | ☐ Pass ☐ Fail | |
| 5. Evaluation | 5.1 Start Evaluation | ☐ Pass ☐ Fail | |
| 5. Evaluation | 5.2 View Report | ☐ Pass ☐ Fail | |
| 6. Query Service | 6.1 Single Query | ☐ Pass ☐ Fail | |
| 6. Query Service | 6.2 Fuzzy Query | ☐ Pass ☐ Fail | |
| 6. Query Service | 6.3 No Match Query | ☐ Pass ☐ Fail | |
| 7. Rate Limiting | 7.1 Rate Limit Enforcement | ☐ Pass ☐ Fail | |

### Overall Assessment

**Total Tests**: _____ / 16  
**Passed**: _____  
**Failed**: _____  
**Pass Rate**: _____%

**Recommendation**: ☐ Accept ☐ Accept with Conditions ☐ Reject

**Comments**:
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

---

## Troubleshooting

### Common Issues

#### Issue 1: Cannot Connect to API
**Solution**: 
- Check if server is running: `ps aux | grep uvicorn`
- Check logs: `tail -f logs/app_*.log`
- Restart server: `./scripts/stop.sh && ./scripts/start.sh`

#### Issue 2: Authentication Fails
**Solution**:
- Verify user exists in database
- Check password is correct
- Verify JWT secret is configured in .env

#### Issue 3: Tests Timeout
**Solution**:
- Increase timeout values
- Check system resources (CPU, memory)
- Verify database is not locked

#### Issue 4: Model Training Fails
**Solution**:
- Check GPU/CPU availability
- Verify sufficient disk space
- Check training data is valid
- Review error logs

---

## Sign-off

### Acceptance Criteria Met

- ☐ All functional requirements implemented
- ☐ All test scenarios passed
- ☐ Performance requirements met
- ☐ Accuracy requirements met
- ☐ Documentation complete
- ☐ No critical bugs

### Approvals

**Product Owner**: _______________  Date: _______________

**Technical Lead**: _______________  Date: _______________

**QA Lead**: _______________  Date: _______________

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-11  
**Next Review**: After UAT completion

