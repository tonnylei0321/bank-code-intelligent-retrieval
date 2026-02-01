#!/usr/bin/env python3
"""
测试智能问答与Redis集成
"""
import requests
import json

def test_intelligent_qa_with_redis():
    """测试智能问答与Redis集成"""
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
    
    # 2. 测试不同类型的问题
    test_questions = [
        {
            "question": "工商银行西虹桥支行的联行号是什么？",
            "strategy": "redis_only"
        },
        {
            "question": "中国工商银行股份有限公司上海市西虹桥支行",
            "strategy": "redis_only"
        },
        {
            "question": "102290002916是哪个银行？",
            "strategy": "redis_only"
        },
        {
            "question": "福州有哪些工商银行支行？",
            "strategy": "intelligent"
        }
    ]
    
    for i, test_case in enumerate(test_questions, 1):
        print(f"\n{i}. 测试问题: {test_case['question']}")
        print(f"   策略: {test_case['strategy']}")
        
        qa_data = {
            "question": test_case["question"],
            "retrieval_strategy": test_case["strategy"]
        }
        
        response = requests.post(
            f"{base_url}/api/intelligent-qa/ask",
            headers=headers,
            json=qa_data
        )
        
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                result = data["data"]
                print(f"   答案: {result.get('answer', 'No answer')[:100]}...")
                print(f"   置信度: {result.get('confidence', 0)}")
                print(f"   匹配银行数: {len(result.get('matched_banks', []))}")
                print(f"   响应时间: {result.get('response_time', 0):.2f}秒")
            else:
                print(f"   ❌ 请求失败: {data}")
        else:
            print(f"   ❌ HTTP错误: {response.text}")

if __name__ == "__main__":
    test_intelligent_qa_with_redis()