#!/usr/bin/env python3
"""
简化的RAG测试脚本
"""
import asyncio
import os
import sys

# 设置环境变量
os.environ['SECRET_KEY'] = 'test-secret-key'
os.environ['DATABASE_URL'] = 'sqlite:///./data/bank_code.db'

from app.core.database import get_db
from app.services.rag_service import RAGService
from app.services.query_service import QueryService

async def main():
    db = next(get_db())
    try:
        print("初始化RAG服务...")
        rag_service = RAGService(db)
        query_service = QueryService(db)
        
        # 测试查询
        question = "中国工商银行"
        print(f"\n测试查询: {question}")
        
        # RAG检索
        print("执行RAG检索...")
        results = await rag_service.retrieve_relevant_banks(
            question=question,
            top_k=3,
            similarity_threshold=0.1
        )
        
        print(f"\n检索到 {len(results)} 个结果:")
        for i, result in enumerate(results):
            score = result.get('final_score', result.get('similarity_score', 0))
            print(f"  {i+1}. {result['bank_name'][:50]}... -> {result['bank_code']} (分数: {score:.3f})")
        
        # 生成答案
        if results:
            print("\n生成最终答案...")
            answer = query_service.generate_answer_with_small_model(question, results)
            print(f"最终答案: {answer}")
        else:
            print("未找到相关银行信息")
            
        print("\n测试完成!")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())