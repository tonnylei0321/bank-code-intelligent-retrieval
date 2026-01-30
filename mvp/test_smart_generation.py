"""
测试智能样本生成器
"""
import sys
sys.path.insert(0, '.')

from app.services.smart_sample_generator import SmartSampleGenerator

def test_rule_based_generation():
    """测试基于规则的生成"""
    print("=" * 60)
    print("测试 1: 基于规则的样本生成")
    print("=" * 60)
    
    generator = SmartSampleGenerator()
    
    # 测试几个银行
    test_banks = [
        {"name": "中国工商银行股份有限公司北京市分行", "code": "102100099996"},
        {"name": "中国建设银行股份有限公司上海市分行", "code": "105290000012"},
        {"name": "汉口银行股份有限公司兴新街支行", "code": "313521001758"},
    ]
    
    for bank in test_banks:
        print(f"\n银行: {bank['name']}")
        print(f"联行号: {bank['code']}")
        print("-" * 60)
        
        samples = generator.generate_samples_rule_based(
            bank["name"],
            bank["code"],
            num_samples=7
        )
        
        print(f"生成了 {len(samples)} 个样本:")
        for i, sample in enumerate(samples, 1):
            print(f"  {i}. 问题: {sample['question']}")
            print(f"     答案: {sample['answer'][:50]}...")
        print()


def test_batch_generation():
    """测试批量生成"""
    print("=" * 60)
    print("测试 2: 批量生成（规则模式）")
    print("=" * 60)
    
    generator = SmartSampleGenerator()
    
    # 测试数据
    bank_records = [
        {"name": "中国工商银行股份有限公司北京市分行", "code": "102100099996"},
        {"name": "中国建设银行股份有限公司上海市分行", "code": "105290000012"},
        {"name": "中国农业银行股份有限公司广州分行", "code": "103581000018"},
        {"name": "中国银行股份有限公司深圳市分行", "code": "104584000013"},
        {"name": "交通银行股份有限公司杭州分行", "code": "301331000018"},
    ]
    
    print(f"\n批量生成 {len(bank_records)} 个银行的训练样本...")
    
    all_samples = generator.batch_generate(
        bank_records,
        samples_per_bank=5,
        batch_size=10
    )
    
    print(f"\n✅ 生成完成!")
    print(f"   总银行数: {len(bank_records)}")
    print(f"   总样本数: {len(all_samples)}")
    print(f"   平均每个银行: {len(all_samples) / len(bank_records):.1f} 个样本")
    
    # 显示一些示例
    print(f"\n前 10 个样本示例:")
    for i, sample in enumerate(all_samples[:10], 1):
        print(f"  {i}. Q: {sample['question']}")
        print(f"     A: {sample['answer'][:60]}...")


def test_file_parsing():
    """测试文件解析"""
    print("=" * 60)
    print("测试 3: .unl 文件解析")
    print("=" * 60)
    
    from app.api.bank_data import parse_unl_file
    
    file_path = "../data/T_BANK_LINE_NO_ICBC_ALL.unl"
    
    print(f"\n解析文件: {file_path}")
    
    try:
        bank_records = parse_unl_file(file_path)
        
        print(f"\n✅ 解析成功!")
        print(f"   总记录数: {len(bank_records)}")
        
        # 显示前 5 条
        print(f"\n前 5 条记录:")
        for i, record in enumerate(bank_records[:5], 1):
            print(f"  {i}. {record['name'][:40]}... -> {record['code']}")
        
        # 测试生成样本
        print(f"\n为前 3 个银行生成样本...")
        generator = SmartSampleGenerator()
        
        samples = generator.batch_generate(
            bank_records[:3],
            samples_per_bank=7
        )
        
        print(f"✅ 生成了 {len(samples)} 个样本")
        
    except FileNotFoundError:
        print(f"❌ 文件不存在: {file_path}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")


if __name__ == "__main__":
    print("\n🧪 智能样本生成器测试\n")
    
    # 运行测试
    test_rule_based_generation()
    print("\n")
    test_batch_generation()
    print("\n")
    test_file_parsing()
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成!")
    print("=" * 60)
