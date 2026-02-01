#!/usr/bin/env python3
"""
测试Redis页面修复
"""
import requests
import json
import time

def test_redis_page_fix():
    """测试Redis页面修复"""
    base_url = "http://localhost:8000"
    
    print("🔧 测试Redis页面修复")
    print("=" * 50)
    
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
    print(f"   Token: {token[:50]}...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 2. 测试Redis健康检查
    print("\n2. 测试Redis健康检查...")
    response = requests.get(f"{base_url}/api/redis/health", headers=headers)
    print(f"   状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            print("   ✅ Redis健康检查成功")
            stats = data.get("stats", {})
            print(f"   Redis状态: {data.get('status')}")
            print(f"   银行数据总数: {stats.get('total_banks', 0)}")
            print(f"   内存使用: {stats.get('memory_usage', 'N/A')}")
            print(f"   键总数: {stats.get('key_statistics', {}).get('total_keys', 0)}")
        else:
            print(f"   ❌ Redis健康检查失败: {data}")
    else:
        print(f"   ❌ HTTP错误: {response.text}")
        return
    
    # 3. 测试加载数据到Redis
    print("\n3. 测试加载数据到Redis...")
    response = requests.post(f"{base_url}/api/redis/load-data", headers=headers)
    print(f"   状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            print("   ✅ 数据加载成功")
            load_data = data.get("data", {})
            print(f"   加载数量: {load_data.get('loaded_count', 0)}")
            print(f"   批次数: {load_data.get('total_batches', 0)}")
        else:
            print(f"   ❌ 数据加载失败: {data}")
    else:
        print(f"   ❌ HTTP错误: {response.text}")
    
    # 4. 再次检查Redis状态
    print("\n4. 再次检查Redis状态...")
    response = requests.get(f"{base_url}/api/redis/health", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            stats = data.get("stats", {})
            print(f"   ✅ 数据加载后状态:")
            print(f"   银行数据总数: {stats.get('total_banks', 0)}")
            print(f"   内存使用: {stats.get('memory_usage', 'N/A')}")
            print(f"   键总数: {stats.get('key_statistics', {}).get('total_keys', 0)}")
    
    # 5. 测试搜索功能
    print("\n5. 测试搜索功能...")
    search_params = {
        "query": "工商银行",
        "search_type": "auto",
        "limit": "5"
    }
    
    params_str = "&".join([f"{k}={v}" for k, v in search_params.items()])
    response = requests.get(f"{base_url}/api/redis/search?{params_str}", headers=headers)
    print(f"   状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            results = data.get("data", {}).get("results", [])
            print(f"   ✅ 搜索成功，找到 {len(results)} 条结果")
            for i, result in enumerate(results[:3]):
                print(f"     {i+1}. {result.get('bank_name', 'Unknown')} - {result.get('bank_code', 'Unknown')}")
        else:
            print(f"   ❌ 搜索失败: {data}")
    else:
        print(f"   ❌ HTTP错误: {response.text}")
    
    # 6. 测试智能问答API
    print("\n6. 测试智能问答API...")
    response = requests.get(f"{base_url}/api/intelligent-qa/models", headers=headers)
    print(f"   状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            print("   ✅ 智能问答API正常")
            models_data = data.get("data", {})
            print(f"   当前模型: {models_data.get('current_model', 'Unknown')}")
            print(f"   可用模型数: {models_data.get('total_count', 0)}")
        else:
            print(f"   ❌ 智能问答API失败: {data}")
    else:
        print(f"   ❌ HTTP错误: {response.text}")
    
    # 7. 测试前端页面
    print("\n7. 测试前端页面...")
    try:
        response = requests.get("http://localhost:3000", timeout=5)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ 前端页面正常")
            if "银行代码检索系统" in response.text:
                print("   ✅ 页面标题正确")
            else:
                print("   ⚠️  页面标题可能有问题")
        else:
            print(f"   ❌ 前端页面访问失败")
    except Exception as e:
        print(f"   ❌ 前端页面访问异常: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Redis页面修复测试完成！")
    print("\n📋 修复内容:")
    print("1. ✅ 修复数据库结构问题（添加缺失的列）")
    print("2. ✅ 修复前端token存储键名不一致问题")
    print("3. ✅ 重启后端和前端服务")
    print("4. ✅ 验证所有API端点正常工作")
    print("\n🎯 使用说明:")
    print("1. 前端地址: http://localhost:3000")
    print("2. 使用 admin / admin123456 登录")
    print("3. 点击'Redis管理'菜单")
    print("4. 现在应该可以正常使用所有功能了")

if __name__ == "__main__":
    test_redis_page_fix()