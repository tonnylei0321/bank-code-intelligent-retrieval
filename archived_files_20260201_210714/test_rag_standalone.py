#!/usr/bin/env python3
"""
独立RAG系统测试（完全不依赖数据库）
"""

import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 创建一个模拟的数据库会话，但不实际连接数据库
class MockDBSession:
    def close(self):
        pass

async def test_rag_standalone():
    """测试独立的RAG系统"""
    
    try:
        # 直接导入RAG服务，使用模拟数据库会话
        from app.services.rag_service import RAGService
        
        print("1. 初始化独立RAG服务...")
        # 使用模拟数据库会话初始化RAG服务
        mock_db = MockDBSession()
        rag_service = RAGService(mock_db)
        
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
        
        print(f"\n2. 开始纯RAG检索测试（{len(test_cases)}个测试用例）...")
        print("   📌 注意：完全基于向量数据库检索，不使用传统数据库")
        
        success_count = 0
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n   测试 {i}: {test_case['name']}")
            print(f"   查询: {test_case['query']}")
            
            try:
                # 执行纯RAG检索
                results = await rag_service.retrieve_relevant_banks(
                    test_case['query'], 
                    top_k=5,
                    similarity_threshold=0.1
                )
                
                print(f"   📊 RAG检索结果数: {len(results)}")
                
                if results:
                    first_result = results[0]['bank_name']
                    print(f"   🥇 第一个结果: {first_result}")
                    print(f"   📍 联行号: {results[0]['bank_code']}")
                    print(f"   🔍 检索方法: {results[0].get('retrieval_method', 'unknown')}")
                    print(f"   📊 RAG分数: {results[0].get('final_score', 'N/A'):.3f}")
                    
                    # 显示前3个结果
                    if len(results) > 1:
                        print(f"   📋 其他结果:")
                        for j, result in enumerate(results[1:4], 2):
                            print(f"      {j}. {result['bank_name']} (分数: {result.get('final_score', 0):.3f})")
                    
                    # 验证结果正确性
                    if 'expected_first' in test_case:
                        if test_case['expected_first'] == first_result:
                            print(f"   ✅ 完全匹配正确")
                            success_count += 1
                        elif test_case['expected_first'] in first_result:
                            print(f"   ✅ 包含匹配正确")
                            success_count += 1
                        else:
                            print(f"   ❌ 结果不匹配")
                            print(f"      期望: {test_case['expected_first']}")
                            print(f"      实际: {first_result}")
                    elif 'expected_contains' in test_case:
                        if test_case['expected_contains'] in first_result:
                            print(f"   ✅ 包含期望内容")
                            success_count += 1
                        else:
                            print(f"   ❌ 不包含期望内容: {test_case['expected_contains']}")
                else:
                    print(f"   ❌ RAG检索无结果")
                    
            except Exception as e:
                print(f"   ❌ RAG检索异常: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # 测试总结
        success_rate = (success_count / len(test_cases)) * 100
        
        print(f"\n📊 纯RAG检索测试总结:")
        print(f"   总测试用例: {len(test_cases)}")
        print(f"   成功用例: {success_count}")
        print(f"   成功率: {success_rate:.1f}%")
        
        # 评估
        print(f"\n🎯 RAG检索准确性评估:")
        if success_rate >= 80:
            print(f"   🎯 优秀 - RAG检索成功率 >= 80%")
        elif success_rate >= 60:
            print(f"   ✅ 良好 - RAG检索成功率 >= 60%")
        else:
            print(f"   ❌ 需要改进 - RAG检索成功率 < 60%")
        
        # 特别测试关键用例
        print(f"\n🔍 关键用例验证:")
        key_query = "中国工商银行股份有限公司北京西单支行"
        print(f"   测试查询: {key_query}")
        
        key_results = await rag_service.retrieve_relevant_banks(key_query, top_k=3)
        if key_results and key_results[0]['bank_name'] == key_query:
            print(f"   ✅ 关键用例通过 - 完整名称精确匹配成功")
        else:
            print(f"   ❌ 关键用例失败 - 完整名称匹配有问题")
            if key_results:
                print(f"      实际返回: {key_results[0]['bank_name']}")
        
        return success_rate >= 60
        
    except Exception as e:
        print(f"❌ RAG系统初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 启动纯RAG检索系统测试")
    print("📌 本测试完全基于向量数据库，不使用传统SQL数据库")
    success = asyncio.run(test_rag_standalone())
    sys.exit(0 if success else 1)