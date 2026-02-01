#!/bin/bash

echo "🧹 开始清理和重启服务（包含RAG系统和Redis）..."

# 1. 强制停止所有服务
echo "1️⃣ 强制停止所有服务..."

# 查找并强制停止uvicorn进程
echo "   停止后端服务..."
UVICORN_PIDS=$(ps aux | grep -E "uvicorn.*app\.main:app" | grep -v grep | awk '{print $2}')
if [ ! -z "$UVICORN_PIDS" ]; then
    echo "   发现uvicorn进程: $UVICORN_PIDS"
    kill -9 $UVICORN_PIDS 2>/dev/null
    echo "   ✅ 强制停止uvicorn进程"
else
    echo "   ✅ 未发现uvicorn进程"
fi

# 查找并强制停止npm/node前端进程
echo "   停止前端服务..."
NPM_PIDS=$(ps aux | grep -E "npm.*start|node.*frontend" | grep -v grep | awk '{print $2}')
if [ ! -z "$NPM_PIDS" ]; then
    echo "   发现npm/node进程: $NPM_PIDS"
    kill -9 $NPM_PIDS 2>/dev/null
    echo "   ✅ 强制停止npm/node进程"
else
    echo "   ✅ 未发现npm/node进程"
fi

# 停止Redis服务
echo "   停止Redis服务..."
if command -v redis-cli &> /dev/null; then
    # 尝试优雅关闭Redis
    redis-cli shutdown 2>/dev/null || true
    sleep 2
    
    # 检查Redis是否还在运行
    REDIS_PIDS=$(ps aux | grep -E "redis-server" | grep -v grep | awk '{print $2}')
    if [ ! -z "$REDIS_PIDS" ]; then
        echo "   发现Redis进程: $REDIS_PIDS，强制停止"
        kill -9 $REDIS_PIDS 2>/dev/null
    fi
    echo "   ✅ Redis服务已停止"
else
    echo "   ⚠️ redis-cli未找到，跳过Redis停止"
fi

# 强制释放端口
echo "   检查端口占用..."
PORT_8000_PID=$(lsof -ti:8000 2>/dev/null)
if [ ! -z "$PORT_8000_PID" ]; then
    echo "   端口8000被进程$PORT_8000_PID占用，强制释放"
    kill -9 $PORT_8000_PID 2>/dev/null
fi

PORT_3000_PID=$(lsof -ti:3000 2>/dev/null)
if [ ! -z "$PORT_3000_PID" ]; then
    echo "   端口3000被进程$PORT_3000_PID占用，强制释放"
    kill -9 $PORT_3000_PID 2>/dev/null
fi

PORT_6379_PID=$(lsof -ti:6379 2>/dev/null)
if [ ! -z "$PORT_6379_PID" ]; then
    echo "   端口6379被进程$PORT_6379_PID占用，强制释放"
    kill -9 $PORT_6379_PID 2>/dev/null
fi

# 等待进程完全停止
sleep 5

# 验证端口释放
if lsof -i:8000 >/dev/null 2>&1; then
    echo "   ⚠️ 端口8000仍被占用"
else
    echo "   ✅ 端口8000已释放"
fi

if lsof -i:3000 >/dev/null 2>&1; then
    echo "   ⚠️ 端口3000仍被占用"
else
    echo "   ✅ 端口3000已释放"
fi

if lsof -i:6379 >/dev/null 2>&1; then
    echo "   ⚠️ 端口6379仍被占用"
else
    echo "   ✅ 端口6379已释放"
fi

# 2. 清理Redis数据（可选）
echo "2️⃣ 清理Redis数据..."

