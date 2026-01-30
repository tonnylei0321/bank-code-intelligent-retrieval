#!/bin/bash

# MPS 内存溢出修复脚本

echo "🔧 修复 MPS 内存溢出问题..."

# 1. 停止所有相关进程
echo "1️⃣ 停止所有服务..."
pkill -f "uvicorn.*mvp"
pkill -f "python.*mvp"
sleep 2

# 2. 清理 Python 缓存
echo "2️⃣ 清理 Python 缓存..."
find mvp -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find mvp -type f -name "*.pyc" -delete 2>/dev/null || true

# 3. 设置环境变量（降低 MPS 内存使用）
echo "3️⃣ 配置 MPS 内存限制..."
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.7
export PYTORCH_MPS_LOW_WATERMARK_RATIO=0.5

# 4. 重启服务
echo "4️⃣ 重启后端服务..."
cd mvp
source venv/bin/activate

# 使用更保守的内存设置启动
PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.7 \
PYTORCH_MPS_LOW_WATERMARK_RATIO=0.5 \
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > backend.log 2>&1 &

echo "✅ 服务已重启，使用更保守的内存设置"
echo ""
echo "📊 监控命令："
echo "   tail -f mvp/backend.log"
echo "   tail -f mvp/logs/error_2026-01-21.log"
echo ""
echo "💡 如果仍然出现内存问题，请考虑："
echo "   1. 减少批处理大小"
echo "   2. 使用更小的模型"
echo "   3. 限制并发查询数量"
