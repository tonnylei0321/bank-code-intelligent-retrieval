# 企业级小模型训练平台系统架构设计

## 1. 系统架构概览

### 1.1 整体架构
```
┌─────────────────────────────────────────────────────────────┐
│                    前端展示层 (Frontend)                      │
├─────────────────────────────────────────────────────────────┤
│                    API网关层 (API Gateway)                   │
├─────────────────────────────────────────────────────────────┤
│                    业务服务层 (Business Services)             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │
│  │ 用户管理服务 │ │ 训练管理服务 │ │ 模型管理服务 │ │ 问答服务 │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    数据访问层 (Data Access)                  │
├─────────────────────────────────────────────────────────────┤
│                    基础设施层 (Infrastructure)               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │
│  │   数据库    │ │  文件存储   │ │  消息队列   │ │ 外部API │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 技术栈选型

#### 后端技术栈
- **开发语言**: Python 3.8+
- **Web框架**: FastAPI (高性能异步框架)
- **数据库**: PostgreSQL (主数据库) + Redis (缓存)
- **ORM框架**: SQLAlchemy + Alembic (数据库迁移)
- **任务队列**: Celery + Redis
- **机器学习**: PyTorch + Transformers + PEFT (LoRA)
- **API文档**: OpenAPI/Swagger

#### 前端技术栈
- **框架**: React 18 + TypeScript
- **状态管理**: Redux Toolkit
- **UI组件**: Ant Design
- **构建工具**: Vite
- **HTTP客户端**: Axios

#### 基础设施
- **容器化**: Docker + Docker Compose
- **反向代理**: Nginx
- **监控**: Prometheus + Grafana
- **日志**: ELK Stack (Elasticsearch + Logstash + Kibana)

## 2. 核心服务设计

### 2.1 用户管理服务 (User Service)
```python
# 核心功能
- 用户认证 (JWT Token)
- 用户信息管理 (CRUD)
- 角色权限管理 (RBAC)
- 会话管理
```

**API设计**:
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/refresh` - Token刷新
- `GET /api/users/profile` - 获取用户信息
- `PUT /api/users/profile` - 更新用户信息
- `GET /api/users` - 用户列表 (管理员)
- `POST /api/users` - 创建用户 (管理员)

### 2.2 训练管理服务 (Training Service)
```python
# 核心功能
- 训练任务管理
- 数据预处理
- 模型微调 (LoRA)
- 训练进度监控
- 资源调度
```

**API设计**:
- `POST /api/training/tasks` - 创建训练任务
- `GET /api/training/tasks` - 获取训练任务列表
- `GET /api/training/tasks/{task_id}` - 获取训练任务详情
- `POST /api/training/tasks/{task_id}/start` - 启动训练
- `POST /api/training/tasks/{task_id}/stop` - 停止训练
- `GET /api/training/tasks/{task_id}/progress` - 获取训练进度

### 2.3 数据管理服务 (Data Service)
```python
# 核心功能
- 数据文件上传
- 数据格式验证
- 数据预处理
- 数据版本管理
```

**API设计**:
- `POST /api/data/upload` - 上传数据文件
- `GET /api/data/datasets` - 获取数据集列表
- `GET /api/data/datasets/{dataset_id}` - 获取数据集详情
- `POST /api/data/datasets/{dataset_id}/validate` - 验证数据集
- `GET /api/data/datasets/{dataset_id}/preview` - 预览数据

### 2.4 模型管理服务 (Model Service)
```python
# 核心功能
- 模型注册
- 模型版本管理
- 模型测试验证
- 模型部署
```

**API设计**:
- `GET /api/models` - 获取模型列表
- `POST /api/models` - 注册新模型
- `GET /api/models/{model_id}` - 获取模型详情
- `POST /api/models/{model_id}/test` - 测试模型
- `POST /api/models/{model_id}/deploy` - 部署模型

### 2.5 问答服务 (QA Service)
```python
# 核心功能
- 智能问答
- 历史记录管理
- 结果缓存
- 性能监控
```

