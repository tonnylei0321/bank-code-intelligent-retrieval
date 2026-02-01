#!/bin/bash

echo "🔄 重启后端服务..."

# 查找并停止现有的uvicorn进程
echo "停止现有服务..."
pkill -f "uvicorn app.main:app" || echo "没有运行中的服务"

# 等待进程完全停止
sleep 2

# 启动新的服务
echo "启动新服务..."
cd mvp
source venv/bin/activate
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > backend.log 2>&1 &

# 等待服务启动
sleep 3

# 检查服务状态
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    echo "✅ 后端服务已成功启动"
    echo "📝 日志文件: mvp/backend.log"
    echo "🌐 服务地址: http://localhost:8000"
else
    echo "❌ 后端服务启动失败"
    echo "请查看日志: tail -f mvp/backend.log"
    exit 1
fi
