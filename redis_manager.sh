#!/bin/bash

# Redis管理脚本
# 用于启动、停止、重启和管理Redis服务

REDIS_PORT=6379
REDIS_HOST=127.0.0.1
REDIS_CONFIG_FILE="/etc/redis/redis.conf"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查Redis是否已安装
check_redis_installed() {
    if ! command -v redis-server &> /dev/null; then
        print_error "Redis未安装"
        echo "安装命令:"
        echo "  Ubuntu/Debian: sudo apt-get install redis-server"
        echo "  CentOS/RHEL: sudo yum install redis"
        echo "  macOS: brew install redis"
        return 1
    fi
    return 0
}

# 检查Redis是否正在运行
is_redis_running() {
    if pgrep -x "redis-server" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# 检查Redis连接
test_redis_connection() {
    if redis-cli -h $REDIS_HOST -p $REDIS_PORT ping >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 启动Redis服务
start_redis() {
    print_info "启动Redis服务..."
    
    if ! check_redis_installed; then
        return 1
    fi
    
    if is_redis_running; then
        print_warning "Redis服务已在运行"
        if test_redis_connection; then
            print_success "Redis连接正常"
            show_redis_info
        else
            print_error "Redis连接失败"
        fi
        return 0
    fi
    
    # 尝试不同的启动方式
    if command -v systemctl &> /dev/null; then
        # 使用systemd启动
        print_info "尝试使用systemd启动Redis..."
        if sudo systemctl start redis 2>/dev/null || sudo systemctl start redis-server 2>/dev/null; then
            sleep 2
            if test_redis_connection; then
                print_success "Redis通过systemd启动成功"
                show_redis_info
                return 0
            fi
        fi
    fi
    
    if command -v service &> /dev/null; then
        # 使用service命令启动
        print_info "尝试使用service命令启动Redis..."
        if sudo service redis start 2>/dev/null || sudo service redis-server start 2>/dev/null; then
            sleep 2
            if test_redis_connection; then
                print_success "Redis通过service命令启动成功"
                show_redis_info
                return 0
            fi
        fi
    fi
    
    # 直接启动Redis
    print_info "尝试直接启动Redis..."
    if [ -f "$REDIS_CONFIG_FILE" ]; then
        redis-server $REDIS_CONFIG_FILE --daemonize yes 2>/dev/null &
    else
        redis-server --daemonize yes --port $REDIS_PORT --bind $REDIS_HOST 2>/dev/null &
    fi
    
    sleep 3
    
    if test_redis_connection; then
        print_success "Redis直接启动成功"
        show_redis_info
        return 0
    else
        print_error "Redis启动失败"
        return 1
    fi
}

# 停止Redis服务
stop_redis() {
    print_info "停止Redis服务..."
    
    if ! is_redis_running; then
        print_warning "Redis服务未运行"
        return 0
    fi
    
    # 尝试优雅关闭
    if command -v redis-cli &> /dev/null; then
        print_info "尝试优雅关闭Redis..."
        redis-cli -h $REDIS_HOST -p $REDIS_PORT shutdown 2>/dev/null || true
        sleep 2
    fi
    
    # 检查是否还在运行
    if is_redis_running; then
        print_info "强制停止Redis进程..."
        REDIS_PIDS=$(ps aux | grep -E "redis-server" | grep -v grep | awk '{print $2}')
        if [ ! -z "$REDIS_PIDS" ]; then
            kill -9 $REDIS_PIDS 2>/dev/null
            sleep 1
        fi
    fi
    
    # 尝试使用系统服务停止
    if command -v systemctl &> /dev/null; then
        sudo systemctl stop redis 2>/dev/null || sudo systemctl stop redis-server 2>/dev/null || true
    elif command -v service &> /dev/null; then
        sudo service redis stop 2>/dev/null || sudo service redis-server stop 2>/dev/null || true
    fi
    
    if ! is_redis_running; then
        print_success "Redis服务已停止"
        return 0
    else
        print_error "Redis停止失败"
        return 1
    fi
}

# 重启Redis服务
restart_redis() {
    print_info "重启Redis服务..."
    stop_redis
    sleep 2
    start_redis
}

# 显示Redis信息
show_redis_info() {
    if ! test_redis_connection; then
        print_error "无法连接到Redis"
        return 1
    fi
    
    echo ""
    print_info "Redis服务信息:"
    
    # 基本信息
    REDIS_VERSION=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT info server | grep redis_version | cut -d: -f2 | tr -d '\r')
    REDIS_MODE=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT info server | grep redis_mode | cut -d: -f2 | tr -d '\r')
    UPTIME=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT info server | grep uptime_in_seconds | cut -d: -f2 | tr -d '\r')
    
    echo "  版本: $REDIS_VERSION"
    echo "  模式: $REDIS_MODE"
    echo "  运行时间: $UPTIME 秒"
    echo "  地址: $REDIS_HOST:$REDIS_PORT"
    
    # 内存信息
    USED_MEMORY=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT info memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')
    MAX_MEMORY=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT info memory | grep maxmemory_human | cut -d: -f2 | tr -d '\r')
    
    echo "  内存使用: $USED_MEMORY"
    if [ ! -z "$MAX_MEMORY" ] && [ "$MAX_MEMORY" != "0B" ]; then
        echo "  最大内存: $MAX_MEMORY"
    fi
    
    # 数据库信息
    DB_KEYS=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT dbsize)
    echo "  键数量: $DB_KEYS"
    
    # 连接信息
    CONNECTED_CLIENTS=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT info clients | grep connected_clients | cut -d: -f2 | tr -d '\r')
    echo "  连接客户端: $CONNECTED_CLIENTS"
    
    echo ""
}

