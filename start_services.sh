#!/bin/bash

echo "=========================================="
echo "  启动前后台服务"
echo "=========================================="
echo ""

# 启动后端服务
echo "🚀 启动后端服务..."
cd mvp
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "✅ 后端服务已启动 (PID: $BACKEND_PID)"
echo "📍 后端地址: http://localhost:8000"
echo "📚 API文档: http://localhost:8000/docs"
echo ""

# 等待后端启动
sleep 3

# 检查后端是否启动成功
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ 后端服务健康检查通过"
else
    echo "⚠️  后端服务可能还在启动中..."
fi
echo ""

# 启动前端服务
echo "🚀 启动前端服务..."
cd ../frontend

# 检查node_modules
if [ ! -d "node_modules" ] || [ ! -f "node_modules/.bin/vite" ]; then
    echo "📦 安装前端依赖..."
    npm install
fi

echo "🌐 启动Vite开发服务器..."
npx vite &
FRONTEND_PID=$!
echo "✅ 前端服务已启动 (PID: $FRONTEND_PID)"
echo "📍 前端地址: http://localhost:5173"
echo ""

echo "=========================================="
echo "  服务启动完成"
echo "=========================================="
echo ""
echo "访问地址："
echo "  - 前端: http://localhost:5173"
echo "  - 后端API: http://localhost:8000"
echo "  - API文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo ""

# 等待用户中断
wait
