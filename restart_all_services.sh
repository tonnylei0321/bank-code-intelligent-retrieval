#!/bin/bash

echo "=========================================="
echo "🔄 重启前后端服务"
echo "=========================================="

# 停止后端服务
echo ""
echo "📍 1. 停止后端服务..."
pkill -f "uvicorn" || echo "   后端服务未运行"
sleep 2

# 停止前端服务
echo ""
echo "📍 2. 停止前端服务..."
pkill -f "vite" || echo "   前端服务未运行"
sleep 2

# 启动后端服务
echo ""
echo "🚀 3. 启动后端服务..."
cd mvp
nohup ./venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info > backend.log 2>&1 &
cd ..
sleep 3

# 检查后端状态
if ps aux | grep "uvicorn" | grep -v grep > /dev/null; then
    echo "   ✅ 后端服务启动成功！"
    echo "   📝 访问地址: http://localhost:8000"
    echo "   📋 日志文件: mvp/backend.log"
else
    echo "   ❌ 后端服务启动失败"
    exit 1
fi

# 启动前端服务
echo ""
echo "🚀 4. 启动前端服务..."
cd frontend
nohup npm start > frontend.log 2>&1 &
cd ..
sleep 5

# 检查前端状态
if ps aux | grep "vite" | grep -v grep > /dev/null; then
    echo "   ✅ 前端服务启动成功！"
    echo "   📝 访问地址: http://localhost:3000"
    echo "   📋 日志文件: frontend/frontend.log"
else
    echo "   ❌ 前端服务启动失败"
    echo "   查看日志:"
    tail -20 frontend/frontend.log
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ 所有服务启动完成！"
echo "=========================================="
echo ""
echo "📝 后续步骤:"
echo "1. 访问 http://localhost:3000"
echo "2. 使用 Cmd+Shift+R (Mac) 硬刷新浏览器"
echo "3. 登录系统 (admin/admin123)"
echo "4. 查看「样本管理」菜单是否有子菜单"
echo "5. 点击「大模型提示词管理」测试功能"
echo ""
echo "📋 查看日志:"
echo "   后端: tail -f mvp/backend.log"
echo "   前端: tail -f frontend/frontend.log"
echo ""
