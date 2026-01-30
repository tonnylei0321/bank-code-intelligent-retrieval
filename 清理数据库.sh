#!/bin/bash

# 清理数据库脚本
# 用于删除所有数据集和联行号记录

echo "================================"
echo "清理数据库脚本"
echo "================================"
echo ""
echo "⚠️  警告：此操作将删除所有数据集和联行号记录！"
echo ""
read -p "确认要继续吗？(输入 yes 继续): " confirm

if [ "$confirm" != "yes" ]; then
    echo "操作已取消"
    exit 0
fi

echo ""
echo "正在清理数据库..."
echo ""

# 进入mvp目录
cd mvp

# 查看当前数据
echo "📊 当前数据统计："
sqlite3 data/bank_code.db "SELECT COUNT(*) as '数据集数量' FROM datasets;"
sqlite3 data/bank_code.db "SELECT COUNT(*) as '联行号记录数' FROM bank_codes;"
echo ""

# 删除所有联行号记录
echo "🗑️  删除联行号记录..."
sqlite3 data/bank_code.db "DELETE FROM bank_codes;"
echo "✅ 联行号记录已删除"

# 删除所有数据集
echo "🗑️  删除数据集..."
sqlite3 data/bank_code.db "DELETE FROM datasets;"
echo "✅ 数据集已删除"

# 重置自增ID
echo "🔄 重置自增ID..."
sqlite3 data/bank_code.db "DELETE FROM sqlite_sequence WHERE name='datasets';"
sqlite3 data/bank_code.db "DELETE FROM sqlite_sequence WHERE name='bank_codes';"
echo "✅ 自增ID已重置"

echo ""
echo "📊 清理后数据统计："
sqlite3 data/bank_code.db "SELECT COUNT(*) as '数据集数量' FROM datasets;"
sqlite3 data/bank_code.db "SELECT COUNT(*) as '联行号记录数' FROM bank_codes;"
echo ""

echo "================================"
echo "✅ 数据库清理完成！"
echo "================================"
echo ""
echo "现在可以："
echo "1. 刷新浏览器（Ctrl+F5 或 Cmd+Shift+R）"
echo "2. 重新上传CSV文件"
echo "3. 点击验证按钮"
echo ""
