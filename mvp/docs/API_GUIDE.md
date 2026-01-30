# API使用指南

## 目录

- [概述](#概述)
- [认证流程](#认证流程)
- [API端点](#api端点)
  - [认证相关](#认证相关)
  - [数据管理](#数据管理)
  - [训练数据生成](#训练数据生成)
  - [模型训练](#模型训练)
  - [模型评估](#模型评估)
  - [问答查询](#问答查询)
  - [日志查询](#日志查询)
  - [管理员功能](#管理员功能)
- [错误处理](#错误处理)
- [常见问题](#常见问题)

## 概述

联行号检索模型训练验证系统提供RESTful API接口，支持数据管理、模型训练、评估和问答查询等功能。

**基础URL**: `http://localhost:8000`

**API版本**: v1

**数据格式**: JSON

## 认证流程

### 1. 用户登录

获取JWT Token用于后续API调用。

**端点**: `POST /api/v1/auth/login`

**请求体**:
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**响应示例**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### 2. 使用Token

在后续请求的Header中添加Token：

```bash
Authorization: Bearer <access_token>
```

**示例**:
```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
     http://localhost:8000/api/v1/datasets
```

### 3. Token过期处理

Token有效期为24小时。当Token过期时，API会返回401状态码，需要重新登录获取新Token。

## API端点

### 认证相关

#### 登录

**端点**: `POST /api/v1/auth/login`

**权限**: 无需认证

**请求体**:
```json
{
  "username": "string",
  "password": "string"
}
```

**响应**:
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 86400
}
```

**示例**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

#### 获取当前用户信息

**端点**: `GET /api/v1/auth/me`

**权限**: 需要认证

**响应**:
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "role": "admin",
  "is_active": true,
  "created_at": "2026-01-10T10:00:00"
}
```

### 数据管理

#### 上传数据集

**端点**: `POST /api/v1/datasets/upload`

**权限**: 管理员

**请求**: multipart/form-data

**参数**:
- `file`: CSV文件（必需）

**CSV格式要求**:
- 包含三列：银行名称、联行号、清算行行号
- 编码：UTF-8
- 示例：
```csv
银行名称,联行号,清算行行号
中国工商银行北京分行,102100000026,102100000000
中国农业银行上海分行,103290000012,103290000000
```

**响应**:
```json
{
  "id": 1,
  "filename": "bank_codes.csv",
  "total_records": 150000,
  "valid_records": 149850,
  "invalid_records": 150,
  "status": "uploaded",
  "upload_time": "2026-01-10T10:00:00"
}
```

**示例**:
```bash
curl -X POST http://localhost:8000/api/v1/datasets/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@bank_codes.csv"
```

#### 获取数据集列表

**端点**: `GET /api/v1/datasets`

**权限**: 需要认证

**查询参数**:
- `skip`: 跳过记录数（默认：0）
- `limit`: 返回记录数（默认：10）

**响应**:
```json
{
  "total": 5,
  "items": [
    {
      "id": 1,
      "filename": "bank_codes.csv",
      "total_records": 150000,
      "valid_records": 149850,
      "status": "indexed",
      "created_at": "2026-01-10T10:00:00"
    }
  ]
}
```

#### 获取数据集详情

**端点**: `GET /api/v1/datasets/{dataset_id}`

**权限**: 需要认证

**响应**:
```json
{
  "id": 1,
  "filename": "bank_codes.csv",
  "total_records": 150000,
  "valid_records": 149850,
  "invalid_records": 150,
  "status": "indexed",
  "upload_time": "2026-01-10T10:00:00",
  "statistics": {
    "unique_banks": 500,
    "unique_codes": 149850
  }
}
```

#### 预览数据

**端点**: `GET /api/v1/datasets/{dataset_id}/preview`

**权限**: 需要认证

**查询参数**:
- `limit`: 返回记录数（默认：100，最大：100）

**响应**:
```json
{
  "dataset_id": 1,
  "records": [
    {
      "id": 1,
      "bank_name": "中国工商银行北京分行",
      "bank_code": "102100000026",
      "clearing_code": "102100000000"
    }
  ],
  "total": 100
}
```

### 训练数据生成

#### 生成问答对

**端点**: `POST /api/v1/qa-pairs/generate`

**权限**: 管理员

**请求体**:
```json
{
  "dataset_id": 1,
  "question_types": ["exact", "fuzzy", "reverse", "natural"],
  "samples_per_record": 4
}
```

**响应**:
```json
{
  "task_id": "gen_123",
  "dataset_id": 1,
  "status": "running",
  "progress": 0,
  "estimated_time": 3600
}
```

**示例**:
```bash
curl -X POST http://localhost:8000/api/v1/qa-pairs/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": 1}'
```

#### 获取问答对统计

**端点**: `GET /api/v1/qa-pairs/{dataset_id}/stats`

**权限**: 需要认证

**响应**:
```json
{
  "dataset_id": 1,
  "total_pairs": 600000,
  "by_type": {
    "exact": 150000,
    "fuzzy": 150000,
    "reverse": 150000,
    "natural": 150000
  },
  "by_split": {
    "train": 480000,
    "val": 60000,
    "test": 60000
  }
}
```

#### 查询问答对

**端点**: `GET /api/v1/qa-pairs/{dataset_id}`

**权限**: 需要认证

**查询参数**:
- `skip`: 跳过记录数（默认：0）
- `limit`: 返回记录数（默认：10）
- `question_type`: 问题类型过滤（可选）
- `split_type`: 数据集类型过滤（可选）

**响应**:
```json
{
  "total": 600000,
  "items": [
    {
      "id": 1,
      "question": "中国工商银行北京分行的联行号是什么？",
      "answer": "102100000026",
      "question_type": "exact",
      "split_type": "train",
      "generated_at": "2026-01-10T11:00:00"
    }
  ]
}
```

### 模型训练

#### 启动训练任务

**端点**: `POST /api/v1/training/start`

**权限**: 管理员

**请求体**:
```json
{
  "dataset_id": 1,
  "config": {
    "learning_rate": 0.0002,
    "batch_size": 16,
    "num_epochs": 3,
    "lora_r": 16,
    "lora_alpha": 32,
    "lora_dropout": 0.05
  }
}
```

**响应**:
```json
{
  "job_id": 1,
  "dataset_id": 1,
  "status": "pending",
  "config": {...},
  "created_at": "2026-01-10T12:00:00"
}
```

**示例**:
```bash
curl -X POST http://localhost:8000/api/v1/training/start \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": 1}'
```

#### 查询训练状态

**端点**: `GET /api/v1/training/{job_id}`

**权限**: 需要认证

**响应**:
```json
{
  "job_id": 1,
  "dataset_id": 1,
  "status": "running",
  "progress": 45.5,
  "current_epoch": 2,
  "total_epochs": 3,
  "train_loss": 0.234,
  "val_loss": 0.256,
  "val_accuracy": 0.923,
  "started_at": "2026-01-10T12:00:00",
  "estimated_completion": "2026-01-10T18:00:00"
}
```

#### 停止训练任务

**端点**: `POST /api/v1/training/{job_id}/stop`

**权限**: 管理员

**响应**:
```json
{
  "job_id": 1,
  "status": "stopped",
  "message": "Training job stopped successfully"
}
```

#### 获取训练任务列表

**端点**: `GET /api/v1/training/jobs`

**权限**: 需要认证

**查询参数**:
- `status`: 状态过滤（可选）
- `skip`: 跳过记录数（默认：0）
- `limit`: 返回记录数（默认：10）

**响应**:
```json
{
  "total": 10,
  "items": [
    {
      "job_id": 1,
      "dataset_id": 1,
      "status": "completed",
      "val_accuracy": 0.956,
      "started_at": "2026-01-10T12:00:00",
      "completed_at": "2026-01-10T18:30:00"
    }
  ]
}
```

### 模型评估

#### 启动评估任务

**端点**: `POST /api/v1/evaluation/start`

**权限**: 管理员

**请求体**:
```json
{
  "training_job_id": 1,
  "evaluation_type": "model",
  "include_baseline": true
}
```

**响应**:
```json
{
  "eval_id": 1,
  "training_job_id": 1,
  "status": "running",
  "created_at": "2026-01-10T19:00:00"
}
```

#### 查询评估状态

**端点**: `GET /api/v1/evaluation/{eval_id}`

**权限**: 需要认证

**响应**:
```json
{
  "eval_id": 1,
  "training_job_id": 1,
  "status": "completed",
  "metrics": {
    "accuracy": 0.956,
    "precision": 0.958,
    "recall": 0.954,
    "f1_score": 0.956,
    "avg_response_time": 234.5,
    "p95_response_time": 456.7
  },
  "evaluated_at": "2026-01-10T19:30:00"
}
```

#### 获取评估报告

**端点**: `GET /api/v1/evaluation/{eval_id}/report`

**权限**: 需要认证

**响应**: Markdown格式的评估报告

**示例**:
```bash
curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/api/v1/evaluation/1/report \
     -o evaluation_report.md
```

### 问答查询

#### 单次查询

**端点**: `POST /api/v1/query`

**权限**: 需要认证

**请求体**:
```json
{
  "question": "中国工商银行北京分行的联行号是什么？"
}
```

**响应**:
```json
{
  "question": "中国工商银行北京分行的联行号是什么？",
  "answer": "中国工商银行北京分行的联行号是102100000026",
  "confidence": 0.95,
  "response_time": 234.5,
  "matched_records": [
    {
      "bank_name": "中国工商银行北京分行",
      "bank_code": "102100000026",
      "clearing_code": "102100000000"
    }
  ],
  "timestamp": "2026-01-10T20:00:00"
}
```

**示例**:
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"question": "工行北京的联行号"}'
```

#### 批量查询

**端点**: `POST /api/v1/query/batch`

**权限**: 需要认证

**请求体**:
```json
{
  "questions": [
    "中国工商银行北京分行的联行号是什么？",
    "农行上海分行的联行号"
  ]
}
```

**响应**:
```json
{
  "results": [
    {
      "question": "中国工商银行北京分行的联行号是什么？",
      "answer": "...",
      "confidence": 0.95
    },
    {
      "question": "农行上海分行的联行号",
      "answer": "...",
      "confidence": 0.92
    }
  ],
  "total": 2,
  "avg_response_time": 245.3
}
```

#### 查询历史

**端点**: `GET /api/v1/query/history`

**权限**: 需要认证

**查询参数**:
- `skip`: 跳过记录数（默认：0）
- `limit`: 返回记录数（默认：10）
- `start_date`: 开始日期（可选）
- `end_date`: 结束日期（可选）

**响应**:
```json
{
  "total": 1000,
  "items": [
    {
      "id": 1,
      "question": "...",
      "answer": "...",
      "confidence": 0.95,
      "response_time": 234.5,
      "created_at": "2026-01-10T20:00:00"
    }
  ]
}
```

### 日志查询

#### 查询日志

**端点**: `GET /api/v1/logs`

**权限**: 管理员

**查询参数**:
- `start_date`: 开始日期（可选）
- `end_date`: 结束日期（可选）
- `level`: 日志级别（可选：INFO, WARNING, ERROR）
- `task_id`: 任务ID（可选）
- `skip`: 跳过记录数（默认：0）
- `limit`: 返回记录数（默认：100）

**响应**:
```json
{
  "total": 5000,
  "items": [
    {
      "timestamp": "2026-01-10T20:00:00",
      "level": "INFO",
      "message": "Training job 1 started",
      "task_id": 1,
      "details": {...}
    }
  ]
}
```

**示例**:
```bash
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8000/api/v1/logs?level=ERROR&limit=50"
```

### 管理员功能

#### 创建用户

**端点**: `POST /api/v1/admin/users`

**权限**: 管理员

**请求体**:
```json
{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "password123",
  "role": "user"
}
```

**响应**:
```json
{
  "id": 2,
  "username": "newuser",
  "email": "newuser@example.com",
  "role": "user",
  "is_active": true,
  "created_at": "2026-01-10T21:00:00"
}
```

#### 获取用户列表

**端点**: `GET /api/v1/admin/users`

**权限**: 管理员

**响应**:
```json
{
  "total": 10,
  "items": [
    {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com",
      "role": "admin",
      "is_active": true
    }
  ]
}
```

#### 更新用户

**端点**: `PUT /api/v1/admin/users/{user_id}`

**权限**: 管理员

**请求体**:
```json
{
  "email": "newemail@example.com",
  "role": "admin",
  "is_active": false
}
```

#### 删除用户

**端点**: `DELETE /api/v1/admin/users/{user_id}`

**权限**: 管理员

**响应**:
```json
{
  "message": "User deleted successfully"
}
```

## 错误处理

### 错误响应格式

所有错误响应遵循统一格式：

```json
{
  "success": false,
  "error_code": "ERROR_CODE",
  "error_message": "Human readable error message",
  "error_details": {
    "field": "Additional error details"
  },
  "timestamp": "2026-01-10T20:00:00",
  "request_id": "req_123456"
}
```

### 常见错误码

#### 客户端错误 (4xx)

| 状态码 | 错误码 | 说明 | 解决方法 |
|--------|--------|------|----------|
| 400 | BAD_REQUEST | 请求参数错误 | 检查请求参数格式和类型 |
| 401 | UNAUTHORIZED | 未认证或Token过期 | 重新登录获取新Token |
| 403 | FORBIDDEN | 权限不足 | 使用管理员账号或联系管理员 |
| 404 | NOT_FOUND | 资源不存在 | 检查资源ID是否正确 |
| 422 | VALIDATION_ERROR | 数据验证失败 | 检查请求数据格式 |
| 429 | RATE_LIMIT_EXCEEDED | 请求频率超限 | 等待后重试 |

#### 服务器错误 (5xx)

| 状态码 | 错误码 | 说明 | 解决方法 |
|--------|--------|------|----------|
| 500 | INTERNAL_ERROR | 服务器内部错误 | 联系技术支持 |
| 503 | SERVICE_UNAVAILABLE | 服务暂时不可用 | 稍后重试 |

### 错误处理示例

#### 示例1: Token过期

**请求**:
```bash
curl -H "Authorization: Bearer expired_token" \
     http://localhost:8000/api/v1/datasets
```

**响应** (401):
```json
{
  "success": false,
  "error_code": "TOKEN_EXPIRED",
  "error_message": "JWT token has expired",
  "timestamp": "2026-01-10T20:00:00"
}
```

**解决**: 重新登录获取新Token

#### 示例2: 权限不足

**请求**:
```bash
curl -X POST http://localhost:8000/api/v1/training/start \
  -H "Authorization: Bearer user_token" \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": 1}'
```

**响应** (403):
```json
{
  "success": false,
  "error_code": "INSUFFICIENT_PERMISSIONS",
  "error_message": "Admin role required for this operation",
  "timestamp": "2026-01-10T20:00:00"
}
```

**解决**: 使用管理员账号

#### 示例3: 数据验证失败

**请求**:
```bash
curl -X POST http://localhost:8000/api/v1/datasets/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@invalid.txt"
```

**响应** (422):
```json
{
  "success": false,
  "error_code": "INVALID_FILE_FORMAT",
  "error_message": "File format validation failed",
  "error_details": {
    "expected_format": "CSV with 3 columns",
    "actual_format": "TXT file"
  },
  "timestamp": "2026-01-10T20:00:00"
}
```

**解决**: 上传正确格式的CSV文件

#### 示例4: 频率限制

**响应** (429):
```json
{
  "success": false,
  "error_code": "RATE_LIMIT_EXCEEDED",
  "error_message": "Too many requests",
  "error_details": {
    "limit": 100,
    "window": "1 minute",
    "retry_after": 45
  },
  "timestamp": "2026-01-10T20:00:00"
}
```

**解决**: 等待45秒后重试

## 常见问题

### Q1: 如何获取管理员权限？

A: 系统初始化时会创建默认管理员账号（username: admin, password: admin123）。首次登录后请立即修改密码。

### Q2: 上传的CSV文件格式要求是什么？

A: CSV文件必须包含三列：银行名称、联行号、清算行行号。文件编码必须是UTF-8。示例：
```csv
银行名称,联行号,清算行行号
中国工商银行北京分行,102100000026,102100000000
```

### Q3: 训练任务需要多长时间？

A: 使用15万条数据训练通常需要6-8小时（取决于硬件配置）。可以通过查询训练状态API获取预计完成时间。

### Q4: 如何查看训练进度？

A: 使用 `GET /api/v1/training/{job_id}` 端点查询训练状态，返回的 `progress` 字段表示完成百分比。

### Q5: 查询响应时间过长怎么办？

A: 
1. 检查模型是否已加载到内存
2. 检查服务器资源使用情况
3. 考虑使用批量查询接口提高效率

### Q6: Token过期后如何处理？

A: Token有效期为24小时。过期后会收到401错误，需要重新调用登录接口获取新Token。

### Q7: 如何处理"未找到"的查询结果？

A: 系统会返回200状态码，但 `matched_records` 为空数组，`answer` 包含"未找到"提示。这不是错误，而是正常的查询结果。

### Q8: 可以同时运行多个训练任务吗？

A: 当前版本不支持并发训练。如果尝试启动新任务时已有任务在运行，会返回错误提示。

### Q9: 如何导出评估报告？

A: 使用 `GET /api/v1/evaluation/{eval_id}/report` 端点，返回Markdown格式的报告，可以保存为文件。

### Q10: API有请求频率限制吗？

A: 是的，所有API端点限制为每分钟100次请求。超过限制会返回429状态码。

## 技术支持

如有其他问题，请联系技术支持团队或查看项目文档。

---

**文档版本**: v1.0  
**更新日期**: 2026-01-11  
**维护者**: 系统开发团队
