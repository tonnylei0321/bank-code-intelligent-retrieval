# API接口规范设计

## 1. API设计原则

### 1.1 RESTful设计
- 使用标准HTTP方法 (GET, POST, PUT, DELETE)
- 资源导向的URL设计
- 统一的响应格式
- 合理的HTTP状态码

### 1.2 版本控制
- URL版本控制: `/api/v1/`
- 向后兼容原则
- 版本废弃通知机制

### 1.3 统一响应格式
```json
{
  "code": 200,
  "message": "success",
  "data": {},
  "timestamp": "2026-01-08T10:30:00Z",
  "request_id": "uuid"
}
```

## 2. 认证授权API

### 2.1 用户登录
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "password123"
}
```

**响应**:
```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "user": {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com",
      "role": "admin"
    }
  }
}
```

### 2.2 Token刷新
```http
POST /api/v1/auth/refresh
Authorization: Bearer {refresh_token}
```

### 2.3 用户登出
```http
POST /api/v1/auth/logout
Authorization: Bearer {access_token}
```

## 3. 用户管理API

### 3.1 获取用户信息
```http
GET /api/v1/users/profile
Authorization: Bearer {access_token}
```

### 3.2 更新用户信息
```http
PUT /api/v1/users/profile
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "email": "newemail@example.com",
  "password": "newpassword123"
}
```

### 3.3 用户列表 (管理员)
```http
GET /api/v1/users?page=1&size=20&role=user
Authorization: Bearer {access_token}
```

**响应**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "users": [
      {
        "id": 1,
        "username": "user1",
        "email": "user1@example.com",
        "role": "user",
        "is_active": true,
        "created_at": "2026-01-08T10:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "size": 20,
      "total": 100,
      "pages": 5
    }
  }
}
```

### 3.4 创建用户 (管理员)
```http
POST /api/v1/users
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "password123",
  "role": "user"
}
```

## 4. 数据管理API

### 4.1 上传数据文件
```http
POST /api/v1/data/upload
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

file: [binary data]
name: "联行号数据集"
description: "2026年最新联行号数据"
```

**响应**:
```json
{
  "code": 200,
  "message": "文件上传成功",
  "data": {
    "dataset_id": 1,
    "name": "联行号数据集",
    "file_size": 1048576,
    "record_count": 150000,
    "format": "csv",
    "status": "uploaded"
  }
}
```

### 4.2 获取数据集列表
```http
GET /api/v1/data/datasets?page=1&size=20&status=validated
Authorization: Bearer {access_token}
```

### 4.3 数据集详情
```http
GET /api/v1/data/datasets/1
Authorization: Bearer {access_token}
```

### 4.4 验证数据集
```http
POST /api/v1/data/datasets/1/validate
Authorization: Bearer {access_token}
```

**响应**:
```json
{
  "code": 200,
  "message": "数据验证完成",
  "data": {
    "dataset_id": 1,
    "status": "validated",
    "validation_result": {
      "total_records": 150000,
      "valid_records": 149950,
      "invalid_records": 50,
      "error_details": [
        {
          "line": 1001,
          "error": "联行号格式错误",
          "data": "中国银行北京分行,invalid_code,123456"
        }
      ]
    }
  }
}
```

### 4.5 预览数据
```http
GET /api/v1/data/datasets/1/preview?limit=100
Authorization: Bearer {access_token}
```

## 5. 训练管理API

### 5.1 创建训练任务
```http
POST /api/v1/training/tasks
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "联行号检索模型训练",
  "dataset_id": 1,
  "model_type": "bank_code_retrieval",
  "config": {
    "base_model": "Qwen3-0.6B",
    "lora_config": {
      "r": 16,
      "lora_alpha": 32,
      "target_modules": ["q_proj", "v_proj"],
      "lora_dropout": 0.1
    },
    "training_args": {
      "num_train_epochs": 3,
      "learning_rate": 2e-4,
      "batch_size": 16,
      "warmup_steps": 100
    }
  }
}
```

### 5.2 启动训练任务
```http
POST /api/v1/training/tasks/1/start
Authorization: Bearer {access_token}
```

### 5.3 获取训练进度
```http
GET /api/v1/training/tasks/1/progress
Authorization: Bearer {access_token}
```

**响应**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "task_id": 1,
    "status": "training",
    "progress": 65.5,
    "current_epoch": 2,
    "total_epochs": 3,
    "current_step": 1310,
    "total_steps": 2000,
    "metrics": {
      "loss": 0.0234,
      "accuracy": 0.9987,
      "learning_rate": 1.8e-4
    },
    "estimated_remaining_time": 1800,
    "started_at": "2026-01-08T10:00:00Z"
  }
}
```

### 5.4 停止训练任务
```http
POST /api/v1/training/tasks/1/stop
Authorization: Bearer {access_token}
```

### 5.5 获取训练任务列表
```http
GET /api/v1/training/tasks?page=1&size=20&status=completed
Authorization: Bearer {access_token}
```

## 6. 模型管理API

### 6.1 获取模型列表
```http
GET /api/v1/models?page=1&size=20&model_type=bank_code_retrieval
Authorization: Bearer {access_token}
```

**响应**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "models": [
      {
        "id": 1,
        "name": "联行号检索模型",
        "version": "v1.0.0",
        "model_type": "bank_code_retrieval",
        "accuracy": 0.9995,
        "status": "active",
        "is_active": true,
        "created_at": "2026-01-08T12:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "size": 20,
      "total": 5,
      "pages": 1
    }
  }
}
```

