#!/usr/bin/env python3
"""
修复数据库模式 - 添加缺失的字段

添加BankCode表的updated_at字段和TrainingJob表的缺失字段
"""

import sqlite3
import os
from datetime import datetime

def fix_database_schema():
    """修复数据库模式"""
    db_path = "data/bank_code.db"
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔧 开始修复数据库模式...")
        
        # 检查并添加bank_codes表的updated_at字段
        print("📋 检查bank_codes表...")
        cursor.execute("PRAGMA table_info(bank_codes)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'updated_at' not in columns:
            print("➕ 添加bank_codes.updated_at字段...")
            current_time = datetime.utcnow().isoformat()
            cursor.execute(f"ALTER TABLE bank_codes ADD COLUMN updated_at TEXT DEFAULT '{current_time}'")
            
            # 更新现有记录的updated_at字段
            cursor.execute(f"UPDATE bank_codes SET updated_at = '{current_time}' WHERE updated_at IS NULL")
            print("✅ bank_codes.updated_at字段添加完成")
        else:
            print("✅ bank_codes.updated_at字段已存在")
        
        # 检查并添加training_jobs表的缺失字段
        print("📋 检查training_jobs表...")
        cursor.execute("PRAGMA table_info(training_jobs)")
        columns = [column[1] for column in cursor.fetchall()]
        
        missing_fields = []
        required_fields = {
            'retry_count': 'INTEGER DEFAULT 0',
            'max_retries': 'INTEGER DEFAULT 3',
            'queued_at': f'TEXT DEFAULT "{datetime.utcnow().isoformat()}"',
            'priority': 'INTEGER DEFAULT 0'
        }
        
        for field, definition in required_fields.items():
            if field not in columns:
                missing_fields.append((field, definition))
        
        if missing_fields:
            print(f"➕ 添加training_jobs表的缺失字段: {[f[0] for f in missing_fields]}")
            for field, definition in missing_fields:
                cursor.execute(f"ALTER TABLE training_jobs ADD COLUMN {field} {definition}")
                print(f"✅ 添加字段: {field}")
        else:
            print("✅ training_jobs表字段完整")
        
        # 提交更改
        conn.commit()
        print("✅ 数据库模式修复完成")
        
        # 验证修复结果
        print("🔍 验证修复结果...")
        
        # 验证bank_codes表
        cursor.execute("PRAGMA table_info(bank_codes)")
        bank_codes_columns = [column[1] for column in cursor.fetchall()]
        print(f"📊 bank_codes表字段: {bank_codes_columns}")
        
        # 验证training_jobs表
        cursor.execute("PRAGMA table_info(training_jobs)")
        training_jobs_columns = [column[1] for column in cursor.fetchall()]
        print(f"📊 training_jobs表字段: {training_jobs_columns}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 修复数据库模式失败: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    success = fix_database_schema()
    if success:
        print("🎉 数据库模式修复成功！")
    else:
        print("❌ 数据库模式修复失败！")