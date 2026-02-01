#!/usr/bin/env python3
"""
测试LLM生成功能的脚本
"""

import requests
import json
import time

def test_llm_generation():
    """测试LLM生成功能"""
    
    # 准备测试文件
    test_file = "test_llm_debug.unl"
    
    # API端点
    base_url = "http://localhost:8000"
    
    # 登录获取token
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    print("🔐 登录...")
    login_response = requests.post(f"{base_url}/api/v1/auth/login", data=login_data)
    if login_response.status_code != 200:
        print(f"❌ 登录失败: {login_response.text}")
        return
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    print("✅ 登录成功")
    
    # 上传文件并触发LLM生成
    print("📤 上传文件并触发LLM生成...")
    
    with open(test_file, 'rb') as f:
        files = {'file': (test_file, f, 'text/plain')}
        data = {
            'generation_method': 'llm',
            'llm_name': 'qwen',
            'data_amount': 'limited',
            'sample_count': '100',
            'samples_per_bank': '7'
        }
        
        upload_response = requests.post(
            f"{base_url}/api/v1/bank-data/upload-and-generate",
            files=files,
            data=data,
            headers=headers
        )
    
    if upload_response.status_code != 200:
        print(f"❌ 上传失败: {upload_response.text}")
        return
    
    result = upload_response.json()
    task_id = result.get("task_id")
    
    print(f"✅ 上传成功，任务ID: {task_id}")
    
    # 监控任务状态
    print("⏳ 监控任务状态...")
    
    for i in range(60):  # 最多等待60秒
        status_response = requests.get(
            f"{base_url}/api/v1/bank-data/task-status/{task_id}",
            headers=headers
        )
        
        if status_response.status_code == 200:
            status = status_response.json()
            print(f"📊 任务状态: {status.get('status', 'unknown')}")
            print(f"📝 消息: {status.get('message', 'no message')}")
            
            if status.get('status') in ['completed', 'failed']:
                break
        else:
            print(f"⚠️ 状态查询失败: {status_response.text}")
        
        time.sleep(2)
    
    print("🏁 测试完成")

if __name__ == "__main__":
    test_llm_generation()