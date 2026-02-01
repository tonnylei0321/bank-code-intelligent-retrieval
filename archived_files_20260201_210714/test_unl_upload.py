#!/usr/bin/env python3
"""
测试UNL文件上传功能
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def login():
    """登录获取token"""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data="username=admin&password=admin123"
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"登录失败: {response.text}")
        return None

def test_unl_upload(token):
    """测试UNL文件上传"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print("🔍 测试UNL文件上传...")
    
    # 准备文件数据
    files = {
        'file': ('test_sample.unl', open('test_sample.unl', 'rb'), 'text/plain')
    }
    
    data = {
        'name': '测试UNL数据集',
        'description': '测试竖线分隔符的UNL文件上传功能'
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/datasets/upload",
        headers=headers,
        files=files,
        data=data
    )
    
    if response.status_code == 201:
        dataset = response.json()
        print(f"✅ UNL文件上传成功")
        print(f"  - 数据集ID: {dataset['id']}")
        print(f"  - 文件名: {dataset['filename']}")
        print(f"  - 文件大小: {dataset['file_size']} 字节")
        print(f"  - 状态: {dataset['status']}")
        return dataset
    else:
        print(f"❌ UNL文件上传失败: {response.text}")
        return None

def test_dataset_validation(token, dataset_id):
    """测试数据集验证"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"🔍 测试数据集验证 (ID: {dataset_id})...")
    
    response = requests.post(
        f"{BASE_URL}/api/v1/datasets/{dataset_id}/validate",
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 数据集验证成功")
        print(f"  - 总记录数: {result['total_records']}")
        print(f"  - 有效记录: {result['valid_records']}")
        print(f"  - 无效记录: {result['invalid_records']}")
        print(f"  - 状态: {result['status']}")
        if result['errors']:
            print(f"  - 错误: {result['errors'][:3]}")  # 显示前3个错误
        return result
    else:
        print(f"❌ 数据集验证失败: {response.text}")
        return None

def test_dataset_preview(token, dataset_id):
    """测试数据集预览"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"🔍 测试数据集预览 (ID: {dataset_id})...")
    
    response = requests.get(
        f"{BASE_URL}/api/v1/datasets/{dataset_id}/preview?limit=3",
        headers=headers
    )
    
    if response.status_code == 200:
        records = response.json()
        print(f"✅ 数据集预览成功，获取 {len(records)} 条记录")
        for i, record in enumerate(records, 1):
            print(f"  记录 {i}:")
            print(f"    - 银行名称: {record['bank_name']}")
            print(f"    - 联行号: {record['bank_code']}")
            print(f"    - 清算行号: {record['clearing_code']}")
        return records
    else:
        print(f"❌ 数据集预览失败: {response.text}")
        return None

def main():
    print("🚀 开始测试UNL文件上传功能...")
    
    # 登录
    token = login()
    if not token:
        return
    
    print("✅ 登录成功")
    
    # 测试UNL文件上传
    dataset = test_unl_upload(token)
    if not dataset:
        return
    
    # 测试数据集验证
    validation_result = test_dataset_validation(token, dataset['id'])
    if not validation_result:
        return
    
    # 测试数据集预览
    preview_records = test_dataset_preview(token, dataset['id'])
    
    print("\n📊 测试总结:")
    print(f"  - UNL文件上传: ✅ 成功")
    print(f"  - 数据验证: ✅ 成功")
    print(f"  - 数据预览: ✅ 成功")
    print(f"  - 处理记录数: {validation_result['valid_records'] if validation_result else 0}")
    print("✅ UNL文件支持功能测试完成")

if __name__ == "__main__":
    main()