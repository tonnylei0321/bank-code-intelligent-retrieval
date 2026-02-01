#!/usr/bin/env python3
"""
修复RAG向量数据库脚本

这个脚本将重新初始化RAG向量数据库，从文件或数据库导入数据
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

async def fix_rag_database():
    """修复RAG向量数据库"""
    
    print("🔧 开始修复RAG向量数据库...")
    
    # 创建数据库会话
    db = SessionLocal()
    
    try:
        # 1. 创建RAG服务
        print("\n1️⃣ 创建RAG服务...")
        rag_service = RAGService(db)
        print("✅ RAG服务创建成功")
        
        # 2. 检查当前状态
        print("\n2️⃣ 检查当前状态...")
        stats = rag_service.get_database_stats()
        print(f"   向量数据库记录数: {stats.get('vector_db_count', 0)}")
        print(f"   源数据库记录数: {stats.get('source_db_count', 0)}")
        
        # 3. 选择修复方式
        print("\n3️⃣ 选择修复方式...")
        
        # 方式1：从文件导入（推荐，因为之前成功过）
        file_path = "data/T_BANK_LINE_NO_ICBC_ALL.unl"
        if os.path.exists(file_path):
            print(f"✅ 找到银行数据文件: {file_path}")
            print("🔄 开始从文件重新导入RAG数据...")
            
            success = await rag_service.load_from_file(file_path, force_rebuild=True)
            
            if success:
                print("✅ 从文件导入成功！")
            else:
                print("❌ 从文件导入失败，尝试从数据库导入...")
                # 方式2：从数据库导入
                success = await rag_service.initialize_vector_db(force_rebuild=True)
                if success:
                    print("✅ 从数据库导入成功！")
                else:
                    print("❌ 从数据库导入也失败了")
                    return False
        else:
            print(f"❌ 未找到文件 {file_path}，尝试从数据库导入...")
            # 方式2：从数据库导入
            success = await rag_service.initialize_vector_db(force_rebuild=True)
            if success:
                print("✅ 从数据库导入成功！")
            else:
                print("❌ 从数据库导入失败")
                return False
        
        # 4. 验证修复结果
        print("\n4️⃣ 验证修复结果...")
        stats = rag_service.get_database_stats()
        print(f"   修复后向量数据库记录数: {stats.get('vector_db_count', 0)}")
        
        if stats.get('vector_db_count', 0) > 0:
            print("✅ RAG向量数据库修复成功！")
            
            # 5. 测试检索功能
            print("\n5️⃣ 测试检索功能...")
            test_questions = ["工商银行", "建设银行", "农业银行"]
            
            for question in test_questions:
                results = await rag_service.retrieve_relevant_banks(
                    question=question,
                    top_k=3,
                    similarity_threshold=0.3  # 使用较低的阈值
                )
                print(f"   '{question}': {len(results)} 个结果")
                for i, result in enumerate(results):
                    print(f"     {i+1}. {result['bank_name'][:40]}... -> {result['bank_code']}")
            
            return True
        else:
            print("❌ RAG向量数据库仍然为空")
            return False
    
    except Exception as e:
        print(f"❌ 修复过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()

if __name__ == "__main__":
    success = asyncio.run(fix_rag_database())
    if success:
        print("\n🎉 RAG数据库修复完成！现在可以正常使用智能检索功能了。")
    else:
        print("\n💥 RAG数据库修复失败，请检查错误信息。")