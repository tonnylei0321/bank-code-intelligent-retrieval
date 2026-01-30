#!/bin/bash

echo "🧪 简单功能测试"
echo ""

# 1. 健康检查
echo "1️⃣ 健康检查..."
curl -s http://localhost:8000/health
echo ""

# 2. 检查进程
echo ""
echo "2️⃣ 检查进程..."
ps aux | grep -E "uvicorn.*mvp" | grep -v grep

# 3. 检查最近日志
echo ""
echo "3️⃣ 最近应用日志（最后10行）..."
tail -10 mvp/logs/app_2026-01-21.log

# 4. 检查错误
echo ""
echo "4️⃣ 检查是否有新的 MPS 错误..."
if tail -20 mvp/logs/error_2026-01-21.log 2>/dev/null | grep -q "MPS backend out of memory"; then
    echo "   ❌ 仍有 MPS 内存错误"
else
    echo "   ✅ 无新的 MPS 内存错误"
fi

echo ""
echo "✅ 基本测试完成"
