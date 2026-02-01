#!/usr/bin/env python3
"""
测试Redis API修复
"""
import requests
import json

def test_redis_api():
    """测试Redis API"""
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
    
    # 2. 测试Redis健康检查
    print("\n2. 测试Redis健康检查...")
    response = requests.get(f"{base_url}/api/redis/health", headers=headers)
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            print("✅ Redis健康检查成功")
            stats = data.get("stats", {})
            print(f"Redis状态: {data.get('status')}")
            print(f"银行数据总数: {stats.get('total_banks', 0)}")
        else:
            print(f"❌ Redis健康检查失败: {data}")
    else:
        print(f"❌ HTTP错误: {response.text}")

if __name__ == "__main__":
    test_redis_api()