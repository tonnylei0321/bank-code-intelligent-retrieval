#!/bin/bash

# 使用内存限制启动服务

echo "🚀 启动服务（内存优化模式）..."

# 停止现有服务
echo "停止现有服务..."
pkill -f "uvicorn.*mvp" 2>/dev/null
pkill -f "python.*mvp" 2>/dev/null
sleep 2

# 清理缓存
echo "清理缓存..."
find mvp -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# 设置环境变量
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.7
export PYTORCH_MPS_LOW_WATERMARK_RATIO=0.5
export PYTORCH_ENABLE_MPS_FALLBACK=1

# 启动后端
echo "启动后端服务..."
cd mvp
source venv/bin/activate

nohup uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --log-level info > backend.log 2>&1 &

BACKEND_PID=$!
echo "✅ 后端已启动 (PID: $BACKEND_PID)"

# 等待后端启动
echo "等待后端启动..."
sleep 5

# 检查后端状态
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ 后端健康检查通过"
else
    echo "⚠️  后端可能未正常启动，请检查日志"
fi

cd ..

echo ""
echo "📊 服务状态："
echo "   后端: http://localhost:8000"
echo "   API文档: http://localhost:8000/docs"
echo ""
echo "📝 日志文件："
echo "   后端日志: mvp/backend.log"
echo "   应用日志: mvp/logs/app_$(date +%Y-%m-%d).log"
echo "   错误日志: mvp/logs/error_$(date +%Y-%m-%d).log"
echo ""
echo "🔍 监控命令："
echo "   tail -f mvp/backend.log"
echo "   tail -f mvp/logs/error_$(date +%Y-%m-%d).log"
echo ""
echo "💡 内存优化设置："
echo "   PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.7"
echo "   PYTORCH_MPS_LOW_WATERMARK_RATIO=0.5"
