#!/bin/bash

echo "🚀 启动 MVP 后端服务..."

# 停止现有服务
pkill -9 -f "uvicorn" 2>/dev/null
sleep 2

# 进入 mvp 目录并启动
cd mvp

# 设置环境变量
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.7
export PYTORCH_MPS_LOW_WATERMARK_RATIO=0.5
export SECRET_KEY=your-secret-key-here-change-this-in-production
export DATABASE_URL=sqlite:///./data/bank_code.db

# 启动服务
nohup ./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &

echo "✅ 后端已启动"
sleep 3

# 测试
echo "测试登录端点..."
curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=test123" | head -100

echo ""
echo "✅ 后端服务已启动: http://localhost:8000"
echo "📖 API 文档: http://localhost:8000/docs"
