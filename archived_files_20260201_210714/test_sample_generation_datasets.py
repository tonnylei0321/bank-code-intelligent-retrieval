#!/usr/bin/env python3
"""
测试样本生成页面的数据集下拉列表
"""
import requests
import json

# 配置
BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"

def get_auth_token():
    """获取认证token"""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        data={"username": USERNAME, "password": PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"登录失败: {response.text}")
        return None

def test_datasets_api(token):
    """测试数据集API"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/v1/datasets", headers=headers)
    
    if response.status_code == 200:
        datasets = response.json()
        print(f"✅ 数据集API正常，返回 {len(datasets)} 个数据集")
        
        for dataset in datasets:
            print(f"数据集详情:")
            print(f"  - ID: {dataset['id']}")
            print(f"  - 文件名: {dataset['filename']}")
            print(f"  - 总记录数: {dataset['total_records']}")
            print(f"  - 状态: {dataset['status']}")
            print(f"  - 创建时间: {dataset['created_at']}")
            print()
        
        return datasets
    else:
        print(f"❌ 数据集API失败: {response.text}")
        return []

def test_sample_generation_strategies(token):
    """测试样本生成策略API"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/sample-generation/strategies", headers=headers)
    
    if response.status_code == 200:
        strategies = response.json()
        print(f"✅ 样本生成策略API正常")
        print(f"  - 选择策略: {len(strategies.get('selection_strategies', []))} 个")
        print(f"  - 记录数策略: {len(strategies.get('record_count_strategies', []))} 个")
        print(f"  - LLM策略: {len(strategies.get('llm_strategies', []))} 个")
        return strategies
    else:
        print(f"❌ 样本生成策略API失败: {response.text}")
        return {}

def simulate_frontend_data_flow(datasets):
    """模拟前端数据流"""
    print("🔄 模拟前端数据流:")
    
    if not datasets:
        print("❌ 没有数据集，下拉列表将为空")
        return
    
    print("✅ 前端下拉列表应该显示:")
    for dataset in datasets:
        option_text = f"{dataset['filename']} ({dataset['total_records'] or 0} 条记录)"
        print(f"  - Option: {option_text} (value: {dataset['id']})")

def main():
    print("🔍 测试样本生成页面数据集下拉列表")
    print("=" * 60)
    
    # 获取认证token
    print("1. 获取认证token...")
    token = get_auth_token()
    if not token:
        return
    print("✅ 认证成功")
    
    # 测试数据集API
    print("\n2. 测试数据集API...")
    datasets = test_datasets_api(token)
    
    # 测试样本生成策略API
    print("\n3. 测试样本生成策略API...")
    strategies = test_sample_generation_strategies(token)
    
    # 模拟前端数据流
    print("\n4. 模拟前端数据流...")
    simulate_frontend_data_flow(datasets)
    
    # 检查数据完整性
    print("\n5. 数据完整性检查...")
    if datasets:
        dataset = datasets[0]
        required_fields = ['id', 'filename', 'total_records', 'status']
        missing_fields = [field for field in required_fields if field not in dataset]
        
        if missing_fields:
            print(f"⚠️  数据集缺少字段: {missing_fields}")
        else:
            print("✅ 数据集字段完整")
            
        # 检查记录数
        if dataset['total_records'] == 0:
            print("⚠️  数据集记录数为0，可能需要验证数据")
        else:
            print(f"✅ 数据集有 {dataset['total_records']} 条记录")
    
    print("\n" + "=" * 60)
    print("🎉 测试完成")

if __name__ == "__main__":
    main()