#!/usr/bin/env python3
"""
测试样本生成功能
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def login():
    """登录获取token"""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data="username=admin&password=admin123"
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"登录失败: {response.text}")
        return None

def test_strategies_api(token):
    """测试获取生成策略API"""
    print("🔍 测试获取生成策略...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{BASE_URL}/api/sample-generation/strategies",
        headers=headers
    )
    
    print(f"响应状态: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("✅ 获取策略成功")
        print(f"  - 挑选策略: {len(data.get('selection_strategies', []))} 种")
        print(f"  - 记录数策略: {len(data.get('record_count_strategies', []))} 种")
        print(f"  - LLM策略: {len(data.get('llm_strategies', []))} 种")
        return True
    else:
        print(f"❌ 获取策略失败: {response.text}")
        return False

def test_sample_generation(token):
    """测试样本生成"""
    print("\n🔍 测试样本生成...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 先获取数据集列表
    datasets_response = requests.get(
        f"{BASE_URL}/api/v1/datasets/",
        headers=headers
    )
    
    if datasets_response.status_code != 200:
        print("❌ 无法获取数据集列表")
        return False
    
    datasets = datasets_response.json()
    if not datasets:
        print("❌ 没有可用的数据集")
        return False
    
    dataset_id = datasets[0]["id"]
    print(f"使用数据集: {datasets[0]['filename']} (ID: {dataset_id})")
    
    # 启动样本生成任务
    generation_request = {
        "dataset_id": dataset_id,
        "selection_strategy": "all",
        "record_count_strategy": "custom",
        "custom_count": 5,  # 只生成5条记录的样本
        "llm_strategies": ["natural_language", "structured_qa"],
        "questions_per_record": 2,
        "model_type": "local",
        "temperature": 0.7,
        "max_tokens": 256,
        "task_name": "测试样本生成",
        "description": "这是一个测试任务"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/sample-generation/start",
        headers=headers,
        json=generation_request
    )
    
    print(f"启动任务响应状态: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        task_id = result["task_id"]
        print("✅ 样本生成任务已启动")
        print(f"  - 任务ID: {task_id}")
        print(f"  - 预计生成: {result['estimated_total']} 个样本")
        
        # 监控任务进度
        return monitor_task_progress(token, task_id)
    else:
        print(f"❌ 启动任务失败: {response.text}")
        return False

def monitor_task_progress(token, task_id):
    """监控任务进度"""
    print(f"\n🔍 监控任务进度: {task_id}")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    for i in range(30):  # 最多监控30次（60秒）
        response = requests.get(
            f"{BASE_URL}/api/sample-generation/status/{task_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            status = response.json()
            progress = status["progress"]
            current_step = status["current_step"]
            generated = status["generated_samples"]
            errors = status["error_count"]
            
            print(f"  进度: {progress:.1f}% | 步骤: {current_step} | 生成: {generated} | 错误: {errors}")
            
            if status["status"] == "completed":
                print("✅ 任务完成！")
                print(f"  - 总共生成: {generated} 个样本")
                print(f"  - 错误数量: {errors}")
                return True
            elif status["status"] == "failed":
                print("❌ 任务失败")
                return False
            elif status["status"] == "cancelled":
                print("⚠️ 任务被取消")
                return False
        else:
            print(f"❌ 获取任务状态失败: {response.status_code}")
            return False
        
        time.sleep(2)  # 等待2秒
    
    print("⚠️ 监控超时")
    return False

def test_task_list(token):
    """测试获取任务列表"""
    print("\n🔍 测试获取任务列表...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{BASE_URL}/api/sample-generation/tasks",
        headers=headers
    )
    
    print(f"响应状态: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        tasks = data.get("tasks", [])
        print("✅ 获取任务列表成功")
        print(f"  - 任务数量: {len(tasks)}")
        
        for task in tasks[:3]:  # 显示前3个任务
            print(f"    - {task['task_id'][:8]}... | {task['status']} | {task['progress']:.1f}%")
        
        return True
    else:
        print(f"❌ 获取任务列表失败: {response.text}")
        return False

def main():
    print("🧪 样本生成功能测试")
    print("=" * 50)
    
    # 登录
    token = login()
    if not token:
        print("❌ 无法登录，终止测试")
        return
    
    print("✅ 登录成功")
    
    # 测试各个功能
    results = {}
    
    results['strategies'] = test_strategies_api(token)
    results['generation'] = test_sample_generation(token)
    results['task_list'] = test_task_list(token)
    
    # 总结结果
    print("\n" + "=" * 50)
    print("📊 测试结果总结:")
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  - {test_name}: {status}")
    
    success_count = sum(results.values())
    total_count = len(results)
    
    print(f"\n总体结果: {success_count}/{total_count} 项测试通过")
    
    if success_count == total_count:
        print("🎉 样本生成功能测试全部通过！")
    else:
        print("⚠️ 部分功能测试失败，请检查错误信息")

if __name__ == "__main__":
    main()