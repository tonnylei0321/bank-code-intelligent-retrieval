#!/usr/bin/env python3
"""
RAG配置功能测试脚本

测试RAG服务的配置管理功能，包括：
1. 默认配置获取
2. 配置参数更新
3. 配置参数验证
4. 配置重置功能
"""

import sys
sys.path.append('.')

from app.services.rag_service import RAGService
from app.core.database import get_db
from app.api.rag import RAGConfigRequest
from pydantic import ValidationError


def test_rag_config():
    """测试RAG配置功能"""
    print("=" * 60)
    print("RAG配置功能测试")
    print("=" * 60)
    
    # 初始化RAG服务
    print("\n1. 初始化RAG服务...")
    db = next(get_db())
    rag_service = RAGService(db)
    print("✓ RAG服务初始化成功")
    
    # 测试默认配置
    print("\n2. 测试默认配置...")
    default_config = rag_service.get_config()
    print(f"✓ 默认配置包含 {len(default_config)} 个参数")
    print("主要参数:")
    for key in ['top_k', 'similarity_threshold', 'temperature', 'enable_hybrid']:
        print(f"  - {key}: {default_config.get(key)}")
    
    # 测试配置更新
    print("\n3. 测试配置更新...")
    test_updates = {
        'top_k': 8,
        'similarity_threshold': 0.4,
        'temperature': 0.2,
        'enable_hybrid': False
    }
    
    success = rag_service.update_config(test_updates)
    if success:
        print("✓ 配置更新成功")
        updated_config = rag_service.get_config()
        for key, expected_value in test_updates.items():
            actual_value = updated_config.get(key)
            if actual_value == expected_value:
                print(f"  ✓ {key}: {actual_value}")
            else:
                print(f"  ✗ {key}: 期望 {expected_value}, 实际 {actual_value}")
    else:
        print("✗ 配置更新失败")
    
    # 测试配置验证
    print("\n4. 测试配置验证...")
    
    # 测试有效配置
    valid_config = {
        'top_k': 10,
        'similarity_threshold': 0.5,
        'temperature': 0.1
    }
    
    try:
        request = RAGConfigRequest(**valid_config)
        print("✓ 有效配置验证通过")
    except ValidationError as e:
        print(f"✗ 有效配置验证失败: {e}")
    
    # 测试无效配置
    invalid_configs = [
        {'top_k': 100},  # 超出范围
        {'similarity_threshold': 1.5},  # 超出范围
        {'temperature': -0.1},  # 负值
        {'instruction': 'short'},  # 太短
    ]
    
    for i, invalid_config in enumerate(invalid_configs, 1):
        try:
            request = RAGConfigRequest(**invalid_config)
            print(f"✗ 无效配置 {i} 应该被拒绝: {invalid_config}")
        except ValidationError:
            print(f"✓ 无效配置 {i} 正确被拒绝: {invalid_config}")
    
    # 测试配置重置
    print("\n5. 测试配置重置...")
    original_defaults = rag_service._get_default_config()
    reset_success = rag_service.update_config(original_defaults)
    
    if reset_success:
        print("✓ 配置重置成功")
        reset_config = rag_service.get_config()
        
        # 验证几个关键参数是否恢复默认值
        key_params = ['top_k', 'similarity_threshold', 'temperature']
        all_reset = True
        for key in key_params:
            if reset_config.get(key) == original_defaults.get(key):
                print(f"  ✓ {key}: {reset_config.get(key)}")
            else:
                print(f"  ✗ {key}: 期望 {original_defaults.get(key)}, 实际 {reset_config.get(key)}")
                all_reset = False
        
        if all_reset:
            print("✓ 所有参数已重置为默认值")
        else:
            print("✗ 部分参数未正确重置")
    else:
        print("✗ 配置重置失败")
    
    print("\n" + "=" * 60)
    print("RAG配置功能测试完成")
    print("=" * 60)


def test_config_edge_cases():
    """测试配置边界情况"""
    print("\n" + "=" * 60)
    print("RAG配置边界情况测试")
    print("=" * 60)
    
    db = next(get_db())
    rag_service = RAGService(db)
    
    # 测试权重和必须为1的约束
    print("\n1. 测试权重约束...")
    
    # 权重和不为1的情况
    invalid_weights = {
        'vector_weight': 0.7,
        'keyword_weight': 0.4  # 和为1.1
    }
    
    try:
        success = rag_service.update_config(invalid_weights)
        if success:
            print("✗ 权重和不为1的配置应该被拒绝")
        else:
            print("✓ 权重和不为1的配置正确被拒绝")
    except Exception as e:
        print(f"✓ 权重约束验证正常: {e}")
    
    # 权重和为1的情况
    valid_weights = {
        'vector_weight': 0.6,
        'keyword_weight': 0.4  # 和为1.0
    }
    
    success = rag_service.update_config(valid_weights)
    if success:
        print("✓ 权重和为1的配置更新成功")
    else:
        print("✗ 权重和为1的配置更新失败")
    
    # 测试边界值
    print("\n2. 测试边界值...")
    boundary_tests = [
        {'top_k': 1, 'expected': True},  # 最小值
        {'top_k': 50, 'expected': True},  # 最大值
        {'similarity_threshold': 0.0, 'expected': True},  # 最小值
        {'similarity_threshold': 1.0, 'expected': True},  # 最大值
        {'temperature': 0.0, 'expected': True},  # 最小值
        {'temperature': 2.0, 'expected': True},  # 最大值
    ]
    
    for test_case in boundary_tests:
        config = {k: v for k, v in test_case.items() if k != 'expected'}
        expected = test_case['expected']
        
        success = rag_service.update_config(config)
        if success == expected:
            print(f"✓ 边界值测试通过: {config}")
        else:
            print(f"✗ 边界值测试失败: {config}, 期望 {expected}, 实际 {success}")
    
    print("\n" + "=" * 60)
    print("边界情况测试完成")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_rag_config()
        test_config_edge_cases()
        print("\n🎉 所有测试完成！")
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()