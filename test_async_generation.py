#!/usr/bin/env python3
"""
测试异步样本生成API
"""
import requests
import time
import json

BASE_URL = "http://localhost:8000"

# 登录获取token
def login():
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        data={
            "username": "admin",
            "password": "admin123"
        }
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"登录失败: {response.text}")
        return None

# 启动生成任务
def start_generation(token, dataset_id=1):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "dataset_id": dataset_id,
        "generation_type": "llm",
        "question_types": ["exact", "fuzzy"],
        "llm_provider": "local",  # 使用本地模板，速度快
        "selection_strategy": "all",
        "record_count_strategy": "custom",
        "custom_count": 10,  # 只生成10条测试
        "train_ratio": 0.8,
        "val_ratio": 0.1,
        "test_ratio": 0.1
    }
    
    print("🚀 启动生成任务...")
    print(f"参数: {json.dumps(data, indent=2, ensure_ascii=False)}")
    
    response = requests.post(
        f"{BASE_URL}/api/v1/sample-generation/start",
        headers=headers,
        json=data
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 任务已创建: {result['task_id']}")
        return result['task_id']
    else:
        print(f"❌ 创建任务失败: {response.text}")
        return None

# 查询任务状态
def get_task_status(token, task_id):
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{BASE_URL}/api/v1/sample-generation/status/{task_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ 查询状态失败: {response.text}")
        return None

# 列出所有任务
def list_tasks(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{BASE_URL}/api/v1/sample-generation/tasks",
        headers=headers
    )
    
    if response.status_code == 200:
        return response.json()["tasks"]
    else:
        print(f"❌ 列出任务失败: {response.text}")
        return []

# 取消任务
def cancel_task(token, task_id):
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.delete(
        f"{BASE_URL}/api/v1/sample-generation/tasks/{task_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        print(f"✅ 任务已取消")
        return True
    else:
        print(f"❌ 取消任务失败: {response.text}")
        return False

# 监控任务进度
def monitor_task(token, task_id, max_wait=300):
    print(f"\n📊 开始监控任务: {task_id}")
    print("=" * 60)
    
    start_time = time.time()
    last_progress = -1
    
    while True:
        # 检查超时
        if time.time() - start_time > max_wait:
            print(f"\n⏰ 超时 ({max_wait}秒)，停止监控")
            break
        
        # 查询状态
        status = get_task_status(token, task_id)
        if not status:
            break
        
        # 显示进度（只在变化时显示）
        if status['progress'] != last_progress:
            progress_bar = "█" * int(status['progress'] / 5) + "░" * (20 - int(status['progress'] / 5))
            print(f"\r进度: [{progress_bar}] {status['progress']}% | "
                  f"状态: {status['status']} | "
                  f"步骤: {status['current_step']} | "
                  f"样本: {status['generated_samples']}", end='')
            last_progress = status['progress']
        
        # 检查是否完成
        if status['status'] in ['completed', 'failed', 'cancelled']:
            print(f"\n\n{'='*60}")
            print(f"任务状态: {status['status']}")
            
            if status['status'] == 'completed':
                result = status.get('result', {})
                print(f"✅ 生成完成！")
                print(f"   总计生成: {result.get('total_generated', 0)} 个样本")
                print(f"   训练集: {result.get('train_count', 0)}")
                print(f"   验证集: {result.get('val_count', 0)}")
                print(f"   测试集: {result.get('test_count', 0)}")
                print(f"   失败: {result.get('failed_count', 0)}")
            elif status['status'] == 'failed':
                print(f"❌ 任务失败: {status.get('error_message', '未知错误')}")
            else:
                print(f"⚠️ 任务已取消")
            
            # 显示最后几条日志
            if status.get('logs'):
                print(f"\n最近日志:")
                for log in status['logs'][-5:]:
                    print(f"  {log}")
            
            break
        
        # 等待2秒
        time.sleep(2)

def main():
    print("=" * 60)
    print("异步样本生成API测试")
    print("=" * 60)
    
    # 1. 登录
    print("\n1️⃣ 登录系统...")
    token = login()
    if not token:
        return
    print("✅ 登录成功")
    
    # 2. 列出现有任务
    print("\n2️⃣ 列出现有任务...")
    tasks = list_tasks(token)
    if tasks:
        print(f"找到 {len(tasks)} 个任务:")
        for task in tasks[:5]:  # 只显示前5个
            print(f"  - {task['task_id'][:8]}... | {task['status']} | {task['progress']}%")
    else:
        print("暂无任务")
    
    # 3. 启动新任务
    print("\n3️⃣ 启动新的生成任务...")
    task_id = start_generation(token)
    if not task_id:
        return
    
    # 4. 监控任务进度
    monitor_task(token, task_id)
    
    # 5. 再次列出任务
    print("\n5️⃣ 最终任务列表...")
    tasks = list_tasks(token)
    print(f"共 {len(tasks)} 个任务")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
