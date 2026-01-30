#!/usr/bin/env python3
"""
测试训练数据生成功能

验证大模型-小模型协同训练方案的可行性
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.training_data_generator import TrainingDataGenerator
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_single_bank_generation():
    """测试单个银行的变体生成"""
    print("🧪 测试单个银行变体生成...")
    
    generator = TrainingDataGenerator()
    
    # 测试用例：华夏银行江油西山支行
    test_bank = {
        "bank_name": "华夏银行股份有限公司江油西山支行",
        "bank_code": "304659715925"
    }
    
    print(f"输入银行: {test_bank['bank_name']}")
    print(f"联行号: {test_bank['bank_code']}")
    print()
    
    # 生成变体
    variations = generator.generate_bank_variations(test_bank)
    
    print(f"✅ 生成了 {len(variations)} 个变体:")
    print()
    
    for i, variation in enumerate(variations, 1):
        print(f"变体 {i}:")
        print(f"  用户输入: {variation['user_input']}")
        print(f"  实体识别: {variation['entities']}")
        print(f"  置信度: {variation.get('confidence', 'N/A')}")
        print()
    
    return variations


def test_small_dataset_generation():
    """测试小规模数据集生成"""
    print("🧪 测试小规模数据集生成...")
    
    generator = TrainingDataGenerator()
    
    # 生成前10个银行的训练数据
    training_data = generator.generate_comprehensive_dataset(limit=10)
    
    print(f"✅ 生成了 {len(training_data)} 个训练样本")
    
    # 显示前几个样本
    print("\n📋 样本预览:")
    for i, sample in enumerate(training_data[:5]):
        print(f"\n样本 {i+1}:")
        print(f"  原始银行: {sample['original_bank']['bank_name']}")
        print(f"  用户输入: {sample['user_input']}")
        print(f"  实体标注: {sample['entities']}")
        print(f"  置信度: {sample['confidence']}")
    
    # 保存测试数据
    generator.save_training_dataset(training_data, "test_bank_ner_data.json")
    
    return training_data


def analyze_generation_quality(variations):
    """分析生成质量"""
    print("📊 生成质量分析:")
    
    if not variations:
        print("❌ 没有生成任何变体")
        return
    
    # 统计置信度分布
    high_conf = sum(1 for v in variations if v.get('confidence', 0) > 0.9)
    med_conf = sum(1 for v in variations if 0.8 <= v.get('confidence', 0) <= 0.9)
    low_conf = sum(1 for v in variations if v.get('confidence', 0) < 0.8)
    
    print(f"  高置信度 (>0.9): {high_conf}")
    print(f"  中置信度 (0.8-0.9): {med_conf}")
    print(f"  低置信度 (<0.8): {low_conf}")
    
    # 检查实体完整性
    complete_entities = sum(1 for v in variations 
                          if v['entities'].get('bank_name') and 
                             v['entities'].get('location') and 
                             v['entities'].get('branch_name'))
    
    print(f"  完整实体标注: {complete_entities}/{len(variations)}")
    
    # 检查表达多样性
    unique_inputs = len(set(v['user_input'] for v in variations))
    print(f"  表达多样性: {unique_inputs}/{len(variations)} (去重后)")


def main():
    """主测试函数"""
    print("🚀 大模型-小模型协同训练方案测试")
    print("=" * 50)
    
    try:
        # 测试1：单个银行变体生成
        variations = test_single_bank_generation()
        analyze_generation_quality(variations)
        
        print("\n" + "=" * 50)
        
        # 测试2：小规模数据集生成
        training_data = test_small_dataset_generation()
        
        print(f"\n🎊 测试完成!")
        print(f"✅ 单银行变体: {len(variations)} 个")
        print(f"✅ 训练样本: {len(training_data)} 个")
        print(f"✅ 数据文件: data/test_bank_ner_data.json")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()