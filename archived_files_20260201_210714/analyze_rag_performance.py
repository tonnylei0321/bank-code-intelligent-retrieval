#!/usr/bin/env python3
"""
分析RAG检索性能瓶颈
"""

import time
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.rag_service import RAGService
from app.core.database import get_db
from sqlalchemy.orm import Session

def analyze_rag_performance():
    """分析RAG性能瓶颈"""
    
    # 获取数据库会话
    db_gen = get_db()
    db: Session = next(db_gen)
    
    try:
        print("🔍 RAG性能分析开始...")
        
        # 1. 初始化RAG服务（测量时间）
        start_time = time.time()
        rag_service = RAGService(db)
        init_time = time.time() - start_time
        print(f"1. RAG服务初始化耗时: {init_time:.2f}秒")
        
        # 2. 测量向量数据库查询性能
        print("\n2. 测量向量数据库操作性能...")
        
        # 2.1 获取集合统计信息
        start_time = time.time()
        collection_count = rag_service.collection.count()
        count_time = time.time() - start_time
        print(f"   集合计数查询: {count_time:.3f}秒 (记录数: {collection_count})")
        
        # 2.2 测量向量检索性能
        start_time = time.time()
        query_embedding = rag_service.embedding_model.encode(["工商银行西单"], convert_to_tensor=False)
        embedding_time = time.time() - start_time
        print(f"   文本嵌入生成: {embedding_time:.3f}秒")
        
        start_time = time.time()
        vector_results = rag_service.collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=30,
            include=["metadatas", "distances"]
        )
        vector_query_time = time.time() - start_time
        print(f"   向量相似度查询: {vector_query_time:.3f}秒")
        
        # 2.3 测量关键词检索性能
        start_time = time.time()
        all_results = rag_service.collection.get(include=["metadatas"])
        get_all_time = time.time() - start_time
        print(f"   获取所有元数据: {get_all_time:.3f}秒 (这是性能瓶颈！)")
        
        # 2.4 测量关键词匹配性能
        start_time = time.time()
        keyword_matches = 0
        for metadata in all_results["metadatas"]:
            if "西单" in metadata.get("bank_name", ""):
                keyword_matches += 1
        keyword_match_time = time.time() - start_time
        print(f"   关键词匹配处理: {keyword_match_time:.3f}秒 (匹配数: {keyword_matches})")
        
        # 3. 完整检索测试
        print("\n3. 完整检索性能测试...")
        
        import asyncio
        
        start_time = time.time()
        results = asyncio.run(rag_service.retrieve_relevant_banks("工商银行西单", top_k=5))
        total_time = time.time() - start_time
        print(f"   完整检索耗时: {total_time:.2f}秒")
        print(f"   返回结果数: {len(results)}")
        
        # 4. 性能分析总结
        print("\n📊 性能分析总结:")
        print(f"   - RAG服务初始化: {init_time:.2f}秒")
        print(f"   - 文本嵌入生成: {embedding_time:.3f}秒")
        print(f"   - 向量相似度查询: {vector_query_time:.3f}秒")
        print(f"   - 获取所有元数据: {get_all_time:.3f}秒 ⚠️")
        print(f"   - 关键词匹配处理: {keyword_match_time:.3f}秒")
        print(f"   - 完整检索总耗时: {total_time:.2f}秒")
        
        # 5. 性能问题诊断
        print("\n🚨 性能瓶颈分析:")
        if get_all_time > 5.0:
            print("   ❌ 主要瓶颈：获取所有元数据耗时过长")
            print("      - 原因：关键词检索需要遍历所有177k+记录")
            print("      - 建议：优化关键词检索策略，避免全量数据获取")
        
        if init_time > 3.0:
            print("   ⚠️  次要瓶颈：RAG服务初始化较慢")
            print("      - 原因：嵌入模型加载耗时")
            print("      - 建议：使用模型缓存或更轻量的模型")
        
        if embedding_time > 0.5:
            print("   ⚠️  次要瓶颈：文本嵌入生成较慢")
            print("      - 建议：使用GPU加速或更快的嵌入模型")
        
        return True
        
    finally:
        db.close()

if __name__ == "__main__":
    success = analyze_rag_performance()
    sys.exit(0 if success else 1)