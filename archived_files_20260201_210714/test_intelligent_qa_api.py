#!/usr/bin/env python3
"""
测试智能问答API
"""
import requests
import json

def test_intelligent_qa_api():
    """测试智能问答API"""
    base_url = "http://localhost:8000"
    
    # 1. 登录获取令牌
    print("1. 登录获取令牌...")
    login_data = {
        "username": "admin",
        "password": "admin123456"
    }
    
    response = requests.post(
        f"{base_url}/api/v1/auth/login",
        data=login_data
    )
    
    if response.status_code != 200:
        print(f"❌ 登录失败: {response.text}")
        return
    
    token = response.json()["access_token"]
    print("✅ 登录成功")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 2. 测试获取可用模型
    print("\n2. 测试获取可用模型...")
    response = requests.get(f"{base_url}/api/intelligent-qa/models", headers=headers)
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.text}")
    
    # 3. 测试Redis状态
    print("\n3. 测试Redis状态...")
    response = requests.get(f"{base_url}/api/redis/health", headers=headers)
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.text}")
    
    # 4. 测试智能问答
    print("\n4. 测试智能问答...")
    qa_data = {
        "question": "什么是中国工商银行？",
        "model_name": "gpt-3.5-turbo",
        "strategy": "intelligent"
    }
    
    response = requests.post(
        f"{base_url}/api/intelligent-qa/ask",
        headers=headers,
        json=qa_data
    )
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.text}")

if __name__ == "__main__":
    test_intelligent_qa_api()