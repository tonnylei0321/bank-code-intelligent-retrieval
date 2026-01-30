# 部署架构设计

## 1. 部署架构概览

### 1.1 整体部署架构
```
┌─────────────────────────────────────────────────────────────┐
│                        负载均衡层                            │
│                    Nginx Load Balancer                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────┐
│                      应用服务层                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │  Frontend   │ │   Backend   │ │   Backend   │           │
│  │   (React)   │ │  (FastAPI)  │ │  (FastAPI)  │           │
│  │   :3000     │ │    :8000    │ │    :8001    │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────┐
│                      数据服务层                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ PostgreSQL  │ │    Redis    │ │   Celery    │           │
│  │   :5432     │ │    :6379    │ │   Worker    │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────┐
│                      存储服务层                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ 数据文件存储 │ │ 模型文件存储 │ │ 日志文件存储 │           │
│  │   /data     │ │   /models   │ │   /logs     │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 服务组件说明

| 组件 | 作用 | 端口 | 副本数 |
|------|------|------|--------|
| Nginx | 负载均衡、静态文件服务 | 80/443 | 1 |
| Frontend | React前端应用 | 3000 | 1 |
| Backend API | FastAPI后端服务 | 8000-8001 | 2 |
| PostgreSQL | 主数据库 | 5432 | 1 |
| Redis | 缓存和消息队列 | 6379 | 1 |
| Celery Worker | 异步任务处理 | - | 2 |
| Celery Beat | 定时任务调度 | - | 1 |

## 2. Docker容器化部署

### 2.1 项目目录结构
```
training-platform/
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env
├── nginx/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── ssl/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   └── scripts/
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── src/
│   └── public/
├── data/
│   ├── postgres/
│   ├── redis/
│   ├── uploads/
│   ├── models/
│   └── logs/
└── scripts/
    ├── init-db.sql
    ├── backup.sh
    └── deploy.sh
```

### 2.2 Docker Compose配置
```yaml
# docker-compose.yml
version: '3.8'

services:
  # 数据库服务
  postgres:
    image: postgres:14
    container_name: training_postgres
    environment:
      POSTGRES_DB: training_platform
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d training_platform"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Redis缓存服务
  redis:
    image: redis:6-alpine
    container_name: training_redis
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - ./data/redis:/data
    ports:
      - "6379:6379"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  # 后端API服务
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: training_backend
    environment:
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/training_platform
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - ENVIRONMENT=production
    volumes:
      - ./data/uploads:/app/uploads
      - ./data/models:/app/models
      - ./data/logs:/app/logs
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Celery Worker
  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: training_celery_worker
    command: celery -A app.celery worker --loglevel=info --concurrency=2
    environment:
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/training_platform
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./data/uploads:/app/uploads
      - ./data/models:/app/models
      - ./data/logs:/app/logs
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  # Celery Beat调度器
  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: training_celery_beat
    command: celery -A app.celery beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/training_platform
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./data/logs:/app/logs
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  # 前端服务
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: training_frontend
    environment:
      - REACT_APP_API_URL=http://localhost/api
    ports:
      - "3000:3000"
    restart: unless-stopped

  # Nginx负载均衡
  nginx:
    build:
      context: ./nginx
      dockerfile: Dockerfile
    container_name: training_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/ssl:/etc/nginx/ssl
      - ./data/logs/nginx:/var/log/nginx
    depends_on:
      - backend
      - frontend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  upload_data:
  model_data:
  log_data:
```

### 2.3 环境变量配置
```bash
# .env
# 数据库配置
DB_USER=training_user
DB_PASSWORD=secure_password_123
DB_NAME=training_platform

# Redis配置
REDIS_PASSWORD=redis_password_123

# 应用配置
SECRET_KEY=your_secret_key_here
JWT_SECRET_KEY=jwt_secret_key_here
ENVIRONMENT=production

# 大模型API配置
QWEN_API_KEY=your_qwen_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
DOUBAO_API_KEY=your_doubao_api_key

# 文件存储配置
UPLOAD_MAX_SIZE=104857600  # 100MB
MODEL_STORAGE_PATH=/app/models
DATA_STORAGE_PATH=/app/uploads

