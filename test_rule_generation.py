#!/usr/bin/env python3
"""
测试规则生成方式
"""
import requests
import json
import time

# 配置
BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"

def login():
    """登录获取token"""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        data={
            "username": USERNAME,
            "password": PASSWORD
        }
    )
    if response.status_code == 200:
        data = response.json()
        return data["access_token"]
    else:
        print(f"❌ 登录失败: {response.text}")
        return None

def get_datasets(token):
    """获取数据集列表"""
    response = requests.get(
        f"{BASE_URL}/api/v1/datasets",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ 获取数据集失败: {response.text}")
        return []

def start_rule_generation(token, dataset_id):
    """启动规则生成任务"""
    request_data = {
        "dataset_id": dataset_id,
        "generation_type": "rule",  # 使用规则生成
        "question_types": ["exact", "fuzzy"],  # 测试两种类型
        "record_count_strategy": "custom",
        "custom_count": 5,  # 只生成5条测试
        "train_ratio": 0.8,
        "val_ratio": 0.1,
        "test_ratio": 0.1
    }
    
    print(f"\n📤 发送请求:")
    print(json.dumps(request_data, indent=2, ensure_ascii=False))
    
    response = requests.post(
        f"{BASE_URL}/api/v1/sample-generation/start",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json=request_data
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ 任务启动成功!")
        print(f"任务ID: {result['task_id']}")
        return result['task_id']
    else:
        print(f"\n❌ 任务启动失败: {response.text}")
        return None

def check_task_status(token, task_id):
    """检查任务状态"""
    response = requests.get(
        f"{BASE_URL}/api/v1/sample-generation/status/{task_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ 获取任务状态失败: {response.text}")
        return None

def monitor_task(token, task_id, max_wait=120):
    """监控任务执行"""
    print(f"\n🔍 开始监控任务 {task_id[:8]}...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        status = check_task_status(token, task_id)
        
        if not status:
            break
        
        print(f"\r进度: {status['progress']}% | 状态: {status['status']} | "
              f"步骤: {status['current_step']} | "
              f"已生成: {status['generated_samples']} | "
              f"错误: {status['error_count']}", end="")
        
        if status['status'] in ['completed', 'failed', 'cancelled']:
            print()  # 换行
            
            if status['status'] == 'completed':
                print(f"\n✅ 任务完成!")
                print(f"生成样本数: {status['generated_samples']}")
                if status.get('result'):
                    result = status['result']
                    print(f"训练集: {result.get('train_count', 0)}")
                    print(f"验证集: {result.get('val_count', 0)}")
                    print(f"测试集: {result.get('test_count', 0)}")
                
                # 显示最后几条日志
                if status.get('logs'):
                    print(f"\n📋 最后几条日志:")
                    for log in status['logs'][-5:]:
                        print(f"  {log}")
                
                return True
            
            elif status['status'] == 'failed':
                print(f"\n❌ 任务失败!")
                print(f"错误信息: {status.get('error_message', '未知错误')}")
                
                # 显示日志
                if status.get('logs'):
                    print(f"\n📋 错误日志:")
                    for log in status['logs']:
                        print(f"  {log}")
                
                return False
            
            else:
                print(f"\n⚠️  任务被取消")
                return False
        
        time.sleep(2)  # 每2秒检查一次
    
    print(f"\n⏱️  超时: 任务执行超过 {max_wait} 秒")
    return False

def main():
    print("=" * 60)
    print("规则生成方式测试")
    print("=" * 60)
    
    # 1. 登录
    print("\n1️⃣  登录系统...")
    token = login()
    if not token:
        return
    print("✅ 登录成功")
    
    # 2. 获取数据集
    print("\n2️⃣  获取数据集列表...")
    datasets = get_datasets(token)
    if not datasets:
        print("❌ 没有可用的数据集")
        return
    
    print(f"✅ 找到 {len(datasets)} 个数据集:")
    for ds in datasets:
        print(f"  - ID: {ds['id']}, 名称: {ds['filename']}, 记录数: {ds.get('total_records', 0)}")
    
    # 3. 选择第一个数据集
    dataset_id = datasets[0]['id']
    print(f"\n3️⃣  使用数据集 ID: {dataset_id}")
    
    # 4. 启动规则生成任务
    print("\n4️⃣  启动规则生成任务...")
    task_id = start_rule_generation(token, dataset_id)
    if not task_id:
        return
    
    # 5. 监控任务执行
    print("\n5️⃣  监控任务执行...")
    success = monitor_task(token, task_id)
    
    # 6. 总结
    print("\n" + "=" * 60)
    if success:
        print("✅ 规则生成测试成功!")
    else:
        print("❌ 规则生成测试失败!")
    print("=" * 60)

if __name__ == "__main__":
    main()
