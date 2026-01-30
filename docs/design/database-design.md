# 数据库详细设计

## 1. 数据库选型

### 1.1 主数据库: PostgreSQL 14+
**选择理由**:
- 支持JSONB类型，适合存储训练配置和结果
- 优秀的并发性能和事务支持
- 丰富的索引类型和查询优化
- 企业级稳定性和可靠性

### 1.2 缓存数据库: Redis 6+
**选择理由**:
- 高性能内存存储
- 支持多种数据结构
- 适合会话管理和缓存
- 支持发布订阅模式

## 2. 数据表详细设计

### 2.1 用户管理相关表

#### users (用户表)
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_active ON users(is_active);

-- 注释
COMMENT ON TABLE users IS '用户表';
COMMENT ON COLUMN users.username IS '用户名，唯一';
COMMENT ON COLUMN users.email IS '邮箱地址，唯一';
COMMENT ON COLUMN users.password_hash IS '密码哈希值';
COMMENT ON COLUMN users.role IS '用户角色：admin-管理员，user-普通用户';
```

#### user_sessions (用户会话表)
```sql
CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    refresh_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_session_token ON user_sessions(session_token);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);

-- 注释
COMMENT ON TABLE user_sessions IS '用户会话表';
```

### 2.2 数据管理相关表

#### datasets (数据集表)
```sql
CREATE TABLE datasets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    file_path VARCHAR(500) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    record_count INTEGER,
    format VARCHAR(20) NOT NULL CHECK (format IN ('csv', 'txt', 'excel')),
    status VARCHAR(20) DEFAULT 'uploaded' CHECK (status IN ('uploaded', 'validating', 'validated', 'error')),
    validation_result JSONB,
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_datasets_created_by ON datasets(created_by);
CREATE INDEX idx_datasets_status ON datasets(status);
CREATE INDEX idx_datasets_format ON datasets(format);
CREATE INDEX idx_datasets_created_at ON datasets(created_at);
CREATE INDEX idx_datasets_file_hash ON datasets(file_hash);

