#!/bin/bash

# 项目清理脚本
# 删除临时文件、测试数据库、日志文件等无用文件
# 使用方法: bash CLEANUP_SCRIPT.sh

set -e

echo "=========================================="
echo "项目清理脚本"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 统计变量
DELETED_FILES=0
DELETED_DIRS=0
FREED_SPACE=0

# 函数：删除文件
delete_file() {
    local file=$1
    if [ -f "$file" ]; then
        local size=$(du -h "$file" | cut -f1)
        rm -f "$file"
        echo -e "${GREEN}✓${NC} 已删除文件: $file (大小: $size)"
        ((DELETED_FILES++))
    fi
}

# 函数：删除目录
delete_dir() {
    local dir=$1
    if [ -d "$dir" ]; then
        local size=$(du -sh "$dir" | cut -f1)
        rm -rf "$dir"
        echo -e "${GREEN}✓${NC} 已删除目录: $dir (大小: $size)"
        ((DELETED_DIRS++))
    fi
}

echo "开始清理临时文件..."
echo ""

# 1. 删除测试数据库文件
echo "1. 删除测试数据库文件..."
delete_file "mvp/test_admin.db"
delete_file "mvp/test_data_upload.db"
delete_file "mvp/test_models.db"
delete_file "mvp/test_preview_properties.db"
delete_file "mvp/test_validation_properties.db"
echo ""

# 2. 删除日志文件
echo "2. 删除日志文件..."
delete_file "mvp/logs/app_2026-01-08.log"
delete_file "mvp/logs/app_2026-01-09.log"
delete_file "mvp/logs/app_2026-01-10.log"
delete_file "mvp/logs/error_2026-01-08.log"
delete_file "mvp/logs/error_2026-01-09.log"
delete_file "mvp/logs/error_2026-01-10.log"
delete_file "mvp/final_checkpoint_output.log"
echo ""

# 3. 删除临时文件
echo "3. 删除临时文件..."
delete_file "mvp/final_checkpoint_results.json"
delete_file "mvp/test_auth_manual.py"
delete_file "mvp/uploads/test_data_test_data.csv"
echo ""

# 4. 删除缓存目录
echo "4. 删除缓存目录..."
delete_dir "mvp/.hypothesis"
delete_dir "mvp/.pytest_cache"
echo ""

# 5. 清理Python缓存
echo "5. 清理Python缓存..."
find mvp -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find frontend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
echo -e "${GREEN}✓${NC} 已清理所有__pycache__目录"
echo ""

# 6. 清理Node.js缓存（可选）
echo "6. 清理Node.js缓存（可选）..."
if [ -d "frontend/node_modules/.cache" ]; then
    delete_dir "frontend/node_modules/.cache"
fi
echo ""

# 显示清理结果
echo "=========================================="
echo "清理完成！"
echo "=========================================="
echo -e "${GREEN}已删除文件数: $DELETED_FILES${NC}"
echo -e "${GREEN}已删除目录数: $DELETED_DIRS${NC}"
echo ""

# 显示磁盘使用情况
echo "当前磁盘使用情况:"
echo "mvp目录: $(du -sh mvp | cut -f1)"
echo "backend目录: $(du -sh backend | cut -f1)"
echo "frontend目录: $(du -sh frontend | cut -f1)"
echo ""

echo -e "${YELLOW}提示:${NC}"
echo "1. 生产数据库 mvp/data/bank_code.db 已保留"
echo "2. 环境配置文件 .env 已保留"
echo "3. 所有脚本文件已保留"
echo "4. 所有文档文件已保留"
echo ""

echo -e "${GREEN}清理脚本执行完成！${NC}"
