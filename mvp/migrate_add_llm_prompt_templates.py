#!/usr/bin/env python3
"""
数据库迁移脚本：添加LLM提示词模板表

创建llm_prompt_templates表用于存储和管理LLM提示词模板
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger
from sqlalchemy import text

from app.core.database import engine, SessionLocal


def migrate():
    """执行数据库迁移"""
    logger.info("开始数据库迁移：添加LLM提示词模板表")
    
    with engine.connect() as conn:
        # 创建llm_prompt_templates表
        logger.info("创建llm_prompt_templates表...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS llm_prompt_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider VARCHAR(50) NOT NULL,
                prompt_type VARCHAR(50) NOT NULL DEFAULT 'sample_generation',
                question_type VARCHAR(50) NOT NULL,
                template TEXT NOT NULL,
                description TEXT,
                is_default BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # 创建索引
        logger.info("创建索引...")
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_llm_prompt_templates_provider 
            ON llm_prompt_templates(provider)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_llm_prompt_templates_prompt_type 
            ON llm_prompt_templates(prompt_type)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_llm_prompt_templates_question_type 
            ON llm_prompt_templates(question_type)
        """))
        
        conn.commit()
        
        logger.info("✅ 数据库迁移完成！")
    
    # 验证迁移结果
    logger.info("验证迁移结果...")
    with engine.connect() as conn:
        # 检查表是否存在
        result = conn.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='llm_prompt_templates'
        """))
        
        if result.fetchone():
            logger.info("✓ llm_prompt_templates表创建成功")
        else:
            logger.error("✗ llm_prompt_templates表创建失败")
            return False
    
    logger.info("\n迁移完成！现在可以使用LLM提示词模板管理功能了。")
    return True


if __name__ == "__main__":
    try:
        success = migrate()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
