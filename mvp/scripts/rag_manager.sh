#!/bin/bash

# RAG系统管理脚本
# 用于管理RAG向量数据库的初始化、更新、清理和监控

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    # 检查Python环境
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi
    
    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        log_error "虚拟环境不存在，请先运行: python3 -m venv venv"
        exit 1
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 检查必要的Python包
    python3 -c "import chromadb, sentence_transformers" 2>/dev/null || {
        log_error "RAG依赖包未安装，请运行: pip install chromadb sentence-transformers"
        exit 1
    }
    
    log_success "依赖检查通过"
}

# 获取RAG状态
get_rag_status() {
    log_info "获取RAG系统状态..."
    
    # 检查向量数据库目录
    if [ -d "data/vector_db" ]; then
        VECTOR_DB_SIZE=$(du -sh data/vector_db 2>/dev/null | cut -f1)
        VECTOR_DB_FILES=$(find data/vector_db -type f | wc -l)
        log_info "向量数据库: $VECTOR_DB_SIZE, $VECTOR_DB_FILES 个文件"
        
        # 检查ChromaDB
        if [ -f "data/vector_db/chroma.sqlite3" ]; then
            CHROMA_SIZE=$(du -sh data/vector_db/chroma.sqlite3 2>/dev/null | cut -f1)
            log_info "ChromaDB: $CHROMA_SIZE"
        else
            log_warning "ChromaDB数据库文件不存在"
        fi
    else
        log_warning "向量数据库目录不存在"
    fi
    
    # 检查后端服务状态
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        log_success "后端服务运行正常"
        
        # 获取RAG API状态
        RAG_STATS=$(curl -s http://localhost:8000/api/v1/rag/stats 2>/dev/null)
        if [ $? -eq 0 ] && [ ! -z "$RAG_STATS" ]; then
            log_success "RAG API响应正常"
            echo "RAG统计信息: $RAG_STATS" | head -c 200
            echo ""
        else
            log_warning "RAG API无响应"
        fi
    else
        log_error "后端服务未运行"
    fi
}

# 初始化RAG系统
initialize_rag() {
    local force_rebuild=${1:-false}
    
    log_info "初始化RAG系统 (force_rebuild=$force_rebuild)..."
    
    source venv/bin/activate
    
    # 使用Python脚本初始化
    python3 -c "
import asyncio
import sys
sys.path.append('.')
from app.core.database import SessionLocal
from app.services.rag_service import RAGService

async def init_rag():
    db = SessionLocal()
    try:
        rag_service = RAGService(db)
        success = await rag_service.initialize_vector_db(force_rebuild=$force_rebuild)
        if success:
            print('✅ RAG系统初始化成功')
            
            # 获取统计信息
            stats = rag_service.get_database_stats()
            print(f'📊 向量数据库记录数: {stats.get(\"vector_db_count\", 0)}')
            print(f'📊 源数据库记录数: {stats.get(\"source_db_count\", 0)}')
            print(f'📊 同步状态: {\"已同步\" if stats.get(\"is_synced\", False) else \"需要同步\"}')
        else:
            print('❌ RAG系统初始化失败')
            sys.exit(1)
    finally:
        db.close()

asyncio.run(init_rag())
"
    
    if [ $? -eq 0 ]; then
        log_success "RAG系统初始化完成"
    else
        log_error "RAG系统初始化失败"
        exit 1
    fi
}

# 更新RAG数据库
update_rag() {
    log_info "更新RAG数据库..."
    
    source venv/bin/activate
    
    python3 -c "
import asyncio
import sys
sys.path.append('.')
from app.core.database import SessionLocal
from app.services.rag_service import RAGService

async def update_rag():
    db = SessionLocal()
    try:
        rag_service = RAGService(db)
        success = await rag_service.update_vector_db()
        if success:
            print('✅ RAG数据库更新成功')
        else:
            print('❌ RAG数据库更新失败')
            sys.exit(1)
    finally:
        db.close()

asyncio.run(update_rag())
"
    
    if [ $? -eq 0 ]; then
        log_success "RAG数据库更新完成"
    else
        log_error "RAG数据库更新失败"
        exit 1
    fi
}

# 从文件加载数据
load_from_file() {
    local file_path=${1:-"../data/T_BANK_LINE_NO_ICBC_ALL.unl"}
    local force_rebuild=${2:-false}
    
    log_info "从文件加载数据: $file_path (force_rebuild=$force_rebuild)"
    
    if [ ! -f "$file_path" ]; then
        log_error "文件不存在: $file_path"
        exit 1
    fi
    
    source venv/bin/activate
    
    python3 -c "
import asyncio
import sys
sys.path.append('.')
from app.core.database import SessionLocal
from app.services.rag_service import RAGService

async def load_from_file():
    db = SessionLocal()
    try:
        rag_service = RAGService(db)
        success = await rag_service.load_from_file('$file_path', force_rebuild=$force_rebuild)
        if success:
            print('✅ 文件数据加载成功')
            
            # 获取统计信息
            stats = rag_service.get_database_stats()
            print(f'📊 向量数据库记录数: {stats.get(\"vector_db_count\", 0)}')
        else:
            print('❌ 文件数据加载失败')
            sys.exit(1)
    finally:
        db.close()

asyncio.run(load_from_file())
"
    
    if [ $? -eq 0 ]; then
        log_success "文件数据加载完成"
    else
        log_error "文件数据加载失败"
        exit 1
    fi
}

# 测试RAG检索
test_rag_search() {
    local question=${1:-"工商银行北京分行"}
    
    log_info "测试RAG检索: $question"
    
    source venv/bin/activate
    
    python3 -c "
import asyncio
import sys
sys.path.append('.')
from app.core.database import SessionLocal
from app.services.rag_service import RAGService

async def test_search():
    db = SessionLocal()
    try:
        rag_service = RAGService(db)
        results = await rag_service.retrieve_relevant_banks('$question', top_k=3)
        
        print(f'🔍 检索问题: $question')
        print(f'📊 找到结果: {len(results)} 个')
        print('')
        
        for i, result in enumerate(results, 1):
            print(f'{i}. {result[\"bank_name\"]}')
            print(f'   联行号: {result[\"bank_code\"]}')
            print(f'   相似度: {result.get(\"similarity_score\", 0):.3f}')
            print(f'   方法: {result.get(\"retrieval_method\", \"unknown\")}')
            print('')
            
    finally:
        db.close()

asyncio.run(test_search())
"
    
    if [ $? -eq 0 ]; then
        log_success "RAG检索测试完成"
    else
        log_error "RAG检索测试失败"
        exit 1
    fi
}

# 清理RAG数据
clean_rag() {
    log_warning "这将删除所有RAG向量数据库数据！"
    read -p "确认继续？(y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "清理RAG向量数据库..."
        
        if [ -d "data/vector_db" ]; then
            rm -rf data/vector_db/*
            log_success "RAG向量数据库已清理"
        else
            log_warning "向量数据库目录不存在"
        fi
    else
        log_info "取消清理操作"
    fi
}

# 备份RAG数据
backup_rag() {
    local backup_dir="backups/rag_$(date +%Y%m%d_%H%M%S)"
    
    log_info "备份RAG数据到: $backup_dir"
    
    mkdir -p "$backup_dir"
    
    if [ -d "data/vector_db" ]; then
        cp -r data/vector_db "$backup_dir/"
        log_success "RAG数据备份完成: $backup_dir"
    else
        log_warning "向量数据库目录不存在，无法备份"
    fi
}

# 显示帮助信息
show_help() {
    echo "RAG系统管理脚本"
    echo ""
    echo "用法: $0 [命令] [参数]"
    echo ""
    echo "命令:"
    echo "  status              - 显示RAG系统状态"
    echo "  init [force]        - 初始化RAG系统 (可选: force=true强制重建)"
    echo "  update              - 更新RAG数据库"
    echo "  load [file] [force] - 从文件加载数据 (默认文件: ../data/T_BANK_LINE_NO_ICBC_ALL.unl)"
    echo "  search [question]   - 测试RAG检索 (默认问题: '工商银行北京分行')"
    echo "  clean               - 清理RAG向量数据库"
    echo "  backup              - 备份RAG数据"
    echo "  help                - 显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 status"
    echo "  $0 init"
    echo "  $0 init true"
    echo "  $0 load ../data/bank_data.unl true"
    echo "  $0 search '建设银行上海分行'"
    echo ""
}

# 主函数
main() {
    # 切换到mvp目录
    if [ ! -f "app/main.py" ]; then
        if [ -f "mvp/app/main.py" ]; then
            cd mvp
        else
            log_error "请在项目根目录或mvp目录下运行此脚本"
            exit 1
        fi
    fi
    
    case "${1:-help}" in
        "status")
            check_dependencies
            get_rag_status
            ;;
        "init")
            check_dependencies
            initialize_rag "${2:-false}"
            ;;
        "update")
            check_dependencies
            update_rag
            ;;
        "load")
            check_dependencies
            load_from_file "${2:-../data/T_BANK_LINE_NO_ICBC_ALL.unl}" "${3:-false}"
            ;;
        "search")
            check_dependencies
            test_rag_search "${2:-工商银行北京分行}"
            ;;
        "clean")
            clean_rag
            ;;
        "backup")
            backup_rag
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# 运行主函数
main "$@"