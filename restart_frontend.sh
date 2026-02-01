#!/bin/bash

echo "🔄 重启前端服务..."

# 停止前端服务
echo "📍 停止前端服务..."
pkill -f "vite" || echo "前端服务未运行"

# 等待进程完全停止
sleep 2

# 启动前端服务
echo "🚀 启动前端服务..."
cd frontend
nohup npm start > frontend.log 2>&1 &

# 等待服务启动
sleep 3

# 检查服务状态
if ps aux | grep "vite" | grep -v grep > /dev/null; then
    echo "✅ 前端服务启动成功！"
    echo "📝 访问地址: http://localhost:3000"
    echo "📋 日志文件: frontend/frontend.log"
else
    echo "❌ 前端服务启动失败，请检查日志"
    tail -20 frontend/frontend.log
fi
