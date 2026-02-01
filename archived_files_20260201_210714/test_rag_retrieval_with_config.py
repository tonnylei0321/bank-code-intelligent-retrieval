#!/usr/bin/env python3
"""
测试RAG检索功能是否正确使用配置参数
"""

import sys
sys.path.append('.')
import asyncio

from app.services.rag_service import RAGService
from app.core.database import get_db


async def test_retrieval_with_config():
    """测试检索功能使用配置参数"""
    print("=" * 60)
    print("RAG检索配置参数测试")
    print("=" * 60)
    
    # 初始化RAG服务
    print("\n1. 初始化RAG服务...")
    db = next(get_db())
    rag_service = RAGService(db)
    print("✓ RAG服务初始化成功")
    
    # 检查向量数据库状态
    collection_count = rag_service.collection.count()
    print(f"✓ 向量数据库包含 {collection_count} 条记录")
    
    if collection_count == 0:
        print("⚠️  向量数据库为空，跳过检索测试")
        return
    
    # 测试默认配置检索
    print("\n2. 测试默认配置检索...")
    test_question = "工商银行北京分行"
    
    default_results = await rag_service.retrieve_relevant_banks(test_question)
    print(f"✓ 默认配置检索到 {len(default_results)} 个结果")
    
    if default_results:
        print("前3个结果:")
        for i, result in enumerate(default_results[:3], 1):
            print(f"  {i}. {result['bank_name']} -> {result['bank_code']} (分数: {result.get('final_score', 0):.3f})")
    
    # 测试修改top_k参数
    print("\n3. 测试修改top_k参数...")
    rag_service.update_config({'top_k': 3})
    
    limited_results = await rag_service.retrieve_relevant_banks(test_question)
    print(f"✓ top_k=3时检索到 {len(limited_results)} 个结果")
    
    if len(limited_results) <= 3:
        print("✓ top_k参数生效")
    else:
        print("✗ top_k参数未生效")
    
    # 测试修改相似度阈值
    print("\n4. 测试修改相似度阈值...")
    rag_service.update_config({'similarity_threshold': 0.8})  # 很高的阈值
    
    strict_results = await rag_service.retrieve_relevant_banks(test_question)
    print(f"✓ 高阈值(0.8)时检索到 {len(strict_results)} 个结果")
    
    # 降低阈值
    rag_service.update_config({'similarity_threshold': 0.1})  # 很低的阈值
    
    loose_results = await rag_service.retrieve_relevant_banks(test_question)
    print(f"✓ 低阈值(0.1)时检索到 {len(loose_results)} 个结果")
    
    if len(loose_results) >= len(strict_results):
        print("✓ 相似度阈值参数生效")
    else:
        print("✗ 相似度阈值参数未生效")
    
    # 测试混合检索权重
    print("\n5. 测试混合检索权重...")
    
    # 纯向量检索
    rag_service.update_config({
        'vector_weight': 1.0,
        'keyword_weight': 0.0,
        'similarity_threshold': 0.3,
        'top_k': 5
    })
    
    vector_only_results = await rag_service.retrieve_relevant_banks(test_question)
    print(f"✓ 纯向量检索到 {len(vector_only_results)} 个结果")
    
    # 平衡混合检索
    rag_service.update_config({
        'vector_weight': 0.5,
        'keyword_weight': 0.5
    })
    
    balanced_results = await rag_service.retrieve_relevant_banks(test_question)
    print(f"✓ 平衡混合检索到 {len(balanced_results)} 个结果")
    
    # 比较结果差异
    if vector_only_results and balanced_results:
        vector_top = vector_only_results[0]['bank_name']
        balanced_top = balanced_results[0]['bank_name']
        
        if vector_top != balanced_top:
            print("✓ 混合检索权重影响结果排序")
        else:
            print("- 混合检索权重对此查询影响较小")
    
    # 恢复默认配置
    print("\n6. 恢复默认配置...")
    default_config = rag_service._get_default_config()
    rag_service.update_config(default_config)
    print("✓ 配置已恢复默认值")
    
    print("\n" + "=" * 60)
    print("RAG检索配置参数测试完成")
    print("=" * 60)


async def test_config_persistence():
    """测试配置持久性"""
    print("\n" + "=" * 60)
    print("RAG配置持久性测试")
    print("=" * 60)
    
    # 创建第一个RAG服务实例
    print("\n1. 创建第一个RAG服务实例...")
    db1 = next(get_db())
    rag_service1 = RAGService(db1)
    
    # 修改配置
    test_config = {
        'top_k': 7,
        'similarity_threshold': 0.45,
        'temperature': 0.15
    }
    
    rag_service1.update_config(test_config)
    print("✓ 第一个实例配置已更新")
    
    # 创建第二个RAG服务实例
    print("\n2. 创建第二个RAG服务实例...")
    db2 = next(get_db())
    rag_service2 = RAGService(db2)
    
    # 检查配置是否持久化（注意：当前实现中配置是实例级别的，不是持久化的）
    config2 = rag_service2.get_config()
    
    print("第二个实例的配置:")
    for key in test_config.keys():
        value = config2.get(key)
        print(f"  - {key}: {value}")
    
    # 由于当前实现配置不持久化，第二个实例应该使用默认配置
    default_config = rag_service2._get_default_config()
    is_default = all(config2.get(k) == default_config.get(k) for k in test_config.keys())
    
    if is_default:
        print("✓ 配置是实例级别的（符合当前设计）")
    else:
        print("- 配置在实例间共享（可能需要检查）")
    
    print("\n" + "=" * 60)
    print("配置持久性测试完成")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(test_retrieval_with_config())
        asyncio.run(test_config_persistence())
        print("\n🎉 所有检索配置测试完成！")
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()