#!/usr/bin/env python3
"""
直接测试RAG系统（不通过API）
"""

import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.rag_service import RAGService
from app.core.database import get_db
from sqlalchemy.orm import Session

async def test_rag_direct():
    """直接测试RAG系统"""
    
    # 获取数据库会话（即使不用数据库，也需要初始化）
    db_gen = get_db()
    db: Session = next(db_gen)
    
    try:
        # 初始化RAG服务
        print("1. 初始化RAG服务...")
        rag_service = RAGService(db)
        
        # 测试用例
        test_cases = [
            {
                "name": "完整银行名称查询",
                "query": "中国工商银行股份有限公司北京西单支行",
                "expected_first": "中国工商银行股份有限公司北京西单支行"
            },
            {
                "name": "简化银行查询",
                "query": "工商银行西单",
                "expected_first": "中国工商银行股份有限公司北京西单支行"
            },
            {
                "name": "地理位置查询",
                "query": "西单",
                "expected_contains": "西单"
            },
            {
                "name": "银行类型查询",
                "query": "建设银行",
                "expected_contains": "建设银行"
            },
            {
                "name": "复合查询",
                "query": "北京农业银行",
                "expected_contains": "农业银行"
            }
        ]
        
        print(f"\n2. 开始RAG测试（{len(test_cases)}个测试用例）...")
        
        success_count = 0
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n   测试 {i}: {test_case['name']}")
            print(f"   查询: {test_case['query']}")
            
            try:
                # 执行RAG检索
                results = await rag_service.retrieve_relevant_banks(
                    test_case['query'], 
                    top_k=5
                )
                
                print(f"   📊 结果数: {len(results)}")
                
                if results:
                    first_result = results[0]['bank_name']
                    print(f"   🥇 第一个结果: {first_result}")
                    print(f"   📍 联行号: {results[0]['bank_code']}")
                    print(f"   🔍 检索方法: {results[0].get('retrieval_method', 'unknown')}")
                    print(f"   📊 分数: {results[0].get('final_score', 'N/A')}")
                    
                    # 验证结果正确性
                    if 'expected_first' in test_case:
                        if test_case['expected_first'] in first_result:
                            print(f"   ✅ 结果正确")
                            success_count += 1
                        else:
                            print(f"   ❌ 结果不匹配，期望: {test_case['expected_first']}")
                    elif 'expected_contains' in test_case:
                        if test_case['expected_contains'] in first_result:
                            print(f"   ✅ 结果包含期望内容")
                            success_count += 1
                        else:
                            print(f"   ❌ 结果不包含期望内容: {test_case['expected_contains']}")
                else:
                    print(f"   ❌ 没有找到结果")
                    
            except Exception as e:
                print(f"   ❌ 查询异常: {e}")
                continue
        
        # 测试总结
        success_rate = (success_count / len(test_cases)) * 100
        
        print(f"\n📊 RAG测试总结:")
        print(f"   总测试用例: {len(test_cases)}")
        print(f"   成功用例: {success_count}")
        print(f"   成功率: {success_rate:.1f}%")
        
        # 评估
        print(f"\n🎯 准确性评估:")
        if success_rate >= 80:
            print(f"   🎯 优秀 - 成功率 >= 80%")
        elif success_rate >= 60:
            print(f"   ✅ 良好 - 成功率 >= 60%")
        else:
            print(f"   ❌ 需要改进 - 成功率 < 60%")
        
        return success_rate >= 60
        
    finally:
        db.close()

if __name__ == "__main__":
    success = asyncio.run(test_rag_direct())
    sys.exit(0 if success else 1)