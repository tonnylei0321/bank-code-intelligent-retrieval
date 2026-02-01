#!/usr/bin/env python3
"""
RAG系统修复验证脚本

测试RAG系统的核心功能，验证修复是否成功。
"""
import asyncio
import sys
import os
sys.path.append('.')

from app.core.database import SessionLocal
from app.services.rag_service import RAGService
from loguru import logger

async def test_rag_system():
    """测试RAG系统的核心功能"""
    
    print("🔍 开始测试RAG系统...")
    
    db = SessionLocal()
    try:
        # 1. 初始化RAG服务
        print("1️⃣ 初始化RAG服务...")
        rag_service = RAGService(db)
        print("   ✅ RAG服务初始化成功")
        
        # 2. 获取数据库统计信息
        print("2️⃣ 获取数据库统计信息...")
        stats = rag_service.get_database_stats()
        
        if "error" in stats:
            print(f"   ❌ 获取统计信息失败: {stats['error']}")
            return False
        
        print(f"   📊 向量数据库记录数: {stats['vector_db_count']}")
        print(f"   📊 源数据库记录数: {stats['source_db_count']}")
        print(f"   📊 同步状态: {'已同步' if stats['is_synced'] else '需要同步'}")
        print(f"   📊 嵌入模型维度: {stats['embedding_model']}")
        print("   ✅ 统计信息获取成功")
        
        # 3. 检查向量数据库是否为空
        if stats['vector_db_count'] == 0:
            print("3️⃣ 向量数据库为空，尝试初始化...")
            success = await rag_service.initialize_vector_db()
            if success:
                print("   ✅ 向量数据库初始化成功")
                # 重新获取统计信息
                stats = rag_service.get_database_stats()
                print(f"   📊 初始化后记录数: {stats['vector_db_count']}")
            else:
                print("   ❌ 向量数据库初始化失败")
                return False
        else:
            print("3️⃣ 向量数据库已有数据，跳过初始化")
        
        # 4. 测试RAG检索功能
        print("4️⃣ 测试RAG检索功能...")
        test_questions = [
            "工商银行北京西单",
            "建设银行上海分行",
            "农业银行",
            "中国银行"
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"   测试问题 {i}: {question}")
            try:
                results = await rag_service.retrieve_relevant_banks(
                    question=question,
                    top_k=3,
                    similarity_threshold=0.3
                )
                
                if results:
                    print(f"   ✅ 找到 {len(results)} 个结果:")
                    for j, result in enumerate(results[:2], 1):  # 只显示前2个
                        print(f"      {j}. {result['bank_name']} -> {result['bank_code']}")
                        print(f"         相似度: {result.get('similarity_score', 0):.3f}")
                        print(f"         方法: {result.get('retrieval_method', 'unknown')}")
                else:
                    print(f"   ⚠️ 未找到相关结果")
                    
            except Exception as e:
                print(f"   ❌ 检索失败: {e}")
                return False
        
        # 5. 测试配置管理
        print("5️⃣ 测试配置管理...")
        config = rag_service.get_config()
        print(f"   📊 当前相似度阈值: {config.get('similarity_threshold', 'N/A')}")
        print(f"   📊 检索结果数量: {config.get('top_k', 'N/A')}")
        print(f"   📊 混合检索: {'启用' if config.get('enable_hybrid', False) else '禁用'}")
        print("   ✅ 配置获取成功")
        
        # 6. 测试配置更新
        print("6️⃣ 测试配置更新...")
        test_config = {
            "similarity_threshold": 0.4,
            "top_k": 8
        }
        
        success = rag_service.update_config(test_config)
        if success:
            updated_config = rag_service.get_config()
            print(f"   ✅ 配置更新成功")
            print(f"   📊 新相似度阈值: {updated_config.get('similarity_threshold')}")
            print(f"   📊 新检索结果数量: {updated_config.get('top_k')}")
        else:
            print("   ❌ 配置更新失败")
            return False
        
        print("\n🎉 RAG系统测试完成，所有功能正常！")
        return True
        
    except Exception as e:
        print(f"❌ RAG系统测试失败: {e}")
        logger.error(f"RAG system test failed: {e}")
        return False
        
    finally:
        db.close()

def main():
    """主函数"""
    print("=" * 60)
    print("RAG系统修复验证脚本")
    print("=" * 60)
    
    # 运行异步测试
    success = asyncio.run(test_rag_system())
    
    if success:
        print("\n✅ RAG系统工作正常，修复成功！")
        sys.exit(0)
    else:
        print("\n❌ RAG系统存在问题，需要进一步检查")
        sys.exit(1)

if __name__ == "__main__":
    main()