-- 注释
COMMENT ON TABLE datasets IS '数据集表';
COMMENT ON COLUMN datasets.file_hash IS '文件SHA256哈希值，用于去重';
COMMENT ON COLUMN datasets.validation_result IS '数据验证结果JSON';
```

#### dataset_records (数据记录表)
```sql
CREATE TABLE dataset_records (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL,
    bank_name VARCHAR(200) NOT NULL,
    bank_code VARCHAR(50) NOT NULL,
    clearing_code VARCHAR(50) NOT NULL,
    is_valid BOOLEAN DEFAULT true,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_dataset_records_dataset_id ON dataset_records(dataset_id);
CREATE INDEX idx_dataset_records_bank_code ON dataset_records(bank_code);
CREATE INDEX idx_dataset_records_is_valid ON dataset_records(is_valid);

-- 注释
COMMENT ON TABLE dataset_records IS '数据集记录表';
COMMENT ON COLUMN dataset_records.bank_name IS '银行名称';
COMMENT ON COLUMN dataset_records.bank_code IS '联行号';
COMMENT ON COLUMN dataset_records.clearing_code IS '清算行行号';
```

### 2.3 训练管理相关表

#### training_tasks (训练任务表)
```sql
CREATE TABLE training_tasks (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    dataset_id INTEGER NOT NULL REFERENCES datasets(id),
    model_type VARCHAR(50) NOT NULL,
    base_model VARCHAR(100) NOT NULL DEFAULT 'Qwen3-0.6B',
    status VARCHAR(20) DEFAULT 'created' CHECK (status IN ('created', 'queued', 'training', 'completed', 'failed', 'stopped')),
    progress FLOAT DEFAULT 0.0 CHECK (progress >= 0 AND progress <= 100),
    config JSONB NOT NULL,
    result JSONB,
    error_message TEXT,
    created_by INTEGER NOT NULL REFERENCES users(id),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_training_tasks_dataset_id ON training_tasks(dataset_id);
CREATE INDEX idx_training_tasks_status ON training_tasks(status);
CREATE INDEX idx_training_tasks_created_by ON training_tasks(created_by);
CREATE INDEX idx_training_tasks_model_type ON training_tasks(model_type);
CREATE INDEX idx_training_tasks_created_at ON training_tasks(created_at);

-- 注释
COMMENT ON TABLE training_tasks IS '训练任务表';
COMMENT ON COLUMN training_tasks.config IS '训练配置JSON，包含LoRA参数等';
COMMENT ON COLUMN training_tasks.result IS '训练结果JSON，包含指标等';
```

#### training_logs (训练日志表)
```sql
CREATE TABLE training_logs (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES training_tasks(id) ON DELETE CASCADE,
    epoch INTEGER,
    step INTEGER,
    loss FLOAT,
    accuracy FLOAT,
    learning_rate FLOAT,
    metrics JSONB,
    log_level VARCHAR(10) DEFAULT 'INFO' CHECK (log_level IN ('DEBUG', 'INFO', 'WARN', 'ERROR')),
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_training_logs_task_id ON training_logs(task_id);
CREATE INDEX idx_training_logs_epoch_step ON training_logs(task_id, epoch, step);
CREATE INDEX idx_training_logs_created_at ON training_logs(created_at);

-- 注释
COMMENT ON TABLE training_logs IS '训练日志表';
```

### 2.4 模型管理相关表

#### models (模型表)
```sql
CREATE TABLE models (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    version VARCHAR(20) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    base_model VARCHAR(100) NOT NULL,
    model_path VARCHAR(500) NOT NULL,
    config_path VARCHAR(500),
    training_task_id INTEGER REFERENCES training_tasks(id),
    accuracy FLOAT,
    model_size BIGINT,
    status VARCHAR(20) DEFAULT 'registered' CHECK (status IN ('registered', 'testing', 'active', 'inactive', 'deprecated')),
    is_active BOOLEAN DEFAULT false,
    test_results JSONB,
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, version)
);

-- 索引
CREATE INDEX idx_models_training_task_id ON models(training_task_id);
CREATE INDEX idx_models_status ON models(status);
CREATE INDEX idx_models_is_active ON models(is_active);
CREATE INDEX idx_models_model_type ON models(model_type);
CREATE INDEX idx_models_created_by ON models(created_by);

-- 注释
COMMENT ON TABLE models IS '模型表';
COMMENT ON COLUMN models.model_path IS '模型文件路径';
COMMENT ON COLUMN models.config_path IS '模型配置文件路径';
COMMENT ON COLUMN models.test_results IS '模型测试结果JSON';
```

#### model_versions (模型版本表)
```sql
CREATE TABLE model_versions (
    id SERIAL PRIMARY KEY,
    model_id INTEGER NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    version VARCHAR(20) NOT NULL,
    changelog TEXT,
    is_current BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(model_id, version)
);

-- 索引
CREATE INDEX idx_model_versions_model_id ON model_versions(model_id);
CREATE INDEX idx_model_versions_is_current ON model_versions(is_current);

-- 注释
COMMENT ON TABLE model_versions IS '模型版本表';
```

### 2.5 问答服务相关表

#### qa_sessions (问答会话表)
```sql
CREATE TABLE qa_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id),
    model_id INTEGER REFERENCES models(id),
    title VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_qa_sessions_session_id ON qa_sessions(session_id);
CREATE INDEX idx_qa_sessions_user_id ON qa_sessions(user_id);
CREATE INDEX idx_qa_sessions_model_id ON qa_sessions(model_id);

-- 注释
COMMENT ON TABLE qa_sessions IS '问答会话表';
```

#### qa_history (问答历史表)
```sql
CREATE TABLE qa_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id),
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    model_id INTEGER REFERENCES models(id),
    confidence FLOAT,
    response_time INTEGER,
    feedback INTEGER CHECK (feedback IN (1, -1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_qa_history_session_id ON qa_history(session_id);
CREATE INDEX idx_qa_history_user_id ON qa_history(user_id);
CREATE INDEX idx_qa_history_model_id ON qa_history(model_id);
CREATE INDEX idx_qa_history_created_at ON qa_history(created_at);

-- 全文搜索索引
CREATE INDEX idx_qa_history_question_fts ON qa_history USING gin(to_tsvector('chinese', question));
CREATE INDEX idx_qa_history_answer_fts ON qa_history USING gin(to_tsvector('chinese', answer));

-- 注释
COMMENT ON TABLE qa_history IS '问答历史表';
COMMENT ON COLUMN qa_history.confidence IS '回答置信度';
COMMENT ON COLUMN qa_history.response_time IS '响应时间(毫秒)';
COMMENT ON COLUMN qa_history.feedback IS '用户反馈：1-好评，-1-差评';
```

### 2.6 系统管理相关表

#### system_configs (系统配置表)
```sql
CREATE TABLE system_configs (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    config_type VARCHAR(20) DEFAULT 'string' CHECK (config_type IN ('string', 'number', 'boolean', 'json')),
    description TEXT,
    is_encrypted BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_system_configs_config_key ON system_configs(config_key);

-- 注释
COMMENT ON TABLE system_configs IS '系统配置表';
```

#### api_logs (API日志表)
```sql
CREATE TABLE api_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    method VARCHAR(10) NOT NULL,
    path VARCHAR(500) NOT NULL,
    query_params TEXT,
    request_body TEXT,
    response_status INTEGER NOT NULL,
    response_time INTEGER NOT NULL,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_api_logs_user_id ON api_logs(user_id);
CREATE INDEX idx_api_logs_path ON api_logs(path);
CREATE INDEX idx_api_logs_response_status ON api_logs(response_status);
CREATE INDEX idx_api_logs_created_at ON api_logs(created_at);

-- 注释
COMMENT ON TABLE api_logs IS 'API访问日志表';
```

## 3. 数据库约束和触发器

### 3.1 数据完整性约束
```sql
-- 确保只有一个活跃模型
CREATE UNIQUE INDEX idx_models_active_unique 
ON models(model_type) 
WHERE is_active = true;

-- 确保训练任务状态转换合理
CREATE OR REPLACE FUNCTION check_training_status_transition()
RETURNS TRIGGER AS $$
BEGIN
    -- 只允许合理的状态转换
    IF OLD.status = 'completed' AND NEW.status != 'completed' THEN
        RAISE EXCEPTION '已完成的训练任务不能更改状态';
    END IF;
    
    -- 更新时间戳
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_training_status_check
    BEFORE UPDATE ON training_tasks
    FOR EACH ROW
    EXECUTE FUNCTION check_training_status_transition();
```

### 3.2 自动更新时间戳
```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为需要的表添加触发器
CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_datasets_updated_at
    BEFORE UPDATE ON datasets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_models_updated_at
    BEFORE UPDATE ON models
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

## 4. 数据库性能优化

### 4.1 分区策略
```sql
-- 按月分区API日志表
CREATE TABLE api_logs_y2026m01 PARTITION OF api_logs
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE api_logs_y2026m02 PARTITION OF api_logs
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

-- 按月分区训练日志表
CREATE TABLE training_logs_y2026m01 PARTITION OF training_logs
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
```

### 4.2 查询优化视图
```sql
-- 活跃模型视图
CREATE VIEW active_models AS
SELECT 
    m.*,
    u.username as created_by_username,
    tt.name as training_task_name
FROM models m
LEFT JOIN users u ON m.created_by = u.id
LEFT JOIN training_tasks tt ON m.training_task_id = tt.id
WHERE m.is_active = true;

-- 训练任务统计视图
CREATE VIEW training_task_stats AS
SELECT 
    DATE(created_at) as date,
    status,
    COUNT(*) as task_count,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))/3600) as avg_duration_hours
FROM training_tasks
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at), status;

-- 用户活跃度统计视图
CREATE VIEW user_activity_stats AS
SELECT 
    u.id,
    u.username,
    COUNT(DISTINCT qh.session_id) as session_count,
    COUNT(qh.id) as question_count,
    MAX(qh.created_at) as last_activity
FROM users u
LEFT JOIN qa_history qh ON u.id = qh.user_id
WHERE qh.created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY u.id, u.username;
```

## 5. 数据备份和恢复策略

### 5.1 备份策略
```sql
-- 创建备份用户
CREATE USER backup_user WITH PASSWORD 'backup_password';
GRANT CONNECT ON DATABASE training_platform TO backup_user;
GRANT USAGE ON SCHEMA public TO backup_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO backup_user;

-- 备份脚本示例
-- pg_dump -h localhost -U backup_user -d training_platform -f backup_$(date +%Y%m%d_%H%M%S).sql
```

### 5.2 数据归档策略
```sql
-- 归档旧的API日志（保留3个月）
DELETE FROM api_logs 
WHERE created_at < CURRENT_DATE - INTERVAL '3 months';

-- 归档旧的训练日志（保留6个月）
DELETE FROM training_logs 
WHERE created_at < CURRENT_DATE - INTERVAL '6 months';
```

## 6. Redis缓存设计

### 6.1 缓存键命名规范
```
user:session:{user_id}:{session_token}  # 用户会话
model:cache:{model_id}                  # 模型缓存
qa:result:{question_hash}               # 问答结果缓存
training:progress:{task_id}             # 训练进度缓存
system:config:{config_key}              # 系统配置缓存
```

### 6.2 缓存策略
```python
# 缓存配置示例
CACHE_CONFIG = {
    'user_session': {'ttl': 3600},      # 1小时
    'model_cache': {'ttl': 86400},      # 24小时
    'qa_result': {'ttl': 1800},         # 30分钟
    'training_progress': {'ttl': 300},   # 5分钟
    'system_config': {'ttl': 3600},     # 1小时
}
```

## 7. 数据库监控

### 7.1 性能监控查询
```sql
-- 慢查询监控
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- 表大小监控
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 索引使用情况
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

---

**文档版本**: v1.0  
**设计日期**: 2026-01-08  
**下一步**: 部署架构设计和开发环境搭建