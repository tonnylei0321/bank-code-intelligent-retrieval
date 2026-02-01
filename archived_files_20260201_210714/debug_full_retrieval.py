#!/usr/bin/env python3
"""
调试完整检索过程
"""

import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.rag_service import RAGService
from app.core.database import get_db
from sqlalchemy.orm import Session

async def debug_full_retrieval():
    """调试完整检索过程"""
    
    # 获取数据库会话
    db_gen = get_db()
    db: Session = next(db_gen)
    
    try:
        # 初始化RAG服务
        print("1. 初始化RAG服务...")
        rag_service = RAGService(db)
        
        # 测试完整银行名称查询
        query = "中国工商银行股份有限公司北京西单支行"
        print(f"\n2. 测试完整银行名称查询: {query}")
        
        # 手动调用检索函数
        print("\n3. 手动测试_full_name_exact_retrieve...")
        full_name_results = await rag_service._full_name_exact_retrieve(query, 5)
        print(f"完整名称检索结果数: {len(full_name_results)}")
        for i, result in enumerate(full_name_results):
            print(f"{i+1}. {result['bank_name']} -> {result['bank_code']} (分数: {result['final_score']})")
        
        # 测试完整的检索流程
        print("\n4. 测试完整检索流程...")
        results = await rag_service.retrieve_relevant_banks(query, top_k=5)
        print(f"完整检索结果数: {len(results)}")
        for i, result in enumerate(results):
            method = result.get('retrieval_method', 'unknown')
            score = result.get('final_score', 0)
            print(f"{i+1}. {result['bank_name']} -> {result['bank_code']} (分数: {score}, 方法: {method})")
        
        return True
        
    finally:
        db.close()

if __name__ == "__main__":
    success = asyncio.run(debug_full_retrieval())
    sys.exit(0 if success else 1)