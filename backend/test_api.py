"""
简单的API测试脚本
"""

import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_health():
    """测试健康检查"""
    response = requests.get("http://localhost:8000/health")
    print("健康检查:", response.json())
    return response.status_code == 200

def test_login():
    """测试登录"""
    data = {
        "username": "admin",
        "password": "admin123"
    }
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data=data
    )
    print("登录测试:", response.status_code)
    if response.status_code == 200:
        result = response.json()
        print("Token:", result.get("access_token")[:50] + "...")
        return result.get("access_token")
    return None

def test_get_profile(token):
    """测试获取用户信息"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/users/profile",
        headers=headers
    )
    print("获取用户信息:", response.status_code)
    if response.status_code == 200:
        print("用户信息:", response.json())
    return response.status_code == 200

def test_system_status(token):
    """测试系统状态"""
    response = requests.get(f"{BASE_URL}/system/status")
    print("系统状态:", response.status_code)
    if response.status_code == 200:
        print("状态信息:", response.json())
    return response.status_code == 200

def main():
    print("=" * 50)
    print("开始API测试")
    print("=" * 50)
    
    # 测试健康检查
    print("\n1. 测试健康检查")
    if not test_health():
        print("❌ 健康检查失败")
        return
    print("✅ 健康检查通过")
    
    # 测试登录
    print("\n2. 测试登录")
    token = test_login()
    if not token:
        print("❌ 登录失败")
        return
    print("✅ 登录成功")
    
    # 测试获取用户信息
    print("\n3. 测试获取用户信息")
    if not test_get_profile(token):
        print("❌ 获取用户信息失败")
        return
    print("✅ 获取用户信息成功")
    
    # 测试系统状态
    print("\n4. 测试系统状态")
    if not test_system_status(token):
        print("❌ 获取系统状态失败")
        return
    print("✅ 获取系统状态成功")
    
    print("\n" + "=" * 50)
    print("所有测试通过！")
    print("=" * 50)

if __name__ == "__main__":
    main()