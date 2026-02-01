#!/usr/bin/env python3
"""
测试西单支行查询问题
分析为什么"中国工商银行股份有限公司北京西单支行"检索不到结果
"""

import requests
import json
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_xidan_query():
    """测试西单支行查询"""
    
    base_url = "http://localhost:8000"
    
    # 1. 登录获取token
    print("1. 登录获取token...")
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(f"{base_url}/api/v1/auth/login", data=login_data)
        if response.status_code != 200:
            print(f"登录失败: {response.status_code} - {response.text}")
            return False
        
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ 登录成功")
        
    except Exception as e:
        print(f"❌ 登录失败: {e}")
        return False
    
    # 2. 测试完整查询
    print("\n2. 测试完整查询：中国工商银行股份有限公司北京西单支行")
    test_query = {
        "question": "中国工商银行股份有限公司北京西单支行",
        "top_k": 10,
        "similarity_threshold": 0.1  # 降低阈值看看有没有结果
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/rag/search", 
            headers={**headers, "Content-Type": "application/json"},
            json=test_query
        )
        
        if response.status_code != 200:
            print(f"❌ 查询失败: {response.status_code} - {response.text}")
            return False
        
        result = response.json()
        print(f"✅ 查询成功")
        print(f"   找到结果数: {result['total_found']}")
        print(f"   搜索耗时: {result['search_time_ms']:.2f}ms")
        
        if result['results']:
            print("\n   前5个结果:")
            for i, res in enumerate(result['results'][:5]):
                print(f"   {i+1}. {res['bank_name']}")
                print(f"      联行号: {res['bank_code']}")
                print(f"      相似度: {res.get('similarity_score', 'N/A')}")
                print(f"      关键词分数: {res.get('keyword_score', 'N/A')}")
                print(f"      最终分数: {res.get('final_score', 'N/A')}")
                print()
        else:
            print("   ❌ 没有找到任何结果")
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        return False
    
    # 3. 测试简化查询
    print("\n3. 测试简化查询：工商银行西单")
    test_query = {
        "question": "工商银行西单",
        "top_k": 10,
        "similarity_threshold": 0.1
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/rag/search", 
            headers={**headers, "Content-Type": "application/json"},
            json=test_query
        )
        
        if response.status_code != 200:
            print(f"❌ 查询失败: {response.status_code} - {response.text}")
            return False
        
        result = response.json()
        print(f"✅ 查询成功")
        print(f"   找到结果数: {result['total_found']}")
        print(f"   搜索耗时: {result['search_time_ms']:.2f}ms")
        
        if result['results']:
            print("\n   前5个结果:")
            for i, res in enumerate(result['results'][:5]):
                print(f"   {i+1}. {res['bank_name']}")
                print(f"      联行号: {res['bank_code']}")
                print(f"      相似度: {res.get('similarity_score', 'N/A')}")
                print()
        else:
            print("   ❌ 没有找到任何结果")
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        return False
    
    # 4. 测试更简化查询
    print("\n4. 测试更简化查询：西单")
    test_query = {
        "question": "西单",
        "top_k": 10,
        "similarity_threshold": 0.1
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/rag/search", 
            headers={**headers, "Content-Type": "application/json"},
            json=test_query
        )
        
        if response.status_code != 200:
            print(f"❌ 查询失败: {response.status_code} - {response.text}")
            return False
        
        result = response.json()
        print(f"✅ 查询成功")
        print(f"   找到结果数: {result['total_found']}")
        print(f"   搜索耗时: {result['search_time_ms']:.2f}ms")
        
        if result['results']:
            print("\n   前5个结果:")
            for i, res in enumerate(result['results'][:5]):
                print(f"   {i+1}. {res['bank_name']}")
                print(f"      联行号: {res['bank_code']}")
                print(f"      相似度: {res.get('similarity_score', 'N/A')}")
                print()
        else:
            print("   ❌ 没有找到任何结果")
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_xidan_query()
    sys.exit(0 if success else 1)