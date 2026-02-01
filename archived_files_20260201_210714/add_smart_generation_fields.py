"""
数据库迁移脚本：为 qa_pairs 表添加智能生成字段

添加字段：
- bank_name: 银行名称
- bank_code: 联行号
"""
import sqlite3

def migrate_database(db_path: str = "data/bank_code.db"):
    """添加智能生成相关字段到 qa_pairs 表"""
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(qa_pairs)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # 添加 bank_name 字段
        if 'bank_name' not in columns:
            print("添加 bank_name 字段...")
            cursor.execute("ALTER TABLE qa_pairs ADD COLUMN bank_name VARCHAR(200)")
            print("✅ bank_name 字段添加成功")
        else:
            print("bank_name 字段已存在，跳过")
        
        # 添加 bank_code 字段
        if 'bank_code' not in columns:
            print("添加 bank_code 字段...")
            cursor.execute("ALTER TABLE qa_pairs ADD COLUMN bank_code VARCHAR(12)")
            print("✅ bank_code 字段添加成功")
        else:
            print("bank_code 字段已存在，跳过")
        
        conn.commit()
        print("✅ 数据库迁移完成")
        
    except Exception as e:
        print(f"数据库迁移失败: {e}")
        raise
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    print("开始数据库迁移...")
    migrate_database()
    print("迁移完成！")
