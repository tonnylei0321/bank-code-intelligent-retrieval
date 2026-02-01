#!/usr/bin/env python3
"""
测试回退分析功能
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.services.small_model_service import SmallModelService

def test_fallback_analysis():
    """测试回退分析功能"""
    print("🧪 测试回退分析功能")
    print("=" * 50)
    
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

if __name__ == "__main__":
    test_fallback_analysis()