# 监控配置
LOG_LEVEL=INFO
METRICS_ENABLED=true
```

## 3. Nginx配置

### 3.1 Nginx主配置
```nginx
# nginx/nginx.conf
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" '
                    'rt=$request_time uct="$upstream_connect_time" '
                    'uht="$upstream_header_time" urt="$upstream_response_time"';

    access_log /var/log/nginx/access.log main;

    # 基础配置
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 100M;

    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript 
               application/javascript application/xml+rss 
               application/json application/xml;

    # 后端服务器组
    upstream backend_servers {
        least_conn;
        server backend:8000 max_fails=3 fail_timeout=30s;
        keepalive 32;
    }

    # HTTPS重定向
    server {
        listen 80;
        server_name _;
        return 301 https://$server_name$request_uri;
    }

    # 主服务器配置
    server {
        listen 443 ssl http2;
        server_name localhost;

        # SSL配置
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;

        # 前端静态文件
        location / {
            proxy_pass http://frontend:3000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # API接口代理
        location /api/ {
            proxy_pass http://backend_servers;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # 超时配置
            proxy_connect_timeout 30s;
            proxy_send_timeout 300s;
            proxy_read_timeout 300s;
            
            # 缓冲配置
            proxy_buffering on;
            proxy_buffer_size 4k;
            proxy_buffers 8 4k;
        }

        # WebSocket支持
        location /ws/ {
            proxy_pass http://backend_servers;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # 文件上传
        location /api/v1/data/upload {
            proxy_pass http://backend_servers;
            client_max_body_size 100M;
            proxy_request_buffering off;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # 健康检查
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }
}
```

### 3.2 Nginx Dockerfile
```dockerfile
# nginx/Dockerfile
FROM nginx:alpine

# 复制配置文件
COPY nginx.conf /etc/nginx/nginx.conf

# 创建SSL目录
RUN mkdir -p /etc/nginx/ssl

# 生成自签名证书（生产环境请使用正式证书）
RUN apk add --no-cache openssl && \
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/key.pem \
    -out /etc/nginx/ssl/cert.pem \
    -subj "/C=CN/ST=Beijing/L=Beijing/O=Company/CN=localhost"

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
```

## 4. 后端Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要目录
RUN mkdir -p /app/uploads /app/models /app/logs

# 设置权限
RUN chmod +x /app/scripts/*.sh

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 5. 前端Dockerfile

```dockerfile
# frontend/Dockerfile
# 构建阶段
FROM node:16-alpine AS builder

WORKDIR /app

# 复制package文件
COPY package*.json ./

# 安装依赖
RUN npm ci --only=production

# 复制源代码
COPY . .

# 构建应用
RUN npm run build

# 生产阶段
FROM nginx:alpine

# 复制构建结果
COPY --from=builder /app/build /usr/share/nginx/html

# 复制nginx配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
```

## 6. 部署脚本

### 6.1 部署脚本
```bash
#!/bin/bash
# scripts/deploy.sh

set -e

echo "开始部署企业级小模型训练平台..."

# 检查Docker和Docker Compose
if ! command -v docker &> /dev/null; then
    echo "错误: Docker未安装"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "错误: Docker Compose未安装"
    exit 1
fi

# 创建必要目录
mkdir -p data/{postgres,redis,uploads,models,logs}
mkdir -p nginx/ssl

# 设置权限
chmod 755 data
chmod -R 755 data/*

# 生成环境变量文件（如果不存在）
if [ ! -f .env ]; then
    echo "生成环境变量文件..."
    cp .env.example .env
    echo "请编辑 .env 文件配置相关参数"
    exit 1
fi

# 构建镜像
echo "构建Docker镜像..."
docker-compose build

# 启动服务
echo "启动服务..."
docker-compose up -d

# 等待服务启动
echo "等待服务启动..."
sleep 30

# 检查服务状态
echo "检查服务状态..."
docker-compose ps

# 初始化数据库
echo "初始化数据库..."
docker-compose exec backend python -m app.db.init_db

# 创建管理员用户
echo "创建管理员用户..."
docker-compose exec backend python -m app.scripts.create_admin

echo "部署完成！"
echo "访问地址: https://localhost"
echo "管理员账号: admin"
echo "管理员密码: 请查看日志获取初始密码"
```

### 6.2 备份脚本
```bash
#!/bin/bash
# scripts/backup.sh

set -e

BACKUP_DIR="/backup"
DATE=$(date +%Y%m%d_%H%M%S)

echo "开始备份..."

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据库
echo "备份数据库..."
docker-compose exec -T postgres pg_dump -U training_user training_platform > $BACKUP_DIR/db_backup_$DATE.sql

# 备份文件数据
echo "备份文件数据..."
tar -czf $BACKUP_DIR/files_backup_$DATE.tar.gz data/uploads data/models

# 清理旧备份（保留7天）
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "备份完成: $BACKUP_DIR"
```

## 7. 监控和日志

### 7.1 Prometheus配置
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'training-platform'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
```

### 7.2 日志收集配置
```yaml
# logging/filebeat.yml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /app/logs/*.log
  fields:
    service: training-platform
  fields_under_root: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]

logging.level: info
```

## 8. 生产环境优化

### 8.1 性能优化配置
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  backend:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
    environment:
      - WORKERS=4
      - MAX_CONNECTIONS=100

  postgres:
    environment:
      - POSTGRES_SHARED_BUFFERS=256MB
      - POSTGRES_EFFECTIVE_CACHE_SIZE=1GB
      - POSTGRES_MAX_CONNECTIONS=200

  redis:
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
```

### 8.2 安全加固
```bash
# 防火墙配置
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# 限制Docker容器权限
echo '{"userns-remap": "default"}' > /etc/docker/daemon.json
systemctl restart docker
```

---

**文档版本**: v1.0  
**设计日期**: 2026-01-08  
**下一步**: 开发环境搭建和项目初始化