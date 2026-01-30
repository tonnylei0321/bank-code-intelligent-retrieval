#!/bin/bash

set -e

echo "🚀 开始部署企业级小模型训练平台..."

# 检查Docker和Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: Docker未安装"
    echo "请先安装Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ 错误: Docker Compose未安装"
    echo "请先安装Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# 检查环境变量文件
if [ ! -f .env ]; then
    echo "📝 生成环境变量文件..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件配置相关参数，然后重新运行部署脚本"
    echo "重要配置项："
    echo "  - Redis密码"
    echo "  - JWT密钥"
    echo "  - 大模型API密钥"
    exit 1
fi

# 创建必要目录
echo "📁 创建必要目录..."
mkdir -p data/{uploads,models,logs}
mkdir -p backend/app
mkdir -p frontend/src

# 设置权限
chmod 755 data
chmod -R 755 data/* 2>/dev/null || true

# 停止现有服务
echo "🛑 停止现有服务..."
docker-compose down 2>/dev/null || true

# 构建镜像
echo "🔨 构建Docker镜像..."
docker-compose build

# 启动Redis服务
echo "🗄️  启动Redis服务..."
docker-compose up -d redis

# 等待Redis启动
echo "⏳ 等待Redis启动..."
sleep 10

# 检查Redis连接
echo "🔍 检查Redis连接..."
max_attempts=30
attempt=1
while [ $attempt -le $max_attempts ]; do
    if docker-compose exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; then
        echo "✅ Redis连接成功"
        break
    fi
    echo "⏳ 等待Redis连接... ($attempt/$max_attempts)"
    sleep 2
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    echo "❌ Redis连接失败"
    exit 1
fi

# 启动所有服务
echo "🚀 启动所有服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 20

# 初始化数据库
echo "🗄️  初始化数据库..."
docker-compose exec -T backend python -m app.db.init_db

# 检查服务状态
echo "📊 检查服务状态..."
docker-compose ps

# 检查后端健康状态
echo "🔍 检查后端服务..."
max_attempts=30
attempt=1
while [ $attempt -le $max_attempts ]; do
    if curl -f http://localhost:8000/health 2>/dev/null; then
        echo "✅ 后端服务启动成功"
        break
    fi
    echo "⏳ 等待后端服务启动... ($attempt/$max_attempts)"
    sleep 2
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    echo "❌ 后端服务启动失败"
    echo "查看日志: docker-compose logs backend"
    exit 1
fi

# 显示部署结果
echo ""
echo "🎉 部署完成！"
echo ""
echo "📋 服务信息："
echo "  前端地址: http://localhost:3000"
echo "  后端API: http://localhost:8000"
echo "  API文档: http://localhost:8000/docs"
echo ""
echo "👤 默认管理员账号："
echo "  用户名: admin"
echo "  密码: admin123"
echo "  ⚠️  请登录后立即修改密码！"
echo ""
echo "💾 数据库信息："
echo "  类型: SQLite"
echo "  位置: ./data/training_platform.db"
echo ""
echo "🔧 常用命令："
echo "  查看日志: docker-compose logs -f [service_name]"
echo "  停止服务: docker-compose down"
echo "  重启服务: docker-compose restart [service_name]"
echo "  进入容器: docker-compose exec [service_name] bash"
echo ""
echo "📚 更多信息请查看 docs/ 目录下的文档"