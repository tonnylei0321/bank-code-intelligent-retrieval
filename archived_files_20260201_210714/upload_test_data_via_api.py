#!/usr/bin/env python3
"""
通过API上传测试数据

使用API接口上传测试银行数据
"""

import requests
import os

BASE_URL = "http://localhost:8000"

def upload_test_data():
    print("📤 通过API上传测试银行数据...")
    
    # 1. 登录
    print("1. 登录...")
    login_response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        data={"username": "admin", "password": "admin123"}
    )
    
    if login_response.status_code != 200:
        print(f"❌ 登录失败: {login_response.status_code}")
        return
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ 登录成功")
    
    # 2. 上传测试文件
    print("2. 上传测试文件...")
    test_file = "test_banks_100.unl"
    
    if not os.path.exists(test_file):
        print(f"❌ 测试文件不存在: {test_file}")
        return
    
    with open(test_file, 'rb') as f:
        files = {'file': (test_file, f, 'application/octet-stream')}
        data = {
            'samples_per_bank': '7',
            'use_llm': 'false'  # 使用规则生成，不使用LLM
        }
        
        upload_response = requests.post(
            f"{BASE_URL}/api/v1/bank-data/upload-and-generate",
            headers=headers,
            files=files,
            data=data
        )
    
    print(f"上传响应状态: {upload_response.status_code}")
    
    if upload_response.status_code == 200:
        result = upload_response.json()
        print("✅ 数据上传成功!")
        print(f"   处理银行数: {result.get('total_banks', 0)}")
        print(f"   生成样本数: {result.get('total_samples', 0)}")
        print(f"   数据集ID: {result.get('dataset_id', 0)}")
    else:
        print(f"❌ 上传失败: {upload_response.status_code}")
        print(f"   错误: {upload_response.text}")
    
    print("\n🎯 现在可以测试并行生成功能了!")

if __name__ == "__main__":
    upload_test_data()