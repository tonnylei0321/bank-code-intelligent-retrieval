#!/usr/bin/env python3
"""
数据库迁移脚本：添加样本集表

添加sample_sets表和qa_pairs.sample_set_id字段
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.core.database import engine, SessionLocal
from app.core.logging import logger


def migrate():
    """执行迁移"""
    db = SessionLocal()
    
    try:
        logger.info("开始数据库迁移：添加样本集表")
        
        # 1. 创建sample_sets表
        logger.info("创建sample_sets表...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS sample_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(200) NOT NULL,
                dataset_id INTEGER NOT NULL,
                generation_task_id VARCHAR(100) UNIQUE,
                description TEXT,
                total_samples INTEGER NOT NULL DEFAULT 0,
                train_samples INTEGER NOT NULL DEFAULT 0,
                val_samples INTEGER NOT NULL DEFAULT 0,
                test_samples INTEGER NOT NULL DEFAULT 0,
                generation_config JSON,
                status VARCHAR(20) NOT NULL DEFAULT 'generating',
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """))
        
        # 2. 为sample_sets表创建索引
        logger.info("创建索引...")
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_sample_sets_dataset_id 
            ON sample_sets(dataset_id)
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_sample_sets_task_id 
            ON sample_sets(generation_task_id)
        """))
        
        # 3. 检查qa_pairs表是否已有sample_set_id列
        result = db.execute(text("""
            SELECT COUNT(*) as count 
            FROM pragma_table_info('qa_pairs') 
            WHERE name='sample_set_id'
        """))
        has_column = result.fetchone()[0] > 0
        
        if not has_column:
            logger.info("为qa_pairs表添加sample_set_id列...")
            db.execute(text("""
                ALTER TABLE qa_pairs 
                ADD COLUMN sample_set_id INTEGER 
                REFERENCES sample_sets(id) ON DELETE CASCADE
            """))
            
            # 创建索引
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_qa_pairs_sample_set_id 
                ON qa_pairs(sample_set_id)
            """))
        else:
            logger.info("qa_pairs表已有sample_set_id列，跳过")
        
        db.commit()
        logger.info("✅ 数据库迁移完成！")
        
        # 4. 验证迁移
        logger.info("验证迁移结果...")
        
        # 检查sample_sets表
        result = db.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='sample_sets'
        """))
        if result.fetchone():
            logger.info("✓ sample_sets表创建成功")
        else:
            logger.error("✗ sample_sets表创建失败")
        
        # 检查qa_pairs.sample_set_id列
        result = db.execute(text("""
            SELECT COUNT(*) as count 
            FROM pragma_table_info('qa_pairs') 
            WHERE name='sample_set_id'
        """))
        if result.fetchone()[0] > 0:
            logger.info("✓ qa_pairs.sample_set_id列添加成功")
        else:
            logger.error("✗ qa_pairs.sample_set_id列添加失败")
        
        logger.info("\n迁移完成！现在可以使用样本集功能了。")
        
    except Exception as e:
        db.rollback()
        logger.error(f"迁移失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