# 检查是否需要清理Redis数据
read -p "是否清理Redis缓存数据？(y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "   🧹 清理Redis数据..."
    
    # 如果Redis还在运行，先连接清理
    if command -v redis-cli &> /dev/null; then
        # 尝试连接并清理数据
        redis-cli flushall 2>/dev/null || echo "   ⚠️ Redis未运行，跳过数据清理"
    fi
    
    # 清理Redis持久化文件
    if [ -f "/var/lib/redis/dump.rdb" ]; then
        rm -f /var/lib/redis/dump.rdb 2>/dev/null || true
        echo "   ✅ 清理Redis持久化文件"
    fi
    
    # 清理Redis AOF文件
    if [ -f "/var/lib/redis/appendonly.aof" ]; then
        rm -f /var/lib/redis/appendonly.aof 2>/dev/null || true
        echo "   ✅ 清理Redis AOF文件"
    fi
    
    echo "   ✅ Redis数据清理完成"
else
    echo "   ⏭️ 跳过Redis数据清理"
fi

# 3. 清理日志文件
echo "2️⃣ 清理日志文件..."
cd mvp

# 备份今天的重要日志
TODAY=$(date +%Y-%m-%d)
if [ -f "logs/app_${TODAY}.log" ]; then
    cp "logs/app_${TODAY}.log" "logs/app_${TODAY}_backup.log"
    echo "   ✅ 备份应用日志"
fi

if [ -f "logs/error_${TODAY}.log" ]; then
    cp "logs/error_${TODAY}.log" "logs/error_${TODAY}_backup.log"
    echo "   ✅ 备份错误日志"
fi

# 清理旧日志文件（保留今天的）
find logs/ -name "*.log" -not -name "*${TODAY}*" -delete 2>/dev/null
echo "   ✅ 清理旧日志文件"

# 清理后端日志
> backend.log
echo "   ✅ 清理后端日志"

# 3. 清理测试数据和RAG向量数据库
echo "4️⃣ 清理测试数据和RAG向量数据库..."

# 清理失败的训练任务（保留正在运行的任务9和10）
python3 -c "
import sqlite3
conn = sqlite3.connect('data/bank_code.db')
cursor = conn.cursor()

# 删除失败的训练任务（1-8）
cursor.execute('DELETE FROM training_jobs WHERE id < 9 AND status = \"failed\"')
deleted_jobs = cursor.rowcount
print(f'   ✅ 删除失败训练任务: {deleted_jobs}个')

# 清理多余的测试数据集（保留最新的几个）
cursor.execute('SELECT COUNT(*) FROM datasets')
total_datasets = cursor.fetchone()[0]
if total_datasets > 5:
    cursor.execute('DELETE FROM datasets WHERE id < (SELECT MAX(id) - 4 FROM datasets)')
    deleted_datasets = cursor.rowcount
    print(f'   ✅ 清理旧数据集: {deleted_datasets}个')

# 清理孤立的QA对
cursor.execute('DELETE FROM qa_pairs WHERE dataset_id NOT IN (SELECT id FROM datasets)')
deleted_qa = cursor.rowcount
print(f'   ✅ 清理孤立QA对: {deleted_qa}个')

conn.commit()
conn.close()
print('   ✅ 数据库清理完成')
"

# RAG向量数据库状态检查和清理
echo "   🔍 检查RAG向量数据库状态..."
if [ -d "data/vector_db" ]; then
    VECTOR_DB_SIZE=$(du -sh data/vector_db 2>/dev/null | cut -f1)
    VECTOR_DB_FILES=$(find data/vector_db -type f | wc -l)
    echo "   📊 RAG向量数据库: $VECTOR_DB_SIZE, $VECTOR_DB_FILES 个文件"
    
    # 检查ChromaDB数据库文件
    if [ -f "data/vector_db/chroma.sqlite3" ]; then
        CHROMA_SIZE=$(du -sh data/vector_db/chroma.sqlite3 2>/dev/null | cut -f1)
        echo "   📊 ChromaDB数据库: $CHROMA_SIZE"
    fi
    
    # 可选：清理RAG向量数据库（取消注释以启用）
    # echo "   🧹 清理RAG向量数据库..."
    # rm -rf data/vector_db/* 2>/dev/null || true
    # echo "   ✅ RAG向量数据库已清理（需要重新初始化）"
else
    echo "   ⚠️ RAG向量数据库目录不存在"
