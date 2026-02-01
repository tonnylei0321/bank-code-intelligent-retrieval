#!/usr/bin/env python3
"""
RAG检索问题诊断脚本

这个脚本将帮助诊断RAG检索失败的原因
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

# 设置环境变量
os.environ['SECRET_KEY'] = 'debug-secret-key-for-testing'
os.environ['DATABASE_URL'] = 'sqlite:///mvp/data/bank_code.db'

from app.services.rag_service import RAGService
from app.core.database import SessionLocal

async def diagnose_rag_issue():
    """诊断RAG检索问题"""
    
    print("🔍 开始诊断RAG检索问题...")
    
    # 创建数据库会话
    db = SessionLocal()
    
    try:
        # 1. 检查RAG服务初始化
        print("\n1️⃣ 检查RAG服务初始化...")
        rag_service = RAGService(db)
        print("✅ RAG服务初始化成功")
        
        # 2. 检查向量数据库统计
        print("\n2️⃣ 检查向量数据库统计...")
        stats = rag_service.get_database_stats()
        print("📊 RAG数据库统计信息:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        if stats.get('vector_db_count', 0) == 0:
            print("❌ 向量数据库为空！这是检索失败的主要原因。")
            return
        
        # 3. 测试不同相似度阈值的检索
        print("\n3️⃣ 测试不同相似度阈值的检索...")
        test_questions = [
            "工商银行",
            "中国工商银行",
            "工行",
            "建设银行",
            "农业银行"
        ]
        
        thresholds = [0.1, 0.3, 0.5, 0.7, 0.9]
        
        for question in test_questions:
            print(f"\n🔍 测试问题: '{question}'")
            
            for threshold in thresholds:
                try:
                    results = await rag_service.retrieve_relevant_banks(
                        question=question,
                        top_k=5,
                        similarity_threshold=threshold
                    )
                    print(f"   阈值 {threshold}: {len(results)} 个结果")
                    
                    if results:
                        for i, result in enumerate(results[:2]):  # 只显示前2个
                            print(f"     结果{i+1}: {result['bank_name'][:30]}... -> {result['bank_code']} (相似度: {result.get('similarity_score', 'N/A'):.3f})")
                
                except Exception as e:
                    print(f"   阈值 {threshold}: 错误 - {e}")
        
        # 4. 测试原始ChromaDB查询
        print("\n4️⃣ 测试原始ChromaDB查询...")
        try:
            question = "工商银行"
            question_embedding = rag_service.embedding_model.encode([question], convert_to_tensor=False)
            
            # 直接查询ChromaDB
            raw_results = rag_service.collection.query(
                query_embeddings=question_embedding.tolist(),
                n_results=5,
                include=["documents", "metadatas", "distances"]
            )
            
            print(f"📋 原始ChromaDB查询结果:")
            print(f"   找到 {len(raw_results['documents'][0]) if raw_results['documents'] else 0} 个文档")
            
            if raw_results['documents'] and raw_results['documents'][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    raw_results['documents'][0][:3],
                    raw_results['metadatas'][0][:3], 
                    raw_results['distances'][0][:3]
                )):
                    print(f"   结果{i+1}: {metadata['bank_name'][:30]}... (距离: {distance:.3f})")
        
        except Exception as e:
            print(f"❌ 原始ChromaDB查询失败: {e}")
        
        # 5. 检查嵌入模型
        print("\n5️⃣ 检查嵌入模型...")
        try:
            test_text = "中国工商银行"
            embedding = rag_service.embedding_model.encode([test_text])
            print(f"✅ 嵌入模型正常，维度: {embedding.shape}")
        except Exception as e:
            print(f"❌ 嵌入模型错误: {e}")
        
        # 6. 建议修复方案
        print("\n6️⃣ 修复建议:")
        print("   1. 降低相似度阈值到 0.3 或更低")
        print("   2. 检查嵌入模型是否与训练时一致")
        print("   3. 重新初始化向量数据库")
        print("   4. 检查查询预处理逻辑")
        
    except Exception as e:
        print(f"❌ 诊断过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(diagnose_rag_issue())