**API设计**:
- `POST /api/qa/ask` - 提交问题
- `GET /api/qa/history` - 获取问答历史
- `GET /api/qa/history/{session_id}` - 获取会话历史
- `DELETE /api/qa/history/{history_id}` - 删除历史记录

## 3. 数据库设计

### 3.1 核心数据表

#### 用户表 (users)
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 数据集表 (datasets)
```sql
CREATE TABLE datasets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    record_count INTEGER,
    format VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'uploaded',
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 训练任务表 (training_tasks)
```sql
CREATE TABLE training_tasks (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    dataset_id INTEGER REFERENCES datasets(id),
    model_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'created',
    progress FLOAT DEFAULT 0.0,
    config JSONB,
    result JSONB,
    created_by INTEGER REFERENCES users(id),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 模型表 (models)
```sql
CREATE TABLE models (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    version VARCHAR(20) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    model_path VARCHAR(500) NOT NULL,
    training_task_id INTEGER REFERENCES training_tasks(id),
    accuracy FLOAT,
    status VARCHAR(20) DEFAULT 'registered',
    is_active BOOLEAN DEFAULT false,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 问答历史表 (qa_history)
```sql
CREATE TABLE qa_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    session_id VARCHAR(100),
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    model_id INTEGER REFERENCES models(id),
    response_time INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 索引设计
```sql
-- 用户表索引
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

-- 数据集表索引
CREATE INDEX idx_datasets_created_by ON datasets(created_by);
CREATE INDEX idx_datasets_status ON datasets(status);

-- 训练任务表索引
CREATE INDEX idx_training_tasks_dataset_id ON training_tasks(dataset_id);
CREATE INDEX idx_training_tasks_status ON training_tasks(status);
CREATE INDEX idx_training_tasks_created_by ON training_tasks(created_by);

-- 模型表索引
CREATE INDEX idx_models_training_task_id ON models(training_task_id);
CREATE INDEX idx_models_status ON models(status);
CREATE INDEX idx_models_is_active ON models(is_active);

-- 问答历史表索引
CREATE INDEX idx_qa_history_user_id ON qa_history(user_id);
CREATE INDEX idx_qa_history_session_id ON qa_history(session_id);
CREATE INDEX idx_qa_history_created_at ON qa_history(created_at);
```

## 4. 安全设计

### 4.1 认证授权
- **JWT Token**: 无状态认证，支持Token刷新
- **RBAC权限模型**: 基于角色的访问控制
- **API权限验证**: 每个接口都进行权限检查

### 4.2 数据安全
- **密码加密**: 使用bcrypt进行密码哈希
- **数据传输**: HTTPS加密传输
- **敏感数据**: 数据库敏感字段加密存储
- **API限流**: 防止恶意请求

### 4.3 文件安全
- **文件类型验证**: 严格验证上传文件类型
- **文件大小限制**: 限制单文件最大大小
- **路径安全**: 防止路径遍历攻击
- **病毒扫描**: 上传文件病毒扫描

## 5. 性能优化设计

### 5.1 缓存策略
- **Redis缓存**: 用户会话、API响应缓存
- **模型缓存**: 训练好的模型内存缓存
- **查询缓存**: 频繁查询结果缓存

### 5.2 异步处理
- **Celery任务队列**: 训练任务异步执行
- **WebSocket**: 实时进度推送
- **批处理**: 大数据量批量处理

### 5.3 数据库优化
- **连接池**: 数据库连接池管理
- **查询优化**: SQL查询优化和索引优化
- **分页查询**: 大数据量分页处理

## 6. 监控告警设计

### 6.1 系统监控
- **应用监控**: API响应时间、错误率
- **资源监控**: CPU、内存、磁盘使用率
- **业务监控**: 训练任务成功率、模型准确率

### 6.2 日志管理
- **结构化日志**: JSON格式日志
- **日志级别**: DEBUG、INFO、WARN、ERROR
- **日志收集**: ELK Stack集中收集分析

### 6.3 告警机制
- **阈值告警**: 系统资源使用率告警
- **异常告警**: 训练失败、系统异常告警
- **业务告警**: 模型准确率下降告警

---

**文档版本**: v1.0  
**设计日期**: 2026-01-08  
**下一步**: 详细API设计和数据库建模