#!/bin/bash

echo "🚀 启动后端服务..."
echo "📍 工作目录: mvp/"
echo "🌐 后端API: http://localhost:8000"
echo "📚 API文档: http://localhost:8000/docs"
echo ""

cd mvp
source venv/bin/activate
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