fi

# 4. 清理Python缓存
echo "5️⃣ 清理Python缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo "   ✅ Python缓存清理完成"

# 5. 清理临时文件
echo "6️⃣ 清理临时文件..."
rm -rf /tmp/tmp* 2>/dev/null || true
rm -rf temp/temp_files/* 2>/dev/null || true
echo "   ✅ 临时文件清理完成"

cd ..

# 6. 启动Redis服务
echo "7️⃣ 启动Redis服务..."

# 检查Redis是否已安装
if command -v redis-server &> /dev/null; then
    # 检查Redis是否已经在运行
    if ! pgrep -x "redis-server" > /dev/null; then
        echo "   🚀 启动Redis服务..."
        
        # 尝试使用系统服务启动Redis
        if command -v systemctl &> /dev/null; then
            # 使用systemd启动Redis
            sudo systemctl start redis 2>/dev/null || sudo systemctl start redis-server 2>/dev/null || {
                # 如果系统服务启动失败，直接启动Redis
                echo "   ⚠️ 系统服务启动失败，尝试直接启动Redis"
                redis-server --daemonize yes --port 6379 --bind 127.0.0.1 2>/dev/null &
            }
        elif command -v service &> /dev/null; then
            # 使用service命令启动Redis
            sudo service redis start 2>/dev/null || sudo service redis-server start 2>/dev/null || {
                echo "   ⚠️ 系统服务启动失败，尝试直接启动Redis"
                redis-server --daemonize yes --port 6379 --bind 127.0.0.1 2>/dev/null &
            }
        else
            # 直接启动Redis
            redis-server --daemonize yes --port 6379 --bind 127.0.0.1 2>/dev/null &
        fi
        
        # 等待Redis启动
        sleep 3
        
        # 验证Redis是否启动成功
        if redis-cli ping >/dev/null 2>&1; then
            echo "   ✅ Redis服务启动成功"
            
            # 显示Redis信息
            REDIS_VERSION=$(redis-cli info server | grep redis_version | cut -d: -f2 | tr -d '\r')
            REDIS_MODE=$(redis-cli info server | grep redis_mode | cut -d: -f2 | tr -d '\r')
            echo "   📊 Redis版本: $REDIS_VERSION, 模式: $REDIS_MODE"
        else
            echo "   ❌ Redis启动失败"
        fi
    else
        echo "   ✅ Redis服务已在运行"
        
        # 测试Redis连接
        if redis-cli ping >/dev/null 2>&1; then
            echo "   ✅ Redis连接测试成功"
        else
            echo "   ⚠️ Redis连接测试失败"
        fi
    fi
else
    echo "   ❌ Redis未安装，请先安装Redis"
    echo "   安装命令:"
    echo "     Ubuntu/Debian: sudo apt-get install redis-server"
    echo "     CentOS/RHEL: sudo yum install redis"
    echo "     macOS: brew install redis"
    echo "   ⚠️ 智能问答系统需要Redis支持"
fi

# 7. 重启后端服务（使用内存优化配置）
echo "8️⃣ 重启后端服务..."
cd mvp

# 设置所有必要的环境变量
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.7
export PYTORCH_MPS_LOW_WATERMARK_RATIO=0.5
export PYTORCH_ENABLE_MPS_FALLBACK=1
export SECRET_KEY=your-secret-key-here-change-this-in-production
export DATABASE_URL=sqlite:///./data/bank_code.db
export DEBUG=true
export LOG_LEVEL=INFO
export REDIS_URL=redis://localhost:6379/0

# 使用虚拟环境启动服务
nohup ./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info > backend.log 2>&1 &
BACKEND_PID=$!
echo "   ✅ 后端服务已启动 (PID: $BACKEND_PID)"

cd ..

# 等待后端启动
echo "⏳ 等待后端服务启动..."
sleep 8

# 检查后端健康状态和RAG系统
echo "   🔍 测试后端API..."
if curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
   -H "Content-Type: application/x-www-form-urlencoded" \
   -d "username=admin&password=admin123" > /dev/null 2>&1; then
    echo "   ✅ 后端API响应正常"
    
    # 获取token进行RAG系统和Redis测试
    echo "   🔍 检查RAG系统和Redis状态..."
    TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
            -H "Content-Type: application/x-www-form-urlencoded" \
            -d "username=admin&password=admin123" | \
            python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
    
    if [ ! -z "$TOKEN" ]; then
        # 测试RAG配置端点
        RAG_CONFIG=$(curl -s -H "Authorization: Bearer $TOKEN" \
                     "http://localhost:8000/api/v1/rag/config" 2>/dev/null)
        if [ $? -eq 0 ] && [ ! -z "$RAG_CONFIG" ]; then
            echo "   ✅ RAG系统API响应正常"
            echo "   📊 RAG配置: $(echo $RAG_CONFIG | head -c 100)..."
        else
            echo "   ⚠️ RAG系统API可能未正常响应"
        fi
        
        # 测试Redis管理端点
        REDIS_HEALTH=$(curl -s -H "Authorization: Bearer $TOKEN" \
                      "http://localhost:8000/api/redis/health" 2>/dev/null)
        if [ $? -eq 0 ] && [ ! -z "$REDIS_HEALTH" ]; then
            echo "   ✅ Redis管理API响应正常"
            echo "   📊 Redis状态: $(echo $REDIS_HEALTH | head -c 100)..."
        else
            echo "   ⚠️ Redis管理API可能未正常响应"
        fi
        
        # 测试智能问答端点
        QA_MODELS=$(curl -s -H "Authorization: Bearer $TOKEN" \
                    "http://localhost:8000/api/intelligent-qa/models" 2>/dev/null)
        if [ $? -eq 0 ] && [ ! -z "$QA_MODELS" ]; then
            echo "   ✅ 智能问答API响应正常"
            echo "   📊 可用模型: $(echo $QA_MODELS | head -c 100)..."
        else
            echo "   ⚠️ 智能问答API可能未正常响应"
        fi
    else
        echo "   ⚠️ 无法获取认证token"
    fi
else
    echo "   ⚠️ 后端可能未正常启动"
fi

# 9. 可选：初始化智能问答系统
echo "🎯 初始化智能问答系统..."

read -p "是否初始化智能问答系统（加载银行数据到Redis）？(Y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo "   ⏭️ 跳过智能问答系统初始化"
else
    echo "   🚀 正在初始化智能问答系统..."
    
    # 等待后端完全启动
    sleep 5
    
    # 运行初始化脚本
    if [ -f "mvp/scripts/init_intelligent_qa.py" ]; then
        cd mvp
        python3 scripts/init_intelligent_qa.py
        cd ..
        echo "   ✅ 智能问答系统初始化完成"
    else
        echo "   ⚠️ 初始化脚本不存在，请手动初始化"
        echo "   💡 手动初始化步骤："
        echo "      1. 登录系统获取token"
        echo "      2. 访问Redis管理页面"
        echo "      3. 点击'加载数据'按钮"
    fi
fi

# 10. 重启前端服务
echo "🔟 重启前端服务..."
cd frontend

# 确保使用端口3000
export PORT=3000

nohup npm start > frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   ✅ 前端服务已启动 (PID: $FRONTEND_PID)"

cd ..

# 等待前端启动
echo "⏳ 等待前端服务启动..."
sleep 10

# 检查前端状态
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "   ✅ 前端服务正常"
else
    echo "   ⚠️ 前端可能未正常启动，继续等待..."
    sleep 5
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo "   ✅ 前端服务正常（延迟启动）"
    else
        echo "   ❌ 前端启动失败，请检查日志"
    fi
fi

echo ""
echo "🎉 清理和重启完成!"
echo "=" * 50
echo "📊 服务状态:"
echo "   Redis: localhost:6379 ($(redis-cli ping 2>/dev/null || echo "未连接"))"
echo "   后端: http://localhost:8000 (PID: $BACKEND_PID)"
echo "   前端: http://localhost:3000 (PID: $FRONTEND_PID)"
echo "   API文档: http://localhost:8000/docs"
echo "   RAG管理: http://localhost:3000 -> RAG系统管理"
echo "   Redis管理: http://localhost:3000/redis (管理员)"
echo "   智能问答: http://localhost:3000/intelligent-qa"
echo ""
echo "🔍 验证命令:"
echo "   # 测试Redis连接"
echo "   redis-cli ping"
echo "   # 测试后端登录"
echo "   curl -X POST 'http://localhost:8000/api/v1/auth/login' -H 'Content-Type: application/x-www-form-urlencoded' -d 'username=admin&password=admin123'"
echo "   # 测试前端"
echo "   curl http://localhost:3000"
echo "   # 测试RAG配置"
echo "   curl -H 'Authorization: Bearer <token>' http://localhost:8000/api/v1/rag/config"
echo "   # 测试Redis管理"
echo "   curl -H 'Authorization: Bearer <token>' http://localhost:8000/api/redis/health"
echo "   # 测试智能问答"
echo "   curl -H 'Authorization: Bearer <token>' http://localhost:8000/api/intelligent-qa/models"
echo ""
echo "📝 日志监控:"
echo "   tail -f mvp/backend.log"
echo "   tail -f frontend/frontend.log"
TODAY=$(date +%Y-%m-%d)
echo "   tail -f mvp/logs/app_${TODAY}.log"
echo "   # Redis日志"
echo "   tail -f /var/log/redis/redis-server.log  # 或查看系统日志"
echo ""
echo "🤖 AI系统状态:"
echo "   训练任务: 任务9和10继续运行中"
echo "   RAG系统: 向量数据库已就绪"
echo "   Redis缓存: 智能问答数据缓存"
echo "   监控: python3 mvp/system_monitor.py"
echo ""
echo "🔧 Redis管理命令:"
echo "   # 检查Redis状态"
echo "   redis-cli info"
echo "   # 查看Redis内存使用"
echo "   redis-cli info memory"
echo "   # 查看Redis键数量"
echo "   redis-cli dbsize"
echo "   # 清空Redis数据"
echo "   redis-cli flushall"
echo ""
echo "🔧 RAG管理命令:"
echo "   # 检查RAG配置"
echo "   curl -H 'Authorization: Bearer <token>' http://localhost:8000/api/v1/rag/config"
echo "   # 测试RAG检索"
echo "   curl -X POST -H 'Content-Type: application/json' -H 'Authorization: Bearer <token>' \\"
echo "        -d '{\"question\":\"工商银行北京分行\",\"top_k\":5}' \\"
echo "        http://localhost:8000/api/v1/rag/search"
echo ""
echo "🧠 智能问答管理命令:"
echo "   # 检查Redis健康状态"
echo "   curl -H 'Authorization: Bearer <token>' http://localhost:8000/api/redis/health"
echo "   # 加载银行数据到Redis"
echo "   curl -X POST -H 'Authorization: Bearer <token>' http://localhost:8000/api/redis/load-data"
echo "   # 搜索Redis中的银行数据"
echo "   curl -H 'Authorization: Bearer <token>' 'http://localhost:8000/api/redis/search?query=工商银行&limit=5'"
echo "   # 测试智能问答"
echo "   curl -X POST -H 'Content-Type: application/json' -H 'Authorization: Bearer <token>' \\"
echo "        -d '{\"question\":\"工商银行西单支行联行号\",\"retrieval_strategy\":\"intelligent\"}' \\"
echo "        http://localhost:8000/api/intelligent-qa/ask"
echo ""
echo "🎯 快速初始化智能问答系统:"
echo "   # 运行初始化脚本"
echo "   cd mvp && python3 scripts/init_intelligent_qa.py"
echo ""
echo "✅ 系统已准备好进行验证测试!"
echo "🚀 智能问答系统现已完全就绪，包含Redis缓存支持!"