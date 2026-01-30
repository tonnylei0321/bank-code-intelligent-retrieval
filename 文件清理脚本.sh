#!/bin/bash

# 文件清理脚本 - 将无用文件移动到temp目录
# 使用方法: bash 文件清理脚本.sh

set -e

echo "=========================================="
echo "文件清理脚本"
echo "将临时文件、测试数据库、日志文件移动到temp目录"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 统计变量
MOVED_FILES=0
MOVED_DIRS=0

# 创建temp目录结构
echo -e "${BLUE}创建temp目录结构...${NC}"
mkdir -p temp/test_databases
mkdir -p temp/logs
mkdir -p temp/cache
mkdir -p temp/temp_files
echo -e "${GREEN}✓${NC} temp目录结构已创建"
echo ""

# 函数：移动文件
move_file() {
    local file=$1
    local dest=$2
    if [ -f "$file" ]; then
        local size=$(du -h "$file" | cut -f1)
        mv "$file" "$dest/"
        echo -e "${GREEN}✓${NC} 已移动文件: $file -> $dest/ (大小: $size)"
        ((MOVED_FILES++))
    else
        echo -e "${YELLOW}⚠${NC} 文件不存在: $file"
    fi
}

# 函数：移动目录
move_dir() {
    local dir=$1
    local dest=$2
    if [ -d "$dir" ]; then
        local size=$(du -sh "$dir" | cut -f1)
        mv "$dir" "$dest/"
        echo -e "${GREEN}✓${NC} 已移动目录: $dir -> $dest/ (大小: $size)"
        ((MOVED_DIRS++))
    else
        echo -e "${YELLOW}⚠${NC} 目录不存在: $dir"
    fi
}

echo "开始移动文件..."
echo ""

# 1. 移动测试数据库文件
echo -e "${BLUE}1. 移动测试数据库文件...${NC}"
move_file "mvp/test_admin.db" "temp/test_databases"
move_file "mvp/test_data_upload.db" "temp/test_databases"
move_file "mvp/test_models.db" "temp/test_databases"
move_file "mvp/test_preview_properties.db" "temp/test_databases"
move_file "mvp/test_validation_properties.db" "temp/test_databases"
echo ""

# 2. 移动日志文件
echo -e "${BLUE}2. 移动日志文件...${NC}"
move_file "mvp/logs/app_2026-01-08.log" "temp/logs"
move_file "mvp/logs/app_2026-01-09.log" "temp/logs"
move_file "mvp/logs/app_2026-01-10.log" "temp/logs"
move_file "mvp/logs/error_2026-01-08.log" "temp/logs"
move_file "mvp/logs/error_2026-01-09.log" "temp/logs"
move_file "mvp/logs/error_2026-01-10.log" "temp/logs"
move_file "mvp/final_checkpoint_output.log" "temp/logs"
echo ""

# 3. 移动临时文件
echo -e "${BLUE}3. 移动临时文件...${NC}"
move_file "mvp/final_checkpoint_results.json" "temp/temp_files"
move_file "mvp/test_auth_manual.py" "temp/temp_files"
move_file "mvp/uploads/test_data_test_data.csv" "temp/temp_files"
echo ""

# 4. 移动缓存目录
echo -e "${BLUE}4. 移动缓存目录...${NC}"
move_dir "mvp/.hypothesis" "temp/cache"
move_dir "mvp/.pytest_cache" "temp/cache"
echo ""

# 5. 清理Python缓存（可选）
echo -e "${BLUE}5. 清理Python缓存（__pycache__）...${NC}"
echo -e "${YELLOW}提示: 这将删除所有__pycache__目录，不会移动到temp${NC}"
read -p "是否继续？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    find mvp -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find frontend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    echo -e "${GREEN}✓${NC} 已清理所有__pycache__目录"
else
    echo -e "${YELLOW}⊘${NC} 跳过__pycache__清理"
fi
echo ""

# 显示清理结果
echo "=========================================="
echo "清理完成！"
echo "=========================================="
echo -e "${GREEN}已移动文件数: $MOVED_FILES${NC}"
echo -e "${GREEN}已移动目录数: $MOVED_DIRS${NC}"
echo ""

# 显示temp目录结构
echo "temp目录结构:"
tree -L 2 temp 2>/dev/null || ls -R temp
echo ""

# 显示磁盘使用情况
echo "当前磁盘使用情况:"
echo "mvp目录: $(du -sh mvp 2>/dev/null | cut -f1)"
echo "backend目录: $(du -sh backend 2>/dev/null | cut -f1)"
echo "frontend目录: $(du -sh frontend 2>/dev/null | cut -f1)"
echo "temp目录: $(du -sh temp 2>/dev/null | cut -f1)"
echo ""

echo -e "${YELLOW}重要提示:${NC}"
echo "1. 生产数据库 mvp/data/bank_code.db 已保留"
echo "2. 环境配置文件 .env 已保留"
echo "3. 所有脚本文件已保留"
echo "4. 所有文档文件已保留"
echo "5. 临时文件已移动到 temp/ 目录"
echo "6. 如需恢复文件，可从 temp/ 目录中找回"
echo ""

echo -e "${GREEN}清理脚本执行完成！${NC}"
echo ""
echo "如需永久删除temp目录，请执行："
echo "  rm -rf temp"
