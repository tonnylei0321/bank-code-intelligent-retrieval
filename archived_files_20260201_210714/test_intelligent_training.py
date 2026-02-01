#!/usr/bin/env python3
"""
测试智能训练参数优化功能
"""

import requests
import json
import time
from datetime import datetime

def test_intelligent_training():
    """测试智能训练参数优化"""
    
    base_url = "http://localhost:8000"
    
    # 1. 登录获取token
    print("1️⃣ 登录获取认证token...")
    login_response = requests.post(
        f"{base_url}/api/v1/auth/login",
        data={"username": "admin", "password": "admin123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if login_response.status_code != 200:
        print(f"❌ 登录失败: {login_response.text}")
        return
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ 登录成功")
    
    # 2. 获取可用数据集
    print("\n2️⃣ 获取可用数据集...")
    datasets_response = requests.get(f"{base_url}/api/v1/datasets", headers=headers)
    
    if datasets_response.status_code != 200:
        print(f"❌ 获取数据集失败: {datasets_response.text}")
        return
    
    datasets = datasets_response.json()
    if not datasets:
        print("❌ 没有可用的数据集")
        return
    
    # 使用最新的数据集
    dataset = datasets[0]
    dataset_id = dataset["id"]
    print(f"✅ 使用数据集: ID={dataset_id}, 文件={dataset['filename']}")
    
    # 3. 测试不同模型的参数优化
    models_to_test = [
        "Qwen/Qwen2.5-0.5B",
        "Qwen/Qwen2.5-1.5B"
    ]
    
    for model_name in models_to_test:
        print(f"\n3️⃣ 测试模型 {model_name} 的参数优化...")
        
        # 获取优化参数
        optimize_request = {
            "dataset_id": dataset_id,
            "model_name": model_name,
            "target_training_time_hours": 6.0  # 目标6小时完成
        }
        
        optimize_response = requests.post(
            f"{base_url}/api/v1/training/optimize",
            json=optimize_request,
            headers=headers
        )
        
        if optimize_response.status_code != 200:
            print(f"❌ 参数优化失败: {optimize_response.text}")
            continue
        
        optimized_params = optimize_response.json()
        
        print(f"✅ {model_name} 优化参数:")
        print(f"   📊 基础参数:")
        print(f"      Epochs: {optimized_params['epochs']}")
        print(f"      Batch Size: {optimized_params['batch_size']}")
        print(f"      Learning Rate: {optimized_params['learning_rate']}")
        
        print(f"   🔧 LoRA参数:")
        print(f"      LoRA R: {optimized_params['lora_r']}")
        print(f"      LoRA Alpha: {optimized_params['lora_alpha']}")
        print(f"      LoRA Dropout: {optimized_params['lora_dropout']}")
        
        print(f"   ⚡ 优化参数:")
        print(f"      梯度累积步数: {optimized_params['gradient_accumulation_steps']}")
        print(f"      预热步数: {optimized_params['warmup_steps']}")
        print(f"      权重衰减: {optimized_params['weight_decay']}")
        
        print(f"   📈 预估信息:")
        print(f"      预计训练时间: {optimized_params['estimated_training_time_hours']:.2f} 小时")
        print(f"      预计内存使用: {optimized_params['estimated_memory_usage_gb']:.2f} GB")
        
        print(f"   💡 优化建议:")
        for note in optimized_params['optimization_notes']:
            print(f"      • {note}")
    
    # 4. 测试启动智能优化训练
    print(f"\n4️⃣ 启动智能优化训练任务...")
    
    training_request = {
        "dataset_id": dataset_id,
        "model_name": "Qwen/Qwen2.5-0.5B",  # 使用较小的模型
        "use_optimized_params": True,
        "target_training_time_hours": 2.0  # 目标2小时完成
    }
    
    training_response = requests.post(
        f"{base_url}/api/v1/training/start",
        json=training_request,
        headers=headers
    )
    
    if training_response.status_code != 201:
        print(f"❌ 启动训练失败: {training_response.text}")
        return
    
    job = training_response.json()
    job_id = job["id"]
    
    print(f"✅ 训练任务已启动: ID={job_id}")
    print(f"   模型: {job['model_name']}")
    print(f"   数据集: {job['dataset_id']}")
    print(f"   配置: {job['epochs']} epochs, batch_size={job['batch_size']}")
    print(f"   学习率: {job['learning_rate']}")
    print(f"   LoRA: r={job['lora_r']}, alpha={job['lora_alpha']}")
    
    # 5. 监控训练进度
    print(f"\n5️⃣ 监控训练进度...")
    
    for i in range(10):  # 监控10次
        time.sleep(30)  # 等待30秒
        
        status_response = requests.get(
            f"{base_url}/api/v1/training/{job_id}",
            headers=headers
        )
        
        if status_response.status_code != 200:
            print(f"⚠️ 获取状态失败: {status_response.text}")
            continue
        
        job_status = status_response.json()
        status = job_status["status"]
        progress = job_status.get("progress_percentage", 0)
        current_step = job_status.get("current_step", 0)
        total_steps = job_status.get("total_steps", 0)
        train_loss = job_status.get("train_loss")
        
        print(f"⏰ [{datetime.now().strftime('%H:%M:%S')}] 状态: {status}")
        if total_steps > 0:
            print(f"   进度: {current_step}/{total_steps} ({progress:.2f}%)")
        if train_loss:
            print(f"   损失: {train_loss:.4f}")
        
        if status in ["completed", "failed"]:
            print(f"🏁 训练结束: {status}")
            if status == "failed":
                error_msg = job_status.get("error_message", "未知错误")
                print(f"❌ 错误信息: {error_msg}")
            break
    
    print("\n🎉 智能训练参数优化测试完成!")

if __name__ == "__main__":
    test_intelligent_training()