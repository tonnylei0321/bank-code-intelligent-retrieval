#!/usr/bin/env python3
"""
修复priority字段类型
"""
import sqlite3
import os
from datetime import datetime

def fix_priority_field():
    """修复priority字段类型"""
    db_path = "data/bank_code.db"
    
    if not os.path.exists(db_path):
        print("❌ 数据库文件不存在")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔧 修复priority字段类型...")
        
        # 检查当前priority字段类型
        cursor.execute("PRAGMA table_info(training_jobs)")
        columns = cursor.fetchall()
        
        priority_info = None
        for col in columns:
            if col[1] == 'priority':
                priority_info = col
                break
        
        if priority_info:
            print(f"当前priority字段: {priority_info}")
            if 'VARCHAR' in str(priority_info[2]) or 'TEXT' in str(priority_info[2]):
                print("✅ priority字段类型正确，无需修复")
                return True
        
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
        
        # 恢复数据，将priority的数值转换为字符串
        cursor.execute(f"""
            INSERT INTO training_jobs (
                id, dataset_id, created_by, status, model_name, epochs, batch_size,
                learning_rate, lora_r, lora_alpha, lora_dropout, current_epoch,
                total_steps, current_step, progress_percentage, train_loss, val_loss,
                val_accuracy, training_logs, model_path, error_message, retry_count,
                max_retries, queued_at, priority, created_at, started_at, completed_at, updated_at
            )
            SELECT 
                id, dataset_id, created_by, status, model_name, epochs, batch_size,
                learning_rate, lora_r, lora_alpha, lora_dropout, current_epoch,
                total_steps, current_step, progress_percentage, train_loss, val_loss,
                val_accuracy, training_logs, model_path, error_message, 
                COALESCE(retry_count, 0),
                COALESCE(max_retries, 3),
                queued_at,
                CASE 
                    WHEN priority = 1 THEN 'high'
                    WHEN priority = 2 THEN 'low'
                    ELSE 'medium'
                END as priority,
                created_at, started_at, completed_at, updated_at
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
        
        priority_field = None
        for col in new_columns:
            if col[1] == 'priority':
                priority_field = col
                break
        
        if priority_field:
            print(f"新priority字段: {priority_field}")
        
        print("✅ priority字段类型修复完成")
        
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
    print("🔧 修复priority字段类型")
    print("=" * 50)
    
    success = fix_priority_field()
    
    if success:
        print("🎉 priority字段类型修复完成！")
    else:
        print("❌ priority字段类型修复失败")

if __name__ == "__main__":
    main()