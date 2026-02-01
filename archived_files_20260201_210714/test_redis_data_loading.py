#!/usr/bin/env python3
"""
测试Redis数据加载功能
"""
import requests
import json

def test_redis_data_loading():
    """测试Redis数据加载功能"""
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
    
    # 2. 检查Redis状态
    print("\n2. 检查Redis状态...")
    response = requests.get(f"{base_url}/api/redis/health", headers=headers)
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        stats = data.get("stats", {})
        print(f"Redis状态: {data.get('status')}")
        print(f"总银行数: {stats.get('total_banks', 0)}")
        print(f"内存使用: {stats.get('memory_usage', 'Unknown')}")
    
    # 3. 加载银行数据到Redis
    print("\n3. 加载银行数据到Redis...")
    response = requests.post(f"{base_url}/api/redis/load-data", headers=headers)
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.text}")
    
    # 4. 再次检查Redis状态
    print("\n4. 再次检查Redis状态...")
    response = requests.get(f"{base_url}/api/redis/health", headers=headers)
    if response.status_code == 200:
        data = response.json()
        stats = data.get("stats", {})
        print(f"Redis状态: {data.get('status')}")
        print(f"总银行数: {stats.get('total_banks', 0)}")
        print(f"内存使用: {stats.get('memory_usage', 'Unknown')}")
    
    # 5. 测试搜索功能
    print("\n5. 测试搜索功能...")
    search_params = {
        "query": "工商银行",
        "limit": 5
    }
    response = requests.get(f"{base_url}/api/redis/search", headers=headers, params=search_params)
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        results = data.get("data", {}).get("results", [])
        print(f"搜索结果数量: {len(results)}")
        for i, result in enumerate(results[:3]):
            print(f"  {i+1}. {result.get('bank_name', 'Unknown')} - {result.get('bank_code', 'Unknown')}")

if __name__ == "__main__":
    test_redis_data_loading()