#!/usr/bin/env python3
"""
测试上传和生成功能的修复
"""

import requests
import json
import time

# API 基础URL
BASE_URL = "http://localhost:8000"

def login():
    """登录获取token"""
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"登录失败: {response.text}")
        return None

def test_upload_and_generate():
    """测试上传文件并生成训练数据"""
    token = login()
    if not token:
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 使用测试文件
    with open("test_training_management.unl", "rb") as f:
        files = {"file": f}
        data = {
            "generation_method": "rule",
            "data_amount": "limited", 
            "sample_count": "5",  # 只处理5条记录
            "samples_per_bank": "3"  # 每个银行生成3个样本
        }
        
        print("🚀 开始测试上传和生成...")
        response = requests.post(
            f"{BASE_URL}/api/v1/bank-data/upload-and-generate",
            headers=headers,
            files=files,
            data=data
        )
        
        if response.status_code == 200:
            result = response.json()
            task_id = result.get("task_id")
            print(f"✅ 任务启动成功，任务ID: {task_id}")
            
            # 监控进度
            if task_id:
                monitor_progress(token, task_id)
        else:
            print(f"❌ 上传失败: {response.text}")

def monitor_progress(token, task_id):
    """监控任务进度"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print("📊 监控任务进度...")
    for i in range(30):  # 最多等待30次
        response = requests.get(
            f"{BASE_URL}/api/v1/bank-data/generation-progress/{task_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            progress = result.get("data", {})
            status = progress.get("status", "unknown")
            percentage = progress.get("progress_percentage", 0)
            
            print(f"状态: {status}, 进度: {percentage:.1f}%")
            
            if status == "completed":
                print("🎉 任务完成！")
                print(f"生成样本数: {progress.get('generated_samples', 0)}")
                print(f"数据集ID: {progress.get('dataset_id', 'N/A')}")
                break
            elif status == "failed":
                print(f"❌ 任务失败: {progress.get('error', '未知错误')}")
                break
        else:
            print(f"获取进度失败: {response.text}")
            break
        
        time.sleep(2)  # 等待2秒

if __name__ == "__main__":
    test_upload_and_generate()