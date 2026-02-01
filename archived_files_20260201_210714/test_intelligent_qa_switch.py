#!/usr/bin/env python3
"""
测试智能问答RAG开关功能

测试RAG检索增强开关的功能
"""

import requests
import json

def get_auth_token():
    """获取认证token"""
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    response = requests.post(
        "http://localhost:8000/api/v1/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"登录失败: {response.text}")

def test_qa_with_strategy(token, question, strategy):
    """测试指定策略的问答"""
    print(f"\n🧪 测试问答 - 策略: {strategy}")
    print(f"问题: {question}")
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    data = {
        "question": question,
        "model_type": "gpt-3.5-turbo",
        "retrieval_strategy": strategy
    }
    
    response = requests.post(
        "http://localhost:8000/api/intelligent-qa/ask",
        json=data,
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            qa_data = result["data"]
            print(f"✅ 问答成功")
            print(f"   策略: {qa_data.get('retrieval_strategy')}")
            print(f"   置信度: {qa_data.get('confidence', 0):.2f}")
            print(f"   响应时间: {qa_data.get('response_time', 0):.2f}s")
            print(f"   匹配银行数: {len(qa_data.get('matched_banks', []))}")
            print(f"   答案: {qa_data.get('answer', '')[:100]}...")
            return True
        else:
            print(f"❌ 问答失败: {result.get('error_message')}")
            return False
    else:
        print(f"❌ HTTP错误: {response.status_code}")
        print(f"   响应: {response.text}")
        return False

def main():
    """主测试函数"""
    print("🧪 测试智能问答RAG开关功能")
    print("=" * 50)
    
    try:
        # 获取认证token
        print("1️⃣ 获取认证token...")
        token = get_auth_token()
        print("   ✅ 认证成功")
        
        # 测试问题
        test_question = "中国工商银行股份有限公司上海市西虹桥支行的联行号是什么？"
        
        # 测试Redis检索（对应前端关闭RAG开关）
        print("\n2️⃣ 测试Redis检索（关闭RAG开关）")
        redis_success = test_qa_with_strategy(token, test_question, "redis_only")
        
        # 测试RAG检索（对应前端开启RAG开关）
        print("\n3️⃣ 测试RAG检索（开启RAG开关）")
        rag_success = test_qa_with_strategy(token, test_question, "rag_only")
        
        # 测试结果总结
        print("\n📊 测试结果总结:")
        print(f"   Redis检索: {'✅ 成功' if redis_success else '❌ 失败'}")
        print(f"   RAG检索: {'✅ 成功' if rag_success else '❌ 失败'}")
        
        if redis_success and rag_success:
            print("\n🎉 RAG开关功能测试完全成功！")
            print("前端可以通过开关控制使用Redis检索或RAG检索")
        else:
            print("\n⚠️ 部分功能测试失败，请检查系统配置")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    main()