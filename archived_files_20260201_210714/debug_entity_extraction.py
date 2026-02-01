#!/usr/bin/env python3
"""
调试实体提取逻辑
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.rag_service import RAGService
from app.core.database import get_db
from sqlalchemy.orm import Session

def debug_entity_extraction():
    """调试实体提取"""
    
    # 获取数据库会话
    db_gen = get_db()
    db: Session = next(db_gen)
    
    try:
        # 初始化RAG服务
        print("1. 初始化RAG服务...")
        rag_service = RAGService(db)
        
        # 测试实体提取
        test_queries = [
            "中国工商银行股份有限公司北京西单支行",
            "工商银行西单",
            "西单",
            "建设银行",
            "北京农业银行"
        ]
        
        print("\n2. 测试实体提取...")
        for query in test_queries:
            print(f"\n查询: {query}")
            entities = rag_service._extract_question_entities(query)
            print(f"提取的实体: {entities}")
            
            # 特别检查full_name
            if entities.get('full_name'):
                print(f"✅ 检测到完整银行名称: {entities['full_name']}")
            else:
                print("❌ 未检测到完整银行名称")
        
        return True
        
    finally:
        db.close()

if __name__ == "__main__":
    success = debug_entity_extraction()
    sys.exit(0 if success else 1)