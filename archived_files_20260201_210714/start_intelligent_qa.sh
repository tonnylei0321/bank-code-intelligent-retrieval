#!/bin/bash

# 智能问答系统启动脚本（包含Redis支持）

echo "🚀 启动智能问答系统（包含Redis支持）..."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查并启动Redis服务
echo "🔍 检查Redis服务..."
if ! command -v redis-server &> /dev/null; then
    echo "⚠️  Redis未安装，请先安装Redis服务"
    echo "Ubuntu/Debian: sudo apt-get install redis-server"
    echo "CentOS/RHEL: sudo yum install redis"
    echo "macOS: brew install redis"
    echo ""
    echo "或者使用Redis管理脚本: ./redis_manager.sh start"
    exit 1
fi

# 使用Redis管理脚本启动Redis
if [ -f "./redis_manager.sh" ]; then
    echo "🔧 使用Redis管理脚本启动Redis..."
    ./redis_manager.sh start
else
    # 备用Redis启动方法
    if ! pgrep -x "redis-server" > /dev/null; then
        echo "🔄 启动Redis服务..."
        redis-server --daemonize yes --port 6379 --bind 127.0.0.1
        sleep 2
    fi
fi

# 检查Redis连接
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis连接失败"
    echo "请检查Redis服务状态: ./redis_manager.sh status"
    exit 1
fi

echo "✅ Redis服务正常"

# 检查虚拟环境
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  建议使用虚拟环境"
    echo "创建虚拟环境: python3 -m venv venv"
    echo "激活虚拟环境: source venv/bin/activate"
fi

# 安装依赖
echo "📦 检查依赖..."
if [ -f "requirements.txt" ]; then
    pip install -q -r requirements.txt
else
    echo "⚠️ requirements.txt 不存在，跳过依赖安装"
fi

# 检查环境配置
if [ ! -f ".env" ]; then
    echo "⚠️  .env文件不存在，使用默认配置"
    echo "建议复制 .env.intelligent_qa.example 为 .env 并配置"
    
    # 创建基本的.env文件
    cat > .env << EOF
# 基本配置
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=sqlite:///./data/bank_code.db
SECRET_KEY=your-secret-key-here-change-this-in-production
DEBUG=true
LOG_LEVEL=INFO

# 智能问答配置
QA_DEFAULT_RETRIEVAL_STRATEGY=intelligent
QA_ENABLE_HISTORY=true
QA_CACHE_ANSWERS=true

# 如果有API密钥，请取消注释并填入
# OPENAI_API_KEY=your_openai_api_key_here
# ANTHROPIC_API_KEY=your_anthropic_api_key_here
EOF
    echo "✅ 创建了基本的.env配置文件"
fi

# 运行简单测试
echo "🧪 运行基础测试..."
if [ -f "test_intelligent_qa_simple.py" ]; then
    python test_intelligent_qa_simple.py
else
    echo "⚠️ 测试文件不存在，跳过基础测试"
fi

if [ $? -eq 0 ]; then
    echo "✅ 基础测试通过"
else
    echo "❌ 基础测试失败，请检查配置"
    echo "可以使用以下命令检查Redis状态:"
    echo "  ./redis_manager.sh status"
    echo "  ./redis_manager.sh info"
    exit 1
fi

# 初始化系统（可选）
read -p "是否初始化智能问答系统？(y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔧 初始化智能问答系统..."
    if [ -f "scripts/init_intelligent_qa.py" ]; then
        python scripts/init_intelligent_qa.py
    else
        echo "⚠️ 初始化脚本不存在，跳过初始化"
    fi
    
    if [ $? -eq 0 ]; then
        echo "✅ 智能问答系统初始化成功"
    else
        echo "⚠️ 初始化过程中出现警告，但系统仍可使用"
    fi
fi

# 启动Web服务
echo "🌐 启动Web服务..."
echo "访问地址:"
echo "  主页: http://localhost:8000"
echo "  API文档: http://localhost:8000/docs"
echo "  智能问答: http://localhost:8000/intelligent-qa"
echo "  Redis管理: http://localhost:8000/redis (管理员)"
echo ""
echo "Redis管理命令:"
echo "  查看状态: ./redis_manager.sh status"
echo "  查看信息: ./redis_manager.sh info"
echo "  性能测试: ./redis_manager.sh test"
echo ""
echo "按 Ctrl+C 停止服务"

# 设置环境变量
export REDIS_URL=redis://localhost:6379/0

python app/main.py