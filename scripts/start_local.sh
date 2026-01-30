#!/bin/bash

# 本地开发环境启动脚本（不使用Docker）

set -e

echo "🚀 启动本地开发环境..."

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: Python3未安装"
    exit 1
fi

# 创建必要目录
echo "📁 创建必要目录..."
mkdir -p data/{uploads,models,logs}

# 初始化数据库
echo "🗄️  初始化数据库..."
cd backend
python3 -m app.db.init_db

# 启动后端服务
echo "🚀 启动后端服务..."
echo "后端API将在 http://localhost:8000 运行"
echo "API文档: http://localhost:8000/docs"
echo ""
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000