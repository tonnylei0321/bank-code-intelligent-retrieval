#!/usr/bin/env python3
"""
测试前端登录功能
"""
import requests
import json

def test_frontend_login():
    """测试前端登录功能"""
    base_url = "http://localhost:8000"
    
    print("🔐 测试前端登录功能")
    print("=" * 50)
    
    # 1. 测试登录API
    print("1. 测试登录API...")
    login_data = {
        "username": "admin",
        "password": "admin123456"
    }
    
    response = requests.post(
        f"{base_url}/api/v1/auth/login",
        data=login_data
    )
    
    print(f"   状态码: {response.status_code}")
    
    if response.status_code == 200:
        token_data = response.json()
        print("   ✅ 登录成功")
        print(f"   令牌类型: {token_data.get('token_type', 'unknown')}")
        print(f"   令牌长度: {len(token_data.get('access_token', ''))}")
        
        # 2. 测试用户信息获取
        print("\n2. 测试用户信息获取...")
        headers = {
            "Authorization": f"Bearer {token_data['access_token']}"
        }
        
        response = requests.get(f"{base_url}/api/v1/auth/me", headers=headers)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 200:
            user_data = response.json()
            print("   ✅ 用户信息获取成功")
            print(f"   用户名: {user_data.get('username', 'unknown')}")
            print(f"   角色: {user_data.get('role', 'unknown')}")
            print(f"   邮箱: {user_data.get('email', 'unknown')}")
        else:
            print(f"   ❌ 用户信息获取失败: {response.text}")
        
        # 3. 测试智能问答API访问
        print("\n3. 测试智能问答API访问...")
        response = requests.get(f"{base_url}/api/intelligent-qa/models", headers=headers)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 200:
            models_data = response.json()
            print("   ✅ 智能问答API访问成功")
            print(f"   可用模型数: {models_data.get('data', {}).get('total_count', 0)}")
        else:
            print(f"   ❌ 智能问答API访问失败: {response.text}")
        
        # 4. 测试Redis管理API访问
        print("\n4. 测试Redis管理API访问...")
        response = requests.get(f"{base_url}/api/redis/health", headers=headers)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 200:
            redis_data = response.json()
            print("   ✅ Redis管理API访问成功")
            print(f"   Redis状态: {redis_data.get('status', 'unknown')}")
            stats = redis_data.get('stats', {})
            print(f"   银行数据总数: {stats.get('total_banks', 0)}")
        else:
            print(f"   ❌ Redis管理API访问失败: {response.text}")
            
    else:
        print(f"   ❌ 登录失败: {response.text}")
    
    # 5. 测试前端页面访问
    print("\n5. 测试前端页面访问...")
    try:
        response = requests.get("http://localhost:3000", timeout=5)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ 前端页面访问成功")
            if "银行代码检索系统" in response.text:
                print("   ✅ 页面标题正确")
            else:
                print("   ⚠️  页面标题可能有问题")
        else:
            print(f"   ❌ 前端页面访问失败")
    except Exception as e:
        print(f"   ❌ 前端页面访问异常: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 测试完成！")
    print("\n📋 使用说明:")
    print("1. 前端地址: http://localhost:3000")
    print("2. 后端API: http://localhost:8000")
    print("3. API文档: http://localhost:8000/docs")
    print("4. 管理员账号: admin / admin123456")
    print("5. 普通用户: testuser / test123456")

if __name__ == "__main__":
    test_frontend_login()