### 6.2 模型详情
```http
GET /api/v1/models/1
Authorization: Bearer {access_token}
```

### 6.3 测试模型
```http
POST /api/v1/models/1/test
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "test_data": [
    {
      "query": "中国工商银行北京分行的联行号是什么？",
      "expected": "102100000017"
    }
  ]
}
```

**响应**:
```json
{
  "code": 200,
  "message": "模型测试完成",
  "data": {
    "model_id": 1,
    "test_results": [
      {
        "query": "中国工商银行北京分行的联行号是什么？",
        "expected": "102100000017",
        "predicted": "102100000017",
        "confidence": 0.9998,
        "is_correct": true,
        "response_time": 45
      }
    ],
    "summary": {
      "total_tests": 1,
      "correct_predictions": 1,
      "accuracy": 1.0,
      "avg_response_time": 45,
      "avg_confidence": 0.9998
    }
  }
}
```

### 6.4 部署模型
```http
POST /api/v1/models/1/deploy
Authorization: Bearer {access_token}
```

## 7. 问答服务API

### 7.1 提交问题
```http
POST /api/v1/qa/ask
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "question": "中国建设银行上海分行的联行号是多少？",
  "session_id": "session_123",
  "model_id": 1
}
```

**响应**:
```json
{
  "code": 200,
  "message": "问答成功",
  "data": {
    "question": "中国建设银行上海分行的联行号是多少？",
    "answer": "中国建设银行上海分行的联行号是105290000013",
    "confidence": 0.9996,
    "response_time": 89,
    "session_id": "session_123",
    "model_info": {
      "model_id": 1,
      "model_name": "联行号检索模型",
      "version": "v1.0.0"
    },
    "created_at": "2026-01-08T14:30:00Z"
  }
}
```

### 7.2 获取问答历史
```http
GET /api/v1/qa/history?page=1&size=20&session_id=session_123
Authorization: Bearer {access_token}
```

### 7.3 获取会话历史
```http
GET /api/v1/qa/history/session_123
Authorization: Bearer {access_token}
```

### 7.4 删除历史记录
```http
DELETE /api/v1/qa/history/1
Authorization: Bearer {access_token}
```

## 8. 系统监控API

### 8.1 系统状态
```http
GET /api/v1/system/status
Authorization: Bearer {access_token}
```

**响应**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "system": {
      "status": "healthy",
      "uptime": 86400,
      "version": "1.0.0"
    },
    "database": {
      "status": "connected",
      "connections": 15,
      "max_connections": 100
    },
    "redis": {
      "status": "connected",
      "memory_usage": "256MB",
      "connected_clients": 8
    },
    "training": {
      "active_tasks": 2,
      "queued_tasks": 1,
      "completed_tasks": 15
    }
  }
}
```

### 8.2 性能指标
```http
GET /api/v1/system/metrics
Authorization: Bearer {access_token}
```

## 9. 错误码定义

| 错误码 | HTTP状态码 | 描述 | 示例 |
|--------|------------|------|------|
| 200 | 200 | 成功 | 操作成功完成 |
| 400 | 400 | 请求参数错误 | 缺少必需参数 |
| 401 | 401 | 未授权 | Token无效或过期 |
| 403 | 403 | 权限不足 | 无权限访问该资源 |
| 404 | 404 | 资源不存在 | 用户或数据不存在 |
| 409 | 409 | 资源冲突 | 用户名已存在 |
| 422 | 422 | 数据验证失败 | 数据格式不正确 |
| 429 | 429 | 请求过于频繁 | API调用超过限制 |
| 500 | 500 | 服务器内部错误 | 系统异常 |
| 503 | 503 | 服务不可用 | 系统维护中 |

## 10. API限流规则

### 10.1 限流策略
- **用户级限流**: 每用户每分钟最多100次请求
- **IP级限流**: 每IP每分钟最多200次请求
- **接口级限流**: 特殊接口单独限制

### 10.2 限流响应
```json
{
  "code": 429,
  "message": "请求过于频繁，请稍后再试",
  "data": {
    "retry_after": 60,
    "limit": 100,
    "remaining": 0,
    "reset_time": "2026-01-08T15:01:00Z"
  }
}
```

---

**文档版本**: v1.0  
**设计日期**: 2026-01-08  
**下一步**: 数据库详细设计和部署架构