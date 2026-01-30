#!/bin/bash

# 快速启动并行训练数据生成
# 使用3个LLM API并行处理15万条银行数据

echo "🚀 银行训练数据并行生成系统"
echo "=================================="
echo "配置信息："
echo "- 阿里通义千问 API"
echo "- 字节豆包 API" 
echo "- DeepSeek API"
echo "- 每个银行生成7个训练样本"
echo "- 预计生成105万条训练数据"
echo "=================================="

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查依赖
echo "📦 检查依赖..."
python3 -c "import aiohttp, asyncio" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  安装缺失的依赖..."
    pip install aiohttp asyncio
fi

# 创建日志目录
mkdir -p logs

# 询问运行模式
echo ""
read -p "选择运行模式 [1]测试模式 [2]生产模式: " mode

case $mode in
    1)
        echo "🧪 启动测试模式..."
        python3 start_parallel_generation.py --test
        ;;
    2)
        echo "🏭 启动生产模式..."
        echo "⚠️  这将处理15万条银行数据，预计需要数小时"
        read -p "确认继续？(y/N): " confirm
        if [[ $confirm == [yY] ]]; then
            # 后台运行生成
            nohup python3 start_parallel_generation.py > logs/generation_$(date +%Y%m%d_%H%M%S).log 2>&1 &
            GENERATION_PID=$!
            echo "✅ 生成进程已启动 (PID: $GENERATION_PID)"
            echo "📝 日志文件: logs/generation_$(date +%Y%m%d_%H%M%S).log"
            
            # 启动监控
            sleep 3
            echo "🔍 启动进度监控..."
            python3 monitor_generation.py
        else
            echo "❌ 已取消"
        fi
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo "✅ 完成"