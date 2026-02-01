#!/usr/bin/env python3
"""
测试API事务行为
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def get_auth_token():
    """获取认证令牌"""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        data={"username": "admin", "password": "admin123"}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"登录失败: {response.status_code}")

def test_api_transaction():
    """测试API事务行为"""
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. 获取当前QA pairs数量
    response = requests.get(f"{BASE_URL}/api/v1/qa-pairs/1", headers=headers)
    if response.status_code == 200:
        initial_count = len(response.json())
        print(f"初始QA pairs数量: {initial_count}")
    else:
        print(f"获取QA pairs失败: {response.status_code}")
        return
    
    # 2. 获取第一个QA pair的ID
    qa_pairs = response.json()
    if qa_pairs:
        first_qa_id = qa_pairs[0]["id"]
        print(f"准备删除QA pair ID: {first_qa_id}")
        
        # 3. 删除QA pair
        delete_response = requests.delete(
            f"{BASE_URL}/api/v1/qa-pairs/single/{first_qa_id}",
            headers=headers
        )
        print(f"删除响应状态码: {delete_response.status_code}")
        
        # 4. 立即检查数量
        check_response = requests.get(f"{BASE_URL}/api/v1/qa-pairs/1", headers=headers)
        if check_response.status_code == 200:
            after_count = len(check_response.json())
            print(f"删除后QA pairs数量: {after_count}")
            
            if after_count == initial_count - 1:
                print("✅ 删除成功")
            else:
                print("❌ 删除失败或未生效")
        else:
            print(f"检查失败: {check_response.status_code}")
    else:
        print("没有QA pairs可供测试")

if __name__ == "__main__":
    test_api_transaction()