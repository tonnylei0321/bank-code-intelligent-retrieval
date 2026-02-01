#!/usr/bin/env python3
"""
测试RAG优化效果
验证优化后的RAG检索性能和准确性
"""

import time
import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.rag_service import RAGService
from app.core.database import get_db
from sqlalchemy.orm import Session

async def test_rag_optimization():
    """测试RAG优化效果"""
    
    # 获取数据库会话
    db_gen = get_db()
    db: Session = next(db_gen)
    
    try:
        print("🚀 RAG优化效果测试开始...")
        
        # 1. 初始化RAG服务
        print("\n1. 初始化RAG服务...")
        start_time = time.time()
        rag_service = RAGService(db)
        init_time = time.time() - start_time
        print(f"   RAG服务初始化耗时: {init_time:.2f}秒")
        
        # 2. 测试用例
        test_cases = [
            {
                "name": "完整银行名称查询",
                "query": "中国工商银行股份有限公司北京西单支行",
                "expected_contains": ["工商银行", "西单"],
                "expected_first": "中国工商银行股份有限公司北京西单支行"
            },
            {
                "name": "简化银行查询",
                "query": "工商银行西单",
                "expected_contains": ["工商银行", "西单"],
                "expected_first": "中国工商银行股份有限公司北京西单支行"
            },
            {
                "name": "地理位置查询",
                "query": "西单",
                "expected_contains": ["西单"]
            },
            {
                "name": "银行类型查询",
                "query": "建设银行北京",
                "expected_contains": ["建设银行", "北京"]
            },
            {
                "name": "复合查询",
                "query": "北京农业银行",
                "expected_contains": ["农业银行", "北京"]
            }
        ]
        
        print(f"\n2. 开始性能和准确性测试（{len(test_cases)}个测试用例）...")
        
        total_time = 0
        success_count = 0
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n   测试 {i}: {test_case['name']}")
            print(f"   查询: {test_case['query']}")
            
            # 执行查询
            start_time = time.time()
            
            try:
                results = await rag_service.retrieve_relevant_banks(
                    test_case['query'],
                    top_k=5
                )
                
                end_time = time.time()
                query_time = end_time - start_time
                total_time += query_time
                
                print(f"   ⏱️  耗时: {query_time:.3f}秒")
                print(f"   📊 结果数: {len(results)}")
                
                if results:
                    first_result = results[0]['bank_name']
                    print(f"   🥇 第一个结果: {first_result}")
                    print(f"   🎯 第一个分数: {results[0].get('final_score', 'N/A'):.3f}")
                    
                    # 验证结果正确性
                    is_correct = False
                    
                    # 检查期望的第一个结果
                    if 'expected_first' in test_case:
                        if test_case['expected_first'] == first_result:
                            print(f"   ✅ 完全匹配期望结果")
                            is_correct = True
                        elif any(keyword in first_result for keyword in test_case.get('expected_contains', [])):
                            print(f"   ✅ 包含期望关键词")
                            is_correct = True
                        else:
                            print(f"   ❌ 结果不匹配，期望: {test_case['expected_first']}")
                    
                    # 检查期望包含的关键词
                    elif 'expected_contains' in test_case:
                        matched_keywords = [kw for kw in test_case['expected_contains'] if kw in first_result]
                        if matched_keywords:
                            print(f"   ✅ 包含期望关键词: {matched_keywords}")
                            is_correct = True
                        else:
                            print(f"   ❌ 不包含期望关键词: {test_case['expected_contains']}")
                    
                    if is_correct:
                        success_count += 1
                    
                    # 显示前3个结果的详细信息
                    print(f"   📋 前3个结果:")
                    for j, result in enumerate(results[:3]):
                        method = result.get('retrieval_method', 'unknown')
                        score = result.get('final_score', 0)
                        print(f"      {j+1}. {result['bank_name'][:50]}... (分数: {score:.3f}, 方法: {method})")
                
                else:
                    print(f"   ❌ 没有找到结果")
                    
            except Exception as e:
                print(f"   ❌ 查询异常: {e}")
                continue
        
        # 3. 性能总结
        avg_time = total_time / len(test_cases)
        success_rate = (success_count / len(test_cases)) * 100
        
        print(f"\n📊 优化效果总结:")
        print(f"   总测试用例: {len(test_cases)}")
        print(f"   成功用例: {success_count}")
        print(f"   成功率: {success_rate:.1f}%")
        print(f"   总耗时: {total_time:.3f}秒")
        print(f"   平均耗时: {avg_time:.3f}秒")
        print(f"   初始化耗时: {init_time:.2f}秒")
        
        # 4. 性能评估
        print(f"\n🎯 优化效果评估:")
        
        # 性能评估
        if avg_time < 0.5:
            print(f"   🚀 性能优秀 - 平均响应时间 < 0.5秒")
        elif avg_time < 1.0:
            print(f"   ✅ 性能良好 - 平均响应时间 < 1秒")
        elif avg_time < 2.0:
            print(f"   ⚠️  性能一般 - 平均响应时间 < 2秒")
        else:
            print(f"   ❌ 性能需要进一步优化 - 平均响应时间 > 2秒")
        
        # 准确性评估
        if success_rate >= 90:
            print(f"   🎯 准确性优秀 - 成功率 >= 90%")
        elif success_rate >= 70:
            print(f"   ✅ 准确性良好 - 成功率 >= 70%")
        elif success_rate >= 50:
            print(f"   ⚠️  准确性一般 - 成功率 >= 50%")
        else:
            print(f"   ❌ 准确性需要改进 - 成功率 < 50%")
        
        # 5. 优化建议
        print(f"\n💡 进一步优化建议:")
        if init_time > 3.0:
            print(f"   - 考虑使用模型缓存或更轻量的嵌入模型")
        if avg_time > 1.0:
            print(f"   - 考虑添加查询结果缓存")
            print(f"   - 考虑使用GPU加速嵌入生成")
        if success_rate < 80:
            print(f"   - 优化实体提取和匹配逻辑")
            print(f"   - 调整检索策略权重")
        
        return avg_time < 2.0 and success_rate >= 70
        
    finally:
        db.close()

if __name__ == "__main__":
    success = asyncio.run(test_rag_optimization())
    sys.exit(0 if success else 1)