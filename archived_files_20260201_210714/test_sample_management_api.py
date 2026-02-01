#!/usr/bin/env python3
"""
测试样本管理API
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

def test_datasets_api(token):
    """测试数据集API"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print("🔍 测试数据集API...")
    response = requests.get(f"{BASE_URL}/api/v1/datasets", headers=headers)
    
    if response.status_code == 200:
        datasets = response.json()
        print(f"✅ 数据集API正常，找到 {len(datasets)} 个数据集")
        return datasets
    else:
        print(f"❌ 数据集API失败: {response.text}")
        return []

def test_qa_pairs_api(token):
    """测试QA pairs API"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print("🔍 测试QA pairs API...")
    response = requests.get(f"{BASE_URL}/api/v1/qa-pairs?limit=5", headers=headers)
    
    if response.status_code == 200:
        qa_pairs = response.json()
        print(f"✅ QA pairs API正常，找到 {len(qa_pairs)} 个样本")
        if qa_pairs:
            print("📋 样本示例:")
            sample = qa_pairs[0]
            print(f"  - ID: {sample['id']}")
            print(f"  - 问题: {sample['question'][:50]}...")
            print(f"  - 答案: {sample['answer'][:50]}...")
            print(f"  - 类型: {sample['question_type']}")
            print(f"  - 数据集: {sample['split_type']}")
        return qa_pairs
    else:
        print(f"❌ QA pairs API失败: {response.text}")
        return []

def main():
    print("🚀 开始测试样本管理API...")
    
    # 登录
    token = login()
    if not token:
        return
    
    print("✅ 登录成功")
    
    # 测试数据集API
    datasets = test_datasets_api(token)
    
    # 测试QA pairs API
    qa_pairs = test_qa_pairs_api(token)
    
    print("\n📊 测试总结:")
    print(f"  - 数据集数量: {len(datasets)}")
    print(f"  - 样本数量: {len(qa_pairs)}")
    print("✅ 所有API测试完成")

if __name__ == "__main__":
    main()