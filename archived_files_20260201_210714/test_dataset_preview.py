#!/usr/bin/env python3
"""
测试数据集预览功能
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

def test_dataset_list(token):
    """测试数据集列表"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/v1/datasets", headers=headers)
    
    if response.status_code == 200:
        datasets = response.json()
        print(f"✅ 数据集列表获取成功，共 {len(datasets)} 个数据集")
        for dataset in datasets:
            print(f"  - ID: {dataset['id']}, 文件名: {dataset['filename']}, 记录数: {dataset['total_records']}")
        return datasets
    else:
        print(f"❌ 数据集列表获取失败: {response.text}")
        return []

def test_dataset_preview(token, dataset_id):
    """测试数据集预览"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/v1/datasets/{dataset_id}/preview", headers=headers)
    
    if response.status_code == 200:
        preview_data = response.json()
        print(f"✅ 数据集 {dataset_id} 预览成功，返回 {len(preview_data)} 条记录")
        
        # 显示前5条记录
        print("前5条记录:")
        for i, record in enumerate(preview_data[:5]):
            print(f"  {i+1}. 银行名称: {record['bank_name']}")
            print(f"     银行联行号: {record['bank_code']}")
            print(f"     清算行行号: {record['clearing_code']}")
            print()
        
        return preview_data
    else:
        print(f"❌ 数据集 {dataset_id} 预览失败: {response.text}")
        return []

def main():
    print("🔍 测试数据集预览功能")
    print("=" * 50)
    
    # 获取认证token
    print("1. 获取认证token...")
    token = get_auth_token()
    if not token:
        return
    print("✅ 认证成功")
    
    # 获取数据集列表
    print("\n2. 获取数据集列表...")
    datasets = test_dataset_list(token)
    if not datasets:
        return
    
    # 测试预览功能
    print("\n3. 测试数据集预览功能...")
    for dataset in datasets:
        dataset_id = dataset['id']
        print(f"\n测试数据集 {dataset_id} ({dataset['filename']}):")
        preview_data = test_dataset_preview(token, dataset_id)
        
        if preview_data:
            print(f"✅ 预览功能正常，数据格式正确")
            
            # 验证数据结构
            required_fields = ['bank_name', 'bank_code', 'clearing_code']
            first_record = preview_data[0]
            missing_fields = [field for field in required_fields if field not in first_record]
            
            if missing_fields:
                print(f"⚠️  缺少字段: {missing_fields}")
            else:
                print("✅ 数据结构完整")
        else:
            print("❌ 预览功能异常")
    
    print("\n" + "=" * 50)
    print("🎉 测试完成")

if __name__ == "__main__":
    main()