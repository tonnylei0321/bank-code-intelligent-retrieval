# 部署文档

## 目录

- [环境要求](#环境要求)
- [依赖安装](#依赖安装)
- [配置说明](#配置说明)
- [数据库初始化](#数据库初始化)
- [启动和停止](#启动和停止)
- [验证部署](#验证部署)
- [常见问题](#常见问题)
- [生产环境建议](#生产环境建议)

## 环境要求

### 硬件要求

**最低配置**:
- CPU: 4核心
- 内存: 16GB RAM
- 存储: 50GB 可用空间
- 网络: 稳定的互联网连接（用于访问大模型API）

**推荐配置**:
- CPU: 8核心或更多
- 内存: 32GB RAM
- GPU: NVIDIA GPU with 8GB+ VRAM（用于模型训练）
- 存储: 100GB+ SSD
- 网络: 高速互联网连接

### 软件要求

- **操作系统**: 
  - Linux (Ubuntu 20.04+ 推荐)
  - macOS 11+
  - Windows 10+ (WSL2推荐)

- **Python**: 3.9 或更高版本

- **可选组件**:
  - Elasticsearch 8.x (用于基准对比系统)
  - Docker & Docker Compose (用于容器化部署)

## 依赖安装

### 1. 安装Python

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install python3.9 python3.9-venv python3.9-dev
```

#### macOS
```bash
brew install python@3.9
```

#### Windows
从 [Python官网](https://www.python.org/downloads/) 下载并安装Python 3.9+

### 2. 克隆项目

```bash
git clone <repository-url>
cd QWen-Create/mvp
```

### 3. 创建虚拟环境

```bash
python3.9 -m venv .venv
```

### 4. 激活虚拟环境

#### Linux/macOS
```bash
source .venv/bin/activate
```

#### Windows
```bash
.venv\Scripts\activate
```

### 5. 安装Python依赖

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 6. 安装Elasticsearch (可选)

如果需要使用基准对比系统，需要安装Elasticsearch。

#### 使用Docker安装
```bash
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch:8.11.0
```

#### 验证Elasticsearch安装
```bash
curl http://localhost:9200
```

### 7. 下载基座模型

下载Qwen3-0.6B模型到指定目录：

```bash
# 创建模型目录
mkdir -p models/base

# 使用huggingface-cli下载（需要先安装）
pip install huggingface-hub
huggingface-cli download Qwen/Qwen2.5-0.5B-Instruct --local-dir models/base/qwen3-0.6b
```

或者手动从 [Hugging Face](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct) 下载。

## 配置说明

### 1. 创建配置文件

复制示例配置文件：

```bash
cp .env.example .env
```

### 2. 编辑配置文件

使用文本编辑器打开 `.env` 文件并修改以下配置：

```bash
nano .env  # 或使用其他编辑器
```

### 3. 必需配置项

#### 应用设置
```bash
APP_NAME="Bank Code Retrieval System"
APP_VERSION="1.0.0"
DEBUG=False  # 生产环境设置为False
LOG_LEVEL=INFO  # 可选: DEBUG, INFO, WARNING, ERROR
```

#### 数据库配置
```bash
# SQLite数据库路径
DATABASE_URL=sqlite:///./data/bank_code.db
```

#### 安全配置
```bash
# 生成强密钥（重要！）
SECRET_KEY=<生成的随机密钥>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_HOURS=24
```

**生成SECRET_KEY**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### 大模型API配置
```bash
# 阿里通义千问API密钥（必需）
QWEN_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
QWEN_API_URL=https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation
```

获取API密钥：访问 [阿里云DashScope](https://dashscope.console.aliyun.com/)

#### Elasticsearch配置（可选）
```bash
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_INDEX=bank_codes
```

#### 模型路径配置
```bash
BASE_MODEL_PATH=./models/base/qwen3-0.6b
FINETUNED_MODEL_PATH=./models/finetuned
```

#### 训练配置
```bash
MAX_CONCURRENT_TRAINING=1
DEFAULT_BATCH_SIZE=16  # 根据GPU内存调整
DEFAULT_LEARNING_RATE=2e-4
DEFAULT_LORA_R=16
DEFAULT_LORA_ALPHA=32
```

#### API配置
```bash
API_RATE_LIMIT=100  # 每分钟请求次数限制
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]
```

### 4. 配置验证

验证配置文件格式：

```bash
python -c "from app.core.config import settings; print('Configuration loaded successfully')"
```

## 数据库初始化

### 1. 创建数据目录

```bash
mkdir -p data logs models/finetuned reports uploads
```

### 2. 初始化数据库

运行数据库初始化脚本：

```bash
python scripts/init_db.py
```

这将：
- 创建所有必需的数据库表
- 创建默认管理员账号（username: admin, password: admin123）
- 设置数据库索引

### 3. 验证数据库

检查数据库文件是否创建：

```bash
ls -lh data/bank_code.db
```

## 启动和停止

### 开发环境启动

#### 方式1: 使用uvicorn直接启动

```bash
cd mvp
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

参数说明：
- `--host 0.0.0.0`: 监听所有网络接口
- `--port 8000`: 监听端口
- `--reload`: 代码变更时自动重载（仅开发环境）

#### 方式2: 使用启动脚本

```bash
./scripts/start.sh
```

### 生产环境启动

#### 方式1: 使用uvicorn（推荐）

```bash
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info
```

#### 方式2: 使用gunicorn + uvicorn workers

首先安装gunicorn：
```bash
pip install gunicorn
```

启动服务：
```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log \
  --log-level info
```

#### 方式3: 使用systemd服务（Linux）

创建systemd服务文件：

```bash
sudo nano /etc/systemd/system/bank-code-api.service
```

内容：
```ini
[Unit]
Description=Bank Code Retrieval API Service
After=network.target

[Service]
Type=notify
User=<your-username>
Group=<your-group>
WorkingDirectory=/path/to/QWen-Create/mvp
Environment="PATH=/path/to/QWen-Create/mvp/.venv/bin"
ExecStart=/path/to/QWen-Create/mvp/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用并启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable bank-code-api
sudo systemctl start bank-code-api
```

查看服务状态：
```bash
sudo systemctl status bank-code-api
```

### 停止服务

#### 开发环境
按 `Ctrl+C` 停止服务

#### 使用脚本停止
```bash
./scripts/stop.sh
```

#### systemd服务
```bash
sudo systemctl stop bank-code-api
```

### 重启服务

#### systemd服务
```bash
sudo systemctl restart bank-code-api
```

## 验证部署

### 1. 检查服务状态

访问健康检查端点：

```bash
curl http://localhost:8000/health
```

预期响应：
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-01-11T10:00:00"
}
```

### 2. 访问API文档

在浏览器中打开：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 3. 测试登录

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

预期响应：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### 4. 运行测试套件

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_auth_properties.py

# 查看测试覆盖率
pytest --cov=app tests/
```

### 5. 检查日志

```bash
# 查看应用日志
tail -f logs/app_$(date +%Y-%m-%d).log

# 查看错误日志
tail -f logs/error_$(date +%Y-%m-%d).log
```

## 常见问题

### Q1: 启动时提示"ModuleNotFoundError"

**原因**: Python依赖未正确安装

**解决**:
```bash
# 确保虚拟环境已激活
source .venv/bin/activate

# 重新安装依赖
pip install -r requirements.txt
```

### Q2: 数据库连接失败

**原因**: 数据库文件不存在或路径错误

**解决**:
```bash
# 检查数据目录
ls -la data/

# 重新初始化数据库
python scripts/init_db.py
```

### Q3: 大模型API调用失败

**原因**: API密钥未配置或无效

**解决**:
1. 检查 `.env` 文件中的 `QWEN_API_KEY`
2. 验证API密钥是否有效
3. 检查网络连接

### Q4: GPU内存不足

**原因**: 训练批次大小过大

**解决**:
1. 在 `.env` 中减小 `DEFAULT_BATCH_SIZE`
2. 或在训练时指定更小的batch_size

### Q5: 端口已被占用

**错误**: `Address already in use`

**解决**:
```bash
# 查找占用端口的进程
lsof -i :8000

# 杀死进程
kill -9 <PID>

# 或使用其他端口
uvicorn app.main:app --port 8001
```

### Q6: Elasticsearch连接失败

**原因**: Elasticsearch未启动或配置错误

**解决**:
```bash
# 检查Elasticsearch状态
curl http://localhost:9200

# 启动Elasticsearch (Docker)
docker start elasticsearch

# 或禁用基准系统功能
```

### Q7: 权限错误

**错误**: `Permission denied`

**解决**:
```bash
# 修改文件权限
chmod +x scripts/*.sh

# 修改目录权限
chmod -R 755 data/ logs/ models/
```

### Q8: 模型下载失败

**原因**: 网络问题或Hugging Face访问受限

**解决**:
1. 使用镜像站点下载
2. 手动下载模型文件
3. 配置代理

## 生产环境建议

### 1. 安全加固

- **修改默认密码**: 首次登录后立即修改admin密码
- **使用强密钥**: 生成并使用强随机SECRET_KEY
- **启用HTTPS**: 使用Nginx反向代理配置SSL证书
- **限制访问**: 配置防火墙规则，只开放必要端口
- **定期更新**: 及时更新依赖包修复安全漏洞

### 2. 性能优化

- **使用多worker**: 根据CPU核心数配置worker数量
- **启用缓存**: 考虑添加Redis缓存层
- **数据库优化**: 定期清理日志，优化查询
- **负载均衡**: 使用Nginx进行负载均衡
- **GPU加速**: 使用GPU加速模型推理

### 3. 监控和日志

- **日志轮转**: 配置日志轮转避免磁盘占满
```bash
# 安装logrotate
sudo apt install logrotate

# 配置日志轮转
sudo nano /etc/logrotate.d/bank-code-api
```

- **监控指标**: 监控CPU、内存、磁盘使用率
- **告警配置**: 配置异常告警通知
- **日志聚合**: 使用ELK Stack聚合日志

### 4. 备份策略

- **数据库备份**: 每天自动备份数据库
```bash
# 添加到crontab
0 2 * * * cp /path/to/data/bank_code.db /path/to/backup/bank_code_$(date +\%Y\%m\%d).db
```

- **模型备份**: 定期备份训练好的模型
- **配置备份**: 备份 `.env` 配置文件

### 5. 容器化部署

使用Docker Compose部署：

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./models:/app/models
      - ./logs:/app/logs
    environment:
      - DATABASE_URL=sqlite:///./data/bank_code.db
    restart: always

  elasticsearch:
    image: elasticsearch:8.11.0
    ports:
      - "9200:9200"
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    restart: always
```

启动：
```bash
docker-compose up -d
```

### 6. 反向代理配置

使用Nginx作为反向代理：

```nginx
# /etc/nginx/sites-available/bank-code-api
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用配置：
```bash
sudo ln -s /etc/nginx/sites-available/bank-code-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7. 资源限制

使用systemd限制资源使用：

```ini
[Service]
# 限制内存使用
MemoryLimit=16G

# 限制CPU使用
CPUQuota=400%

# 限制文件描述符
LimitNOFILE=65536
```

## 升级和维护

### 升级步骤

1. **备份数据**
```bash
cp data/bank_code.db data/bank_code_backup_$(date +%Y%m%d).db
```

2. **拉取最新代码**
```bash
git pull origin main
```

3. **更新依赖**
```bash
pip install -r requirements.txt --upgrade
```

4. **运行数据库迁移**（如有）
```bash
alembic upgrade head
```

5. **重启服务**
```bash
sudo systemctl restart bank-code-api
```

6. **验证升级**
```bash
curl http://localhost:8000/health
```

### 维护任务

- **每日**: 检查日志，监控系统状态
- **每周**: 清理过期日志，检查磁盘空间
- **每月**: 更新依赖包，备份数据
- **每季度**: 安全审计，性能优化

## 技术支持

如有部署问题，请：
1. 查看日志文件获取详细错误信息
2. 参考本文档的常见问题部分
3. 联系技术支持团队

---

**文档版本**: v1.0  
**更新日期**: 2026-01-11  
**维护者**: 系统开发团队
