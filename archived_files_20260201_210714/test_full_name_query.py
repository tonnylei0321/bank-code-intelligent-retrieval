#!/usr/bin/env python3
"""
测试完整银行名称查询
"""

import requests
import json

def test_full_name_query():
    """测试完整银行名称查询"""
    
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
    
    # 2. 测试完整银行名称查询
    query = "中国工商银行股份有限公司北京西单支行"
    print(f"\n2. 测试完整银行名称查询: {query}")
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/rag/search", 
            headers={**headers, "Content-Type": "application/json"},
            json={
                "question": query,
                "top_k": 10,
                "similarity_threshold": 0.1
            }
        )
        
        if response.status_code != 200:
            print(f"❌ 查询失败: {response.status_code} - {response.text}")
            return False
        
        result = response.json()
        print(f"📊 查询结果数: {result['total_found']}")
        
        if result['results']:
            print("\n🔍 查询结果:")
            for i, bank in enumerate(result['results'], 1):
                print(f"{i}. {bank['bank_name']}")
                print(f"   联行号: {bank['bank_code']}")
                print(f"   相似度: {bank.get('similarity_score', 'N/A')}")
                print(f"   匹配方法: {bank.get('retrieval_method', 'N/A')}")
                print(f"   最终分数: {bank.get('final_score', 'N/A')}")
                print()
            
            # 检查第一个结果是否正确
            first_result = result['results'][0]['bank_name']
            expected = "中国工商银行股份有限公司北京西单支行"
            
            if expected == first_result:
                print("✅ 完整名称查询结果正确！")
                return True
            else:
                print(f"❌ 完整名称查询结果不正确")
                print(f"   期望: {expected}")
                print(f"   实际: {first_result}")
                return False
        else:
            print("❌ 没有找到任何结果")
            return False
            
    except Exception as e:
        print(f"❌ 查询异常: {e}")
        return False

if __name__ == "__main__":
    success = test_full_name_query()
    exit(0 if success else 1)