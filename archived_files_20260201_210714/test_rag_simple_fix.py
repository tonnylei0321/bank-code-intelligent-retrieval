#!/usr/bin/env python3
"""
简单的RAG测试脚本 - 修复版本
测试RAG检索功能是否正常工作
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.append('.')

from app.core.database import SessionLocal
from app.services.rag_service import RAGService

async def test_rag_basic():
    """基础RAG测试"""
    print("🔍 开始RAG基础功能测试...")
    
    db = SessionLocal()
    try:
        # 初始化RAG服务
        print("1. 初始化RAG服务...")
        rag_service = RAGService(db)
        print("   ✅ RAG服务初始化成功")
        
        # 获取统计信息
        print("2. 获取数据库统计信息...")
        stats = rag_service.get_database_stats()
        if "error" in stats:
            print(f"   ❌ 获取统计信息失败: {stats['error']}")
            return False
        
        print(f"   📊 向量数据库记录数: {stats['vector_db_count']}")
        print(f"   📊 源数据库记录数: {stats['source_db_count']}")
        print(f"   📊 同步状态: {'已同步' if stats['is_synced'] else '需要同步'}")
        print(f"   📊 嵌入模型维度: {stats['embedding_model']}")
        
        # 如果向量数据库为空，尝试初始化
        if stats['vector_db_count'] == 0:
            print("3. 向量数据库为空，尝试初始化...")
            success = await rag_service.initialize_vector_db()
            if not success:
                print("   ❌ 向量数据库初始化失败")
                return False
            print("   ✅ 向量数据库初始化成功")
            
            # 重新获取统计信息
            stats = rag_service.get_database_stats()
            print(f"   📊 初始化后记录数: {stats['vector_db_count']}")
        
        # 测试检索功能
        print("4. 测试RAG检索功能...")
        test_questions = [
            "工商银行北京分行",
            "建设银行上海分行",
            "农业银行"
        ]
        
        for question in test_questions:
            print(f"   🔍 检索问题: {question}")
            try:
                results = await rag_service.retrieve_relevant_banks(
                    question=question,
                    top_k=3,
                    similarity_threshold=0.3
                )
                
                print(f"   📊 找到 {len(results)} 个结果")
                for i, result in enumerate(results[:2], 1):  # 只显示前2个
                    print(f"      {i}. {result['bank_name']}")
                    print(f"         联行号: {result['bank_code']}")
                    print(f"         相似度: {result.get('similarity_score', 0):.3f}")
                    print(f"         方法: {result.get('retrieval_method', 'unknown')}")
                
            except Exception as e:
                print(f"   ❌ 检索失败: {e}")
                return False
        
        print("✅ RAG基础功能测试完成")
        return True
        
    except Exception as e:
        print(f"❌ RAG测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

async def test_rag_config():
    """测试RAG配置功能"""
    print("\n🔧 测试RAG配置功能...")
    
    db = SessionLocal()
    try:
        rag_service = RAGService(db)
        
        # 获取当前配置
        print("1. 获取当前配置...")
        config = rag_service.get_config()
        print(f"   📊 当前相似度阈值: {config['similarity_threshold']}")
        print(f"   📊 当前top_k: {config['top_k']}")
        
        # 测试配置更新
        print("2. 测试配置更新...")
        new_config = {
            "similarity_threshold": 0.4,
            "top_k": 8
        }
        
        success = rag_service.update_config(new_config)
        if success:
            print("   ✅ 配置更新成功")
            updated_config = rag_service.get_config()
            print(f"   📊 更新后相似度阈值: {updated_config['similarity_threshold']}")
            print(f"   📊 更新后top_k: {updated_config['top_k']}")
        else:
            print("   ❌ 配置更新失败")
            return False
        
        print("✅ RAG配置功能测试完成")
        return True
        
    except Exception as e:
        print(f"❌ RAG配置测试失败: {e}")
        return False
    finally:
        db.close()

def main():
    """主函数"""
    print("🚀 RAG系统测试开始")
    print("=" * 50)
    
    # 运行基础测试
    success1 = asyncio.run(test_rag_basic())
    
    # 运行配置测试
    success2 = asyncio.run(test_rag_config())
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("🎉 所有RAG测试通过！")
        return 0
    else:
        print("❌ 部分RAG测试失败")
        return 1

if __name__ == "__main__":
    exit(main())