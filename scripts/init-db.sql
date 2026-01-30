-- 初始化数据库脚本
-- 创建数据库（如果不存在）
-- CREATE DATABASE training_platform;

-- 连接到数据库
\c training_platform;

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
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

-- 创建用户会话表
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    refresh_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建数据集表
CREATE TABLE IF NOT EXISTS datasets (
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

-- 创建数据记录表
CREATE TABLE IF NOT EXISTS dataset_records (
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

-- 创建训练任务表
CREATE TABLE IF NOT EXISTS training_tasks (
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

-- 创建训练日志表
CREATE TABLE IF NOT EXISTS training_logs (
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

-- 创建模型表
CREATE TABLE IF NOT EXISTS models (
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

-- 创建问答会话表
CREATE TABLE IF NOT EXISTS qa_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id),
    model_id INTEGER REFERENCES models(id),
    title VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建问答历史表
CREATE TABLE IF NOT EXISTS qa_history (
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

-- 创建系统配置表
CREATE TABLE IF NOT EXISTS system_configs (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    config_type VARCHAR(20) DEFAULT 'string' CHECK (config_type IN ('string', 'number', 'boolean', 'json')),
    description TEXT,
    is_encrypted BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建API日志表
CREATE TABLE IF NOT EXISTS api_logs (
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

-- 创建索引
-- 用户表索引
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

-- 用户会话表索引
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_session_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);

-- 数据集表索引
CREATE INDEX IF NOT EXISTS idx_datasets_created_by ON datasets(created_by);
CREATE INDEX IF NOT EXISTS idx_datasets_status ON datasets(status);
CREATE INDEX IF NOT EXISTS idx_datasets_format ON datasets(format);
CREATE INDEX IF NOT EXISTS idx_datasets_created_at ON datasets(created_at);
CREATE INDEX IF NOT EXISTS idx_datasets_file_hash ON datasets(file_hash);

-- 数据记录表索引
CREATE INDEX IF NOT EXISTS idx_dataset_records_dataset_id ON dataset_records(dataset_id);
CREATE INDEX IF NOT EXISTS idx_dataset_records_bank_code ON dataset_records(bank_code);
CREATE INDEX IF NOT EXISTS idx_dataset_records_is_valid ON dataset_records(is_valid);

-- 训练任务表索引
CREATE INDEX IF NOT EXISTS idx_training_tasks_dataset_id ON training_tasks(dataset_id);
CREATE INDEX IF NOT EXISTS idx_training_tasks_status ON training_tasks(status);
CREATE INDEX IF NOT EXISTS idx_training_tasks_created_by ON training_tasks(created_by);
CREATE INDEX IF NOT EXISTS idx_training_tasks_model_type ON training_tasks(model_type);
CREATE INDEX IF NOT EXISTS idx_training_tasks_created_at ON training_tasks(created_at);

-- 训练日志表索引
CREATE INDEX IF NOT EXISTS idx_training_logs_task_id ON training_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_training_logs_epoch_step ON training_logs(task_id, epoch, step);
CREATE INDEX IF NOT EXISTS idx_training_logs_created_at ON training_logs(created_at);

-- 模型表索引
CREATE INDEX IF NOT EXISTS idx_models_training_task_id ON models(training_task_id);
CREATE INDEX IF NOT EXISTS idx_models_status ON models(status);
CREATE INDEX IF NOT EXISTS idx_models_is_active ON models(is_active);
CREATE INDEX IF NOT EXISTS idx_models_model_type ON models(model_type);
CREATE INDEX IF NOT EXISTS idx_models_created_by ON models(created_by);

-- 问答会话表索引
CREATE INDEX IF NOT EXISTS idx_qa_sessions_session_id ON qa_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_qa_sessions_user_id ON qa_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_qa_sessions_model_id ON qa_sessions(model_id);

-- 问答历史表索引
CREATE INDEX IF NOT EXISTS idx_qa_history_session_id ON qa_history(session_id);
CREATE INDEX IF NOT EXISTS idx_qa_history_user_id ON qa_history(user_id);
CREATE INDEX IF NOT EXISTS idx_qa_history_model_id ON qa_history(model_id);
CREATE INDEX IF NOT EXISTS idx_qa_history_created_at ON qa_history(created_at);

-- 系统配置表索引
CREATE INDEX IF NOT EXISTS idx_system_configs_config_key ON system_configs(config_key);

-- API日志表索引
CREATE INDEX IF NOT EXISTS idx_api_logs_user_id ON api_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_api_logs_path ON api_logs(path);
CREATE INDEX IF NOT EXISTS idx_api_logs_response_status ON api_logs(response_status);
CREATE INDEX IF NOT EXISTS idx_api_logs_created_at ON api_logs(created_at);

-- 创建更新时间戳函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为需要的表添加触发器
DROP TRIGGER IF EXISTS trigger_users_updated_at ON users;
CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_datasets_updated_at ON datasets;
CREATE TRIGGER trigger_datasets_updated_at
    BEFORE UPDATE ON datasets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_training_tasks_updated_at ON training_tasks;
CREATE TRIGGER trigger_training_tasks_updated_at
    BEFORE UPDATE ON training_tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_models_updated_at ON models;
CREATE TRIGGER trigger_models_updated_at
    BEFORE UPDATE ON models
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_qa_sessions_updated_at ON qa_sessions;
CREATE TRIGGER trigger_qa_sessions_updated_at
    BEFORE UPDATE ON qa_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_system_configs_updated_at ON system_configs;
CREATE TRIGGER trigger_system_configs_updated_at
    BEFORE UPDATE ON system_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 插入初始系统配置
INSERT INTO system_configs (config_key, config_value, config_type, description) VALUES
('max_concurrent_training', '5', 'number', '最大并发训练任务数'),
('default_batch_size', '16', 'number', '默认批处理大小'),
('default_learning_rate', '2e-4', 'string', '默认学习率'),
('upload_max_size', '104857600', 'number', '文件上传最大大小(字节)'),
('model_accuracy_threshold', '0.999', 'string', '模型准确率阈值')
ON CONFLICT (config_key) DO NOTHING;

-- 创建默认管理员用户（密码: admin123）
-- 注意：这是开发环境的默认密码，生产环境请修改
INSERT INTO users (username, email, password_hash, role) VALUES
('admin', 'admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3L3jzjvG4W', 'admin')
ON CONFLICT (username) DO NOTHING;

COMMIT;