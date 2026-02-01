#!/usr/bin/env python3
"""
测试用户认证
"""

import requests
import json

def test_auth():
    """测试认证"""
    base_url = "http://localhost:8000"
    
    # 测试不同的用户名和密码组合
    test_cases = [
        ("admin", "admin123"),
        ("admin", "admin"),
        ("testuser", "testpass"),
        ("testuser", "password123")
    ]
    
    for username, password in test_cases:
        print(f"🔐 测试登录: {username} / {password}")
        
        login_data = {
            "username": username,
            "password": password
        }
        
        try:
            response = requests.post(
                f"{base_url}/api/v1/auth/login",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            print(f"   状态码: {response.status_code}")
            print(f"   响应: {response.text[:200]}...")
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print(f"   ✅ 登录成功！Token: {result.get('access_token', '')[:50]}...")
                    return result.get('access_token')
                else:
                    print(f"   ❌ 登录失败: {result.get('error_message')}")
            else:
                print(f"   ❌ HTTP错误: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ 请求异常: {e}")
        
        print()
    
    return None

if __name__ == "__main__":
    token = test_auth()
    if token:
        print(f"🎉 获取到有效token: {token[:50]}...")
    else:
        print("❌ 所有登录尝试都失败了")