#!/usr/bin/env python3
'''
系统错误修复验证脚本
'''
import requests
import json

def test_system():
    base_url = "http://localhost:8000"
    
    # 测试健康检查
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ 系统健康检查通过")
        else:
            print(f"⚠️ 系统健康检查异常: {response.status_code}")
    except Exception as e:
        print(f"❌ 无法连接到后端服务: {e}")
    
    # 测试登录
    try:
        response = requests.post(
            f"{base_url}/api/v1/auth/login",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data="username=admin&password=admin123",
            timeout=10
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            print("✅ 登录测试通过")
            
            # 测试智能问答
            headers = {"Authorization": f"Bearer {token}"}
            qa_response = requests.post(
                f"{base_url}/api/intelligent-qa/ask",
                headers=headers,
                json={
                    "question": "中国工商银行的联行号是什么？",
                    "retrieval_strategy": "redis_only",
                    "model_type": "local"
                },
                timeout=30
            )
            
            if qa_response.status_code == 200:
                print("✅ 智能问答测试通过")
            else:
                print(f"⚠️ 智能问答测试失败: {qa_response.status_code}")
                print(f"错误信息: {qa_response.text}")
        else:
            print(f"❌ 登录失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    print("🧪 系统错误修复验证")
    print("=" * 40)
    test_system()
