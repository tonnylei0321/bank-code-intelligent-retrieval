#!/usr/bin/env python3
"""
快速测试样本生成修复
"""
import requests
import json

def test_sample_generation():
    """测试样本生成API"""
    BASE_URL = "http://localhost:8000"
    
    # 登录获取token
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            data={"username": "admin", "password": "admin123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code != 200:
            print(f"❌ 登录失败: {response.text}")
            return
        
        token = response.json()["access_token"]
        print("✅ 登录成功")
        
    except Exception as e:
        print(f"❌ 登录失败: {e}")
        return
    
    # 获取数据集
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/datasets",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code != 200:
            print(f"❌ 获取数据集失败: {response.text}")
            return
        
        datasets = response.json()
        if not datasets:
            print("❌ 没有数据集")
            return
        
        dataset_id = datasets[0]["id"]
        print(f"✅ 找到数据集: {datasets[0]['filename']} (ID: {dataset_id})")
        
    except Exception as e:
        print(f"❌ 获取数据集失败: {e}")
        return
    
    # 测试样本生成
    try:
        # 使用原有的QAGenerator API
        response = requests.post(
            f"{BASE_URL}/api/v1/qa-pairs/generate",
            json={
                "dataset_id": dataset_id,
                "question_types": ["exact", "natural"],
                "max_records": 2
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 样本生成成功!")
            print(f"   总尝试: {result.get('total_attempts', 0)}")
            print(f"   成功: {result.get('successful', 0)}")
            print(f"   失败: {result.get('failed', 0)}")
        else:
            print(f"⚠️  样本生成API返回: {response.status_code}")
            print(f"   响应: {response.text}")
            
    except Exception as e:
        print(f"❌ 样本生成测试失败: {e}")
    
    # 检查生成的样本
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/qa-pairs",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            samples = response.json()
            print(f"✅ 当前样本总数: {len(samples)}")
            
            if samples:
                latest = samples[0]
                print(f"   最新样本:")
                print(f"   问题: {latest['question'][:50]}...")
                print(f"   答案: {latest['answer'][:50]}...")
                print(f"   类型: {latest['question_type']}")
        else:
            print(f"⚠️  获取样本失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 获取样本失败: {e}")

if __name__ == "__main__":
    print("🔍 快速测试样本生成修复")
    print("=" * 40)
    test_sample_generation()
    print("=" * 40)
    print("🎉 测试完成")