#!/usr/bin/env python3
"""
数据库迁移脚本：添加用户问答历史表
"""
import sqlite3
import os
from datetime import datetime

def migrate_database():
    """执行数据库迁移"""
    db_path = "data/bank_code.db"
    
    if not os.path.exists(db_path):
        print("❌ 数据库文件不存在")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否已存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='user_qa_history'
        """)
        
        if cursor.fetchone():
            print("✅ user_qa_history 表已存在，跳过创建")
            conn.close()
            return True
        
        # 创建用户问答历史表
        cursor.execute("""
            CREATE TABLE user_qa_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                retrieval_strategy VARCHAR(20) NOT NULL DEFAULT 'intelligent',
                model_type VARCHAR(50),
                confidence_score REAL,
                response_time INTEGER,
                context_count INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX idx_user_qa_history_user_id ON user_qa_history(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX idx_user_qa_history_created_at ON user_qa_history(created_at)
        """)
        
        conn.commit()
        print("✅ 成功创建 user_qa_history 表和索引")
        
        # 验证表结构
        cursor.execute("PRAGMA table_info(user_qa_history)")
        columns = cursor.fetchall()
        print(f"📊 表结构验证: {len(columns)} 个字段")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 数据库迁移失败: {e}")
        return False

def main():
    print("🔄 开始数据库迁移...")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = migrate_database()
    
    if success:
        print("✅ 数据库迁移完成")
    else:
        print("❌ 数据库迁移失败")
    
    return success

if __name__ == "__main__":
    main()