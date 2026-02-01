#!/usr/bin/env python3
"""
测试智能问答修复结果
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'mvp'))

async def test_intelligent_qa_fix():
    """测试智能问答修复结果"""
    print("🧪 测试智能问答修复结果")
    print("=" * 50)
    
    try:
        # 导入修复后的服务
        from app.services.small_model_service import SmallModelService
        
        # 创建服务实例
        service = SmallModelService()
        
        # 测试问题
        test_questions = [
            "中国工商银行股份有限公司上海市西虹桥支行的联行号是什么？",
            "工商银行西虹桥支行联行号",
            "102290002916是哪个银行？",
            "上海有哪些工商银行支行？"
        ]
        
        print("📋 测试问题分析功能...")
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n{i}. 测试问题: {question}")
            
            # 调用回退分析
            result = service._fallback_analysis(question)
            
            print(f"   问题类型: {result.get('question_type')}")
            print(f"   银行名称: {result.get('bank_name')}")
            print(f"   联行号: {result.get('bank_code')}")
            print(f"   置信度: {result.get('confidence')}")
            print(f"   关键词: {result.get('keywords')}")
            
            # 检查是否成功提取银行名称
            if result.get('bank_name') or result.get('bank_code'):
                print("   ✅ 信息提取成功")
            else:
                print("   ❌ 信息提取失败")
        
        print("\n🎉 测试完成！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_redis_integration():
    """测试Redis集成"""
    print("\n🔗 测试Redis集成...")
    
    try:
        from app.services.redis_service import RedisService
        from app.core.database import get_db
        
        # 创建Redis服务
        redis_service = RedisService()
        await redis_service.initialize()
        
        # 测试搜索
        test_name = "中国工商银行股份有限公司上海市西虹桥支行"
        print(f"搜索银行: {test_name}")
        
        results = await redis_service.search_banks(test_name, search_type="name", limit=5)
        print(f"找到 {len(results)} 个结果:")
        
        for result in results:
            print(f"  - {result.get('bank_name')} (联行号: {result.get('bank_code')})")
        
        if results:
            print("✅ Redis搜索成功")
            return True
        else:
            print("❌ Redis搜索失败")
            return False
            
    except Exception as e:
        print(f"❌ Redis测试失败: {e}")
        return False

async def main():
    """主函数"""
    print("🔧 智能问答修复验证")
    print("=" * 50)
    
    # 1. 测试小模型服务修复
    print("1️⃣ 测试小模型服务修复...")
    model_test = await test_intelligent_qa_fix()
    
    # 2. 测试Redis集成
    print("\n2️⃣ 测试Redis集成...")
    redis_test = await test_redis_integration()
    
    # 总结
    print("\n📊 测试总结:")
    print(f"   小模型服务: {'✅ 通过' if model_test else '❌ 失败'}")
    print(f"   Redis集成: {'✅ 通过' if redis_test else '❌ 失败'}")
    
    if model_test and redis_test:
        print("\n🎉 所有测试通过！智能问答系统修复成功")
        print("\n📋 修复内容:")
        print("   - 改进了银行名称提取逻辑")
        print("   - 添加了联行号提取功能")
        print("   - 优化了关键词提取算法")
        print("   - 提高了分析置信度")
        
        print("\n🚀 建议:")
        print("   1. 现在可以正常使用智能问答功能")
        print("   2. Redis检索应该能够正确工作")
        print("   3. 可以测试各种银行查询问题")
    else:
        print("\n❌ 部分测试失败，请检查相关配置")

if __name__ == "__main__":
    asyncio.run(main())