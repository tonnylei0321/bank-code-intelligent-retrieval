#!/bin/bash

# SQLite数据库备份脚本

set -e

BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_FILE="./data/training_platform.db"

echo "🔄 开始备份..."

# 创建备份目录
mkdir -p $BACKUP_DIR

# 检查数据库文件是否存在
if [ ! -f "$DB_FILE" ]; then
    echo "❌ 数据库文件不存在: $DB_FILE"
    exit 1
fi

# 备份SQLite数据库
echo "📦 备份数据库..."
cp $DB_FILE $BACKUP_DIR/training_platform_$DATE.db

# 备份文件数据
echo "📦 备份文件数据..."
tar -czf $BACKUP_DIR/files_backup_$DATE.tar.gz data/uploads data/models 2>/dev/null || true

# 清理旧备份（保留7天）
echo "🧹 清理旧备份..."
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "✅ 备份完成: $BACKUP_DIR"
echo "数据库备份: training_platform_$DATE.db"
echo "文件备份: files_backup_$DATE.tar.gz"