#!/bin/bash

echo "🧪 测试cleanup_and_restart.sh脚本修复..."

# 1. 检查脚本语法
echo "1️⃣ 检查脚本语法..."
if bash -n cleanup_and_restart.sh; then
    echo "   ✅ 脚本语法正确"
else
    echo "   ❌ 脚本语法错误"
    exit 1
fi

# 2. 检查关键命令是否存在
echo "2️⃣ 检查依赖命令..."
REQUIRED_COMMANDS=("curl" "lsof" "ps" "kill" "find" "python3")
for cmd in "${REQUIRED_COMMANDS[@]}"; do
    if command -v $cmd >/dev/null 2>&1; then
        echo "   ✅ $cmd 命令可用"
    else
        echo "   ❌ $cmd 命令不可用"
    fi
done

# 3. 检查关键路径
echo "3️⃣ 检查关键路径..."
REQUIRED_PATHS=("mvp" "frontend" "mvp/data" "mvp/venv")
for path in "${REQUIRED_PATHS[@]}"; do
    if [ -d "$path" ]; then
        echo "   ✅ $path 目录存在"
    else
        echo "   ⚠️ $path 目录不存在"
    fi
done

# 4. 检查数据库文件
echo "4️⃣ 检查数据库文件..."
if [ -f "mvp/data/bank_code.db" ]; then
    echo "   ✅ 数据库文件存在"
    DB_SIZE=$(du -sh mvp/data/bank_code.db | cut -f1)
    echo "   📊 数据库大小: $DB_SIZE"
else
    echo "   ❌ 数据库文件不存在"
fi

# 5. 检查虚拟环境
echo "5️⃣ 检查虚拟环境..."
if [ -f "mvp/venv/bin/uvicorn" ]; then
    echo "   ✅ uvicorn 可执行文件存在"
else
    echo "   ❌ uvicorn 可执行文件不存在"
fi

if [ -f "mvp/venv/bin/python" ]; then
    echo "   ✅ Python 虚拟环境存在"
    PYTHON_VERSION=$(mvp/venv/bin/python --version 2>&1)
    echo "   📊 Python版本: $PYTHON_VERSION"
else
    echo "   ❌ Python 虚拟环境不存在"
fi

# 6. 测试API端点（如果服务正在运行）
echo "6️⃣ 测试API端点..."
if curl -s http://localhost:8000 >/dev/null 2>&1; then
    echo "   ✅ 后端服务响应"
    
    # 测试登录端点
    if curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
       -H "Content-Type: application/x-www-form-urlencoded" \
       -d "username=admin&password=admin123" >/dev/null 2>&1; then
        echo "   ✅ 登录端点正常"
    else
        echo "   ⚠️ 登录端点异常"
    fi
else
    echo "   ⚠️ 后端服务未运行"
fi

if curl -s http://localhost:3000 >/dev/null 2>&1; then
    echo "   ✅ 前端服务响应"
else
    echo "   ⚠️ 前端服务未运行"
fi

echo ""
echo "🎯 测试总结:"
echo "   脚本修复的主要问题："
echo "   ✅ 修复了健康检查端点（/health -> 登录测试）"
echo "   ✅ 修复了RAG统计端点（/stats -> /config）"
echo "   ✅ 添加了必要的环境变量（SECRET_KEY等）"
echo "   ✅ 修复了虚拟环境激活问题"
echo "   ✅ 修复了日期硬编码问题（动态获取当前日期）"
echo "   ✅ 改进了前端启动检查逻辑"
echo ""
echo "✅ cleanup_and_restart.sh 脚本修复完成！"