#!/usr/bin/env python3
"""
测试查询日志保存修复
"""
import requests
import json
import time
from datetime import datetime

# API 基础URL
BASE_URL = "http://localhost:8000"

def test_query_logging():
    """测试查询日志是否正确保存"""
    
    print("🧪 测试查询日志保存修复...")
    
    # 1. 登录获取token
    print("\n1. 登录获取token...")
    login_data = {
        "username": "testuser",
        "password": "test123"  # 使用正确的密码
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", data=login_data)
    if response.status_code != 200:
        print(f"❌ 登录失败: {response.status_code} - {response.text}")
        return False
    
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ 登录成功")
    
    # 2. 获取当前查询日志数量
    print("\n2. 获取当前查询日志数量...")
    response = requests.get(f"{BASE_URL}/api/v1/query/history?limit=1", headers=headers)
    if response.status_code != 200:
        print(f"❌ 获取查询历史失败: {response.status_code}")
        return False
    
    initial_count = response.json()["total"]
    print(f"✅ 当前查询日志数量: {initial_count}")
    
    # 3. 发送测试查询
    print("\n3. 发送测试查询...")
    test_question = f"华夏银行江油西山支行联行号 - 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    query_data = {
        "question": test_question,
        "use_rag": True
    }
    
    print(f"测试问题: {test_question}")
    response = requests.post(f"{BASE_URL}/api/v1/query/", json=query_data, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ 查询失败: {response.status_code} - {response.text}")
        return False
    
    query_result = response.json()
    print(f"✅ 查询成功")
    print(f"   答案: {query_result['answer'][:100]}...")
    print(f"   响应时间: {query_result['response_time']:.2f}ms")
    print(f"   置信度: {query_result['confidence']:.2f}")
    
    # 4. 等待一下确保日志已保存
    print("\n4. 等待日志保存...")
    time.sleep(2)
    
    # 5. 检查查询日志是否增加
    print("\n5. 检查查询日志是否增加...")
    response = requests.get(f"{BASE_URL}/api/v1/query/history?limit=1", headers=headers)
    if response.status_code != 200:
        print(f"❌ 获取查询历史失败: {response.status_code}")
        return False
    
    final_count = response.json()["total"]
    print(f"✅ 最新查询日志数量: {final_count}")
    
    # 6. 验证日志是否正确保存
    if final_count > initial_count:
        print(f"✅ 查询日志保存成功! 数量从 {initial_count} 增加到 {final_count}")
        
        # 获取最新的查询记录
        response = requests.get(f"{BASE_URL}/api/v1/query/history?limit=1", headers=headers)
        latest_log = response.json()["items"][0]
        
        print(f"   最新记录ID: {latest_log['id']}")
        print(f"   问题: {latest_log['question'][:50]}...")
        print(f"   时间: {latest_log['created_at']}")
        
        return True
    else:
        print(f"❌ 查询日志保存失败! 数量没有增加 (仍为 {final_count})")
        return False

def test_multiple_queries():
    """测试多次查询的日志保存"""
    
    print("\n🧪 测试多次查询的日志保存...")
    
    # 登录
    login_data = {
        "username": "testuser", 
        "password": "test123"  # 使用正确的密码
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", data=login_data)
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 获取初始数量
    response = requests.get(f"{BASE_URL}/api/v1/query/history?limit=1", headers=headers)
    initial_count = response.json()["total"]
    
    # 发送3个测试查询
    test_questions = [
        "工商银行北京分行联行号",
        "建设银行上海分行联行号", 
        "农业银行广州分行联行号"
    ]
    
    print(f"发送 {len(test_questions)} 个测试查询...")
    
    for i, question in enumerate(test_questions, 1):
        query_data = {"question": f"{question} - 批量测试 {i}", "use_rag": True}
        response = requests.post(f"{BASE_URL}/api/v1/query/", json=query_data, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ 查询 {i}: {result['response_time']:.2f}ms")
        else:
            print(f"  ❌ 查询 {i} 失败: {response.status_code}")
    
    # 等待保存
    time.sleep(3)
    
    # 检查最终数量
    response = requests.get(f"{BASE_URL}/api/v1/query/history?limit=1", headers=headers)
    final_count = response.json()["total"]
    
    expected_count = initial_count + len(test_questions)
    
    if final_count >= expected_count:
        print(f"✅ 批量查询日志保存成功! 数量从 {initial_count} 增加到 {final_count}")
        return True
    else:
        print(f"❌ 批量查询日志保存失败! 期望 {expected_count}, 实际 {final_count}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 查询日志保存修复验证测试")
    print("=" * 60)
    
    # 测试单次查询
    success1 = test_query_logging()
    
    # 测试多次查询
    success2 = test_multiple_queries()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("🎉 所有测试通过! 查询日志保存修复成功!")
    else:
        print("❌ 测试失败! 查询日志保存仍有问题!")
    print("=" * 60)