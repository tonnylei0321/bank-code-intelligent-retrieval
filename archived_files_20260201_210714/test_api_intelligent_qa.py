#!/usr/bin/env python3
"""
测试智能问答API
"""

import requests
import json

def test_intelligent_qa_api():
    """测试智能问答API"""
    print("🧪 测试智能问答API")
    print("=" * 50)
    
    # API基础URL
    base_url = "http://localhost:8000"
    
    # 测试问题
    test_questions = [
        {
            "question": "中国工商银行股份有限公司上海市西虹桥支行的联行号是什么？",
            "description": "完整银行名称查询"
        },
        {
            "question": "工商银行西虹桥支行联行号",
            "description": "简化银行名称查询"
        },
        {
            "question": "102290002916是哪个银行？",
            "description": "联行号反查"
        }
    ]
    
    # 首先尝试登录获取token
    print("1️⃣ 获取访问令牌...")
    try:
        login_response = requests.post(f"{base_url}/api/v1/auth/login", data={
            "username": "admin",
            "password": "admin123456"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            print("✅ 登录成功")
        else:
            print(f"❌ 登录失败: {login_response.text}")
            return
    except Exception as e:
        print(f"❌ 登录请求失败: {e}")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 测试智能问答
    print("\n2️⃣ 测试智能问答功能...")
    
    for i, test_case in enumerate(test_questions, 1):
        print(f"\n测试 {i}: {test_case['description']}")
        print(f"问题: {test_case['question']}")
        
        try:
            # 发送问答请求
            response = requests.post(
                f"{base_url}/api/intelligent-qa/ask",
                headers=headers,
                json={
                    "question": test_case["question"],
                    "model_type": "gpt-3.5-turbo",
                    "retrieval_strategy": "redis_only"
                },
                timeout=30
            )
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    data = result.get("data", {})
                    print(f"✅ 问答成功")
                    print(f"   回答: {data.get('answer', 'N/A')[:100]}...")
                    print(f"   置信度: {data.get('confidence', 0):.2f}")
                    print(f"   匹配银行数: {len(data.get('matched_banks', []))}")
                    print(f"   检索策略: {data.get('retrieval_strategy', 'N/A')}")
                    print(f"   响应时间: {data.get('response_time', 0):.2f}s")
                    
                    # 显示匹配的银行
                    matched_banks = data.get('matched_banks', [])
                    if matched_banks:
                        print(f"   匹配银行:")
                        for bank in matched_banks[:3]:
                            print(f"     - {bank.get('bank_name', 'N/A')} (联行号: {bank.get('bank_code', 'N/A')})")
                else:
                    print(f"❌ 问答失败: {result.get('error_message', '未知错误')}")
            else:
                print(f"❌ 请求失败: {response.text}")
                
        except Exception as e:
            print(f"❌ 请求异常: {e}")
    
    print("\n🎉 API测试完成")

if __name__ == "__main__":
    test_intelligent_qa_api()