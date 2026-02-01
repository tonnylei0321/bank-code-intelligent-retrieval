#!/usr/bin/env python3
"""
调试RAG向量数据库中的西单支行数据
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.rag_service import RAGService
from app.core.database import get_db
from sqlalchemy.orm import Session

def debug_rag_xidan():
    """调试RAG中的西单数据"""
    
    # 获取数据库会话
    db_gen = get_db()
    db: Session = next(db_gen)
    
    try:
        # 初始化RAG服务
        print("1. 初始化RAG服务...")
        rag_service = RAGService(db)
        
        # 检查向量数据库中的所有数据
        print("\n2. 检查向量数据库中包含'西单'的数据...")
        try:
            # 获取所有数据
            all_results = rag_service.collection.get(include=["metadatas", "documents"])
            
            if not all_results["metadatas"]:
                print("❌ 向量数据库为空")
                return False
            
            print(f"   向量数据库总记录数: {len(all_results['metadatas'])}")
            
            # 查找包含西单的记录
            xidan_records = []
            for i, metadata in enumerate(all_results["metadatas"]):
                bank_name = metadata.get("bank_name", "")
                if "西单" in bank_name:
                    xidan_records.append({
                        "bank_name": bank_name,
                        "bank_code": metadata.get("bank_code", ""),
                        "document": all_results["documents"][i] if i < len(all_results["documents"]) else "",
                        "keywords": metadata.get("keywords", "")
                    })
            
            if xidan_records:
                print(f"\n   找到 {len(xidan_records)} 个包含'西单'的记录:")
                for record in xidan_records:
                    print(f"   - {record['bank_name']}")
                    print(f"     联行号: {record['bank_code']}")
                    print(f"     文档: {record['document']}")
                    print(f"     关键词: {record['keywords']}")
                    print()
            else:
                print("   ❌ 向量数据库中没有找到包含'西单'的记录")
            
            # 查找工商银行的记录（前10个）
            print("\n3. 检查向量数据库中工商银行的记录（前10个）...")
            icbc_records = []
            for i, metadata in enumerate(all_results["metadatas"]):
                bank_name = metadata.get("bank_name", "")
                if "工商银行" in bank_name and len(icbc_records) < 10:
                    icbc_records.append({
                        "bank_name": bank_name,
                        "bank_code": metadata.get("bank_code", ""),
                        "document": all_results["documents"][i] if i < len(all_results["documents"]) else ""
                    })
            
            if icbc_records:
                print(f"   找到工商银行记录:")
                for record in icbc_records:
                    print(f"   - {record['bank_name']}")
                    print(f"     联行号: {record['bank_code']}")
                    print()
            else:
                print("   ❌ 向量数据库中没有找到工商银行记录")
            
        except Exception as e:
            print(f"❌ 检查向量数据库失败: {e}")
            return False
        
        # 测试RAG检索
        print("\n4. 测试RAG检索功能...")
        try:
            import asyncio
            
            # 测试西单查询
            results = asyncio.run(rag_service.retrieve_relevant_banks("西单", top_k=5))
            print(f"   '西单'查询结果数: {len(results)}")
            for result in results:
                print(f"   - {result['bank_name']} (分数: {result.get('final_score', 'N/A')})")
            
            # 测试工商银行西单查询
            results = asyncio.run(rag_service.retrieve_relevant_banks("工商银行西单", top_k=5))
            print(f"\n   '工商银行西单'查询结果数: {len(results)}")
            for result in results:
                print(f"   - {result['bank_name']} (分数: {result.get('final_score', 'N/A')})")
            
        except Exception as e:
            print(f"❌ RAG检索测试失败: {e}")
            return False
        
        return True
        
    finally:
        db.close()

if __name__ == "__main__":
    success = debug_rag_xidan()
    sys.exit(0 if success else 1)