#!/usr/bin/env python3
"""
修复训练任务表结构
"""
import sqlite3
import os
from datetime import datetime

def fix_training_jobs_schema():
    """修复训练任务表结构"""
    db_path = "data/bank_code.db"
    
    if not os.path.exists(db_path):
        print("❌ 数据库文件不存在")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔧 修复训练任务表结构...")
        
        # 检查当前表结构
        cursor.execute("PRAGMA table_info(training_jobs)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"当前字段: {column_names}")
        
        # 检查缺失的字段
        required_fields = {
            'retry_count': 'INTEGER DEFAULT 0',
            'max_retries': 'INTEGER DEFAULT 3', 
            'queued_at': 'DATETIME',
            'priority': 'VARCHAR(10) DEFAULT "medium"'
        }
        
        missing_fields = []
        for field, definition in required_fields.items():
            if field not in column_names:
                missing_fields.append((field, definition))
        
        if not missing_fields:
            print("✅ 表结构完整，无需修复")
            return True
        
        print(f"缺失字段: {[field for field, _ in missing_fields]}")
        
        # 备份原表
        backup_table = f"training_jobs_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        cursor.execute(f"CREATE TABLE {backup_table} AS SELECT * FROM training_jobs")
        print(f"✅ 已备份原表为: {backup_table}")
        
        # 重建表结构
        cursor.execute("DROP TABLE training_jobs")
        
        create_sql = """
        CREATE TABLE training_jobs (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            dataset_id INTEGER NOT NULL,
            created_by INTEGER NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            model_name VARCHAR(100) NOT NULL DEFAULT 'Qwen/Qwen2.5-0.5B',
            epochs INTEGER NOT NULL DEFAULT 3,
            batch_size INTEGER NOT NULL DEFAULT 8,
            learning_rate FLOAT NOT NULL DEFAULT 0.0002,
            lora_r INTEGER NOT NULL DEFAULT 16,
            lora_alpha INTEGER NOT NULL DEFAULT 32,
            lora_dropout FLOAT NOT NULL DEFAULT 0.05,
            current_epoch INTEGER DEFAULT 0,
            total_steps INTEGER DEFAULT 0,
            current_step INTEGER DEFAULT 0,
            progress_percentage FLOAT DEFAULT 0.0,
            train_loss FLOAT,
            val_loss FLOAT,
            val_accuracy FLOAT,
            training_logs JSON DEFAULT '[]',
            model_path VARCHAR(500),
            error_message TEXT,
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            queued_at DATETIME,
            priority VARCHAR(10) DEFAULT 'medium',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            started_at DATETIME,
            completed_at DATETIME,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(dataset_id) REFERENCES datasets (id) ON DELETE CASCADE,
            FOREIGN KEY(created_by) REFERENCES users (id)
        )
        """
        
        cursor.execute(create_sql)
        
        # 创建索引
        cursor.execute("CREATE INDEX ix_training_jobs_id ON training_jobs (id)")
        
        # 恢复数据
        cursor.execute(f"""
            INSERT INTO training_jobs (
                id, dataset_id, created_by, status, model_name, epochs, batch_size,
                learning_rate, lora_r, lora_alpha, lora_dropout, current_epoch,
                total_steps, current_step, progress_percentage, train_loss, val_loss,
                val_accuracy, training_logs, model_path, error_message, created_at,
                started_at, completed_at, updated_at
            )
            SELECT 
                id, dataset_id, created_by, status, model_name, epochs, batch_size,
                learning_rate, lora_r, lora_alpha, lora_dropout, current_epoch,
                total_steps, current_step, progress_percentage, train_loss, val_loss,
                val_accuracy, training_logs, model_path, error_message, created_at,
                started_at, completed_at, updated_at
            FROM {backup_table}
        """)
        
        # 验证数据恢复
        cursor.execute("SELECT COUNT(*) FROM training_jobs")
        new_count = cursor.fetchone()[0]
        
        cursor.execute(f"SELECT COUNT(*) FROM {backup_table}")
        backup_count = cursor.fetchone()[0]
        
        if new_count == backup_count:
            print(f"✅ 数据恢复成功: {new_count} 条记录")
            # 删除备份表
            cursor.execute(f"DROP TABLE {backup_table}")
            print("✅ 已删除备份表")
        else:
            print(f"⚠️ 数据恢复异常: 原{backup_count}条，现{new_count}条")
        
        # 验证新表结构
        cursor.execute("PRAGMA table_info(training_jobs)")
        new_columns = cursor.fetchall()
        new_column_names = [col[1] for col in new_columns]
        
        print(f"新表字段: {new_column_names}")
        
        # 检查所有必需字段是否存在
        all_present = all(field in new_column_names for field in required_fields.keys())
        
        if all_present:
            print("✅ 表结构修复完成")
        else:
            print("❌ 表结构修复失败")
            return False
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def main():
    print("🔧 修复训练任务表结构")
    print("=" * 50)
    
    success = fix_training_jobs_schema()
    
    if success:
        print("🎉 训练任务表结构修复完成！")
    else:
        print("❌ 训练任务表结构修复失败")

if __name__ == "__main__":
    main()