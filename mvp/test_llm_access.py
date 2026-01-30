#!/usr/bin/env python3
"""
测试LLM模型访问
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.smart_sample_generator import SmartSampleGenerator

def test_llm_access():
    """测试LLM模型是否可以正常访问"""
    print("🧪 测试LLM模型访问...")
    
    try:
        # 初始化生成器（使用1.5B模型）
        print("1. 初始化SmartSampleGenerator...")
        generator = SmartSampleGenerator()
        print(f"   ✅ 初始化成功 - 模型: {generator.llm_model}, 设备: {generator.device}")
        
        # 尝试加载模型
        print("2. 尝试加载LLM模型...")
        generator.load_model()
        
        if generator.model is not None:
            print("   ✅ LLM模型加载成功！")
            
            # 测试生成功能
            print("3. 测试样本生成...")
            test_bank_name = "中国工商银行股份有限公司北京市分行"
            test_bank_code = "102100099996"
            
            samples = generator.generate_samples_for_bank(
                test_bank_name, 
                test_bank_code, 
                num_samples=3
            )
            
            print(f"   ✅ 生成成功！共生成 {len(samples)} 个样本:")
            for i, sample in enumerate(samples, 1):
                print(f"      {i}. {sample['question']}")
            
            # 卸载模型
            generator.unload_model()
            print("   ✅ 模型已卸载")
            
        else:
            print("   ⚠️  LLM模型未加载，使用规则生成")
            
            # 测试规则生成
            print("3. 测试规则生成...")
            test_bank_name = "中国工商银行股份有限公司北京市分行"
            test_bank_code = "102100099996"
            
            samples = generator.generate_samples_rule_based(
                test_bank_name, 
                test_bank_code, 
                num_samples=3
            )
            
            print(f"   ✅ 规则生成成功！共生成 {len(samples)} 个样本:")
            for i, sample in enumerate(samples, 1):
                print(f"      {i}. {sample['question']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 LLM模型访问测试")
    print("=" * 60)
    
    success = test_llm_access()
    
    print("=" * 60)
    if success:
        print("✅ 测试完成")
    else:
        print("❌ 测试失败")
    print("=" * 60)