# 测试Redis性能
test_redis_performance() {
    print_info "测试Redis性能..."
    
    if ! test_redis_connection; then
        print_error "无法连接到Redis"
        return 1
    fi
    
    echo ""
    print_info "执行Redis基准测试..."
    redis-cli -h $REDIS_HOST -p $REDIS_PORT --latency-history -i 1 &
    LATENCY_PID=$!
    
    # 运行5秒后停止
    sleep 5
    kill $LATENCY_PID 2>/dev/null || true
    
    echo ""
    print_info "执行简单的读写测试..."
    
    # 写入测试
    START_TIME=$(date +%s%N)
    for i in {1..1000}; do
        redis-cli -h $REDIS_HOST -p $REDIS_PORT set "test_key_$i" "test_value_$i" >/dev/null
    done
    END_TIME=$(date +%s%N)
    WRITE_TIME=$(( (END_TIME - START_TIME) / 1000000 ))
    
    # 读取测试
    START_TIME=$(date +%s%N)
    for i in {1..1000}; do
        redis-cli -h $REDIS_HOST -p $REDIS_PORT get "test_key_$i" >/dev/null
    done
    END_TIME=$(date +%s%N)
    READ_TIME=$(( (END_TIME - START_TIME) / 1000000 ))
    
    # 清理测试数据
    redis-cli -h $REDIS_HOST -p $REDIS_PORT eval "for i=1,1000 do redis.call('del', 'test_key_' .. i) end" 0 >/dev/null
    
    echo "  写入1000个键用时: ${WRITE_TIME}ms"
    echo "  读取1000个键用时: ${READ_TIME}ms"
    echo ""
}

# 清理Redis数据
clean_redis_data() {
    print_warning "这将清空所有Redis数据！"
    read -p "确定要继续吗？(y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if test_redis_connection; then
            print_info "清空Redis数据..."
            redis-cli -h $REDIS_HOST -p $REDIS_PORT flushall
            print_success "Redis数据已清空"
        else
            print_error "无法连接到Redis"
            return 1
        fi
    else
        print_info "操作已取消"
    fi
}

# 备份Redis数据
backup_redis_data() {
    print_info "备份Redis数据..."
    
    if ! test_redis_connection; then
        print_error "无法连接到Redis"
        return 1
    fi
    
    BACKUP_DIR="./redis_backups"
    mkdir -p "$BACKUP_DIR"
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/redis_backup_$TIMESTAMP.rdb"
    
    # 触发Redis保存
    redis-cli -h $REDIS_HOST -p $REDIS_PORT bgsave
    
    # 等待保存完成
    while [ "$(redis-cli -h $REDIS_HOST -p $REDIS_PORT lastsave)" = "$(redis-cli -h $REDIS_HOST -p $REDIS_PORT lastsave)" ]; do
        sleep 1
    done
    
    # 复制RDB文件
    if [ -f "/var/lib/redis/dump.rdb" ]; then
        cp /var/lib/redis/dump.rdb "$BACKUP_FILE"
        print_success "Redis数据已备份到: $BACKUP_FILE"
    else
        print_error "找不到Redis数据文件"
        return 1
    fi
}

# 显示帮助信息
show_help() {
    echo "Redis管理脚本"
    echo ""
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  start      启动Redis服务"
    echo "  stop       停止Redis服务"
    echo "  restart    重启Redis服务"
    echo "  status     显示Redis状态"
    echo "  info       显示Redis详细信息"
    echo "  test       测试Redis性能"
    echo "  clean      清空Redis数据"
    echo "  backup     备份Redis数据"
    echo "  help       显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 start    # 启动Redis"
    echo "  $0 status   # 查看状态"
    echo "  $0 info     # 查看详细信息"
    echo ""
}

# 显示Redis状态
show_status() {
    print_info "检查Redis状态..."
    
    if ! check_redis_installed; then
        return 1
    fi
    
    if is_redis_running; then
        if test_redis_connection; then
            print_success "Redis服务正在运行且连接正常"
            show_redis_info
        else
            print_warning "Redis进程在运行但连接失败"
        fi
    else
        print_warning "Redis服务未运行"
    fi
}

# 主函数
main() {
    case "${1:-help}" in
        start)
            start_redis
            ;;
        stop)
            stop_redis
            ;;
        restart)
            restart_redis
            ;;
        status)
            show_status
            ;;
        info)
            show_redis_info
            ;;
        test)
            test_redis_performance
            ;;
        clean)
            clean_redis_data
            ;;
        backup)
            backup_redis_data
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "未知命令: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"