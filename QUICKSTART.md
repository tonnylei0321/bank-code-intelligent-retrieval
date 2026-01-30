# 快速启动指南

## 前置条件

确保您的系统已安装：
- Docker 20.0+
- Docker Compose 2.0+
- 至少8GB可用内存
- 至少20GB可用磁盘空间

## 快速部署（推荐）

### 1. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，配置以下关键参数：
# - DB_PASSWORD: 数据库密码
# - REDIS_PASSWORD: Redis密码
# - SECRET_KEY: 应用密钥
# - JWT_SECRET_KEY: JWT密钥
# - QWEN_API_KEY: 通义千问API密钥（可选）
```

### 2. 一键部署

```bash
# 赋予执行权限
chmod +x scripts/deploy.sh

# 执行部署脚本
./scripts/deploy.sh
```

部署脚本会自动完成：
- ✅ 检查Docker环境
- ✅ 创建必要目录
- ✅ 构建Docker镜像
- ✅ 启动所有服务
- ✅ 初始化数据库
- ✅ 健康检查

### 3. 访问系统

部署成功后，您可以访问：

- **前端界面**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **ReDoc文档**: http://localhost:8000/redoc

### 4. 登录系统

使用默认管理员账号登录：
- 用户名: `admin`
- 密码: `admin123`

⚠️ **重要**: 首次登录后请立即修改密码！

## 手动部署（开发环境）

### 1. 启动数据库服务

```bash
docker-compose up -d postgres redis
```

### 2. 启动后端服务

```bash
# 进入后端目录
cd backend

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 启动前端服务

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动服务
npm start
```

## 验证部署

### 1. 检查服务状态

```bash
# 查看所有服务状态
docker-compose ps

# 应该看到以下服务运行中：
# - training_postgres
# - training_redis
# - training_backend
# - training_celery_worker
# - training_frontend
```

### 2. 测试后端API

```bash
# 健康检查
curl http://localhost:8000/health

# 应该返回：
# {"status":"healthy","service":"企业级小模型训练平台","version":"1.0.0"}
```

### 3. 测试前端访问

在浏览器中打开 http://localhost:3000，应该看到登录页面。

### 4. 运行API测试脚本

```bash
# 确保后端服务已启动
cd backend
python test_api.py
```

## 常用命令

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
docker-compose logs -f celery-worker
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart backend
docker-compose restart frontend
```

### 停止服务

```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷（谨慎操作）
docker-compose down -v
```

### 进入容器

```bash
# 进入后端容器
docker-compose exec backend bash

# 进入前端容器
docker-compose exec frontend sh

# 进入数据库容器
docker-compose exec postgres psql -U training_user -d training_platform
```

## 功能使用

### 1. 数据管理

1. 登录后进入"数据管理"页面
2. 点击"上传数据"按钮
3. 选择CSV/TXT/Excel文件（格式：银行名称,联行号,清算行行号）
4. 系统自动验证数据格式
5. 验证通过后可预览数据

### 2. 训练管理

1. 进入"训练管理"页面
2. 点击"创建训练任务"
3. 选择数据集和配置参数
4. 启动训练并监控进度
5. 训练完成后自动注册模型

### 3. 模型管理

1. 进入"模型管理"页面
2. 查看所有训练完成的模型
3. 测试模型性能
4. 激活模型用于问答服务

### 4. 智能问答

1. 进入"智能问答"页面
2. 输入问题（如："中国工商银行北京分行的联行号是什么？"）
3. 获取AI回答
4. 查看问答历史

## 故障排除

### 问题1: 端口被占用

```bash
# 检查端口占用
lsof -i :3000  # 前端端口
lsof -i :8000  # 后端端口
lsof -i :5432  # 数据库端口

# 修改端口（编辑docker-compose.yml）
```

### 问题2: 数据库连接失败

```bash
# 检查数据库容器状态
docker-compose ps postgres

# 查看数据库日志
docker-compose logs postgres

# 重启数据库
docker-compose restart postgres
```

### 问题3: 前端无法连接后端

```bash
# 检查后端服务状态
curl http://localhost:8000/health

# 检查网络配置
docker-compose exec frontend cat /etc/hosts

# 重启前端服务
docker-compose restart frontend
```

### 问题4: 内存不足

```bash
# 检查Docker资源限制
docker stats

# 增加Docker内存限制（Docker Desktop设置）
# 或修改docker-compose.yml中的资源限制
```

## 数据备份

### 备份数据库

```bash
# 运行备份脚本
./scripts/backup.sh

# 手动备份
docker-compose exec postgres pg_dump -U training_user training_platform > backup.sql
```

### 恢复数据库

```bash
# 从备份恢复
docker-compose exec -T postgres psql -U training_user training_platform < backup.sql
```

## 性能优化

### 1. 数据库优化

```sql
-- 进入数据库容器
docker-compose exec postgres psql -U training_user training_platform

-- 查看慢查询
SELECT * FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;

-- 分析表
ANALYZE;
```

### 2. 缓存优化

```bash
# 检查Redis状态
docker-compose exec redis redis-cli ping

# 查看Redis信息
docker-compose exec redis redis-cli info
```

## 下一步

- 📖 阅读完整文档: [README.md](README.md)
- 🔧 查看API文档: http://localhost:8000/docs
- 📊 查看系统设计: [docs/design/](docs/design/)
- 🎯 查看需求文档: [docs/requirements/](docs/requirements/)

## 获取帮助

如遇到问题，请：
1. 查看日志: `docker-compose logs -f`
2. 检查文档: [README.md](README.md)
3. 提交Issue: GitHub Issues

---

**祝您使用愉快！** 🎉