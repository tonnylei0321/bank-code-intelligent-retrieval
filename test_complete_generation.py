#!/usr/bin/env python3
"""
完整测试样本生成流程
包括规则生成和LLM生成
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"

def login():
    """登录"""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        data={"username": USERNAME, "password": PASSWORD}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    print(f"❌ 登录失败: {response.text}")
    return None

def get_datasets(token):
    """获取数据集"""
    response = requests.get(
        f"{BASE_URL}/api/v1/datasets",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        return response.json()
    return []

def start_generation(token, dataset_id, generation_type="rule"):
    """启动生成任务"""
    request_data = {
        "dataset_id": dataset_id,
        "generation_type": generation_type,
        "question_types": ["exact", "fuzzy"],
        "record_count_strategy": "custom",
        "custom_count": 3,  # 只生成3条测试
        "train_ratio": 0.8,
        "val_ratio": 0.1,
        "test_ratio": 0.1
    }
    
    print(f"\n📤 启动{generation_type}生成任务...")
    print(f"参数: {json.dumps(request_data, indent=2, ensure_ascii=False)}")
    
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
        print(f"✅ 任务启动成功: {result['task_id']}")
        return result['task_id']
    else:
        print(f"❌ 任务启动失败: {response.status_code}")
        print(f"错误: {response.text}")
        return None

def monitor_task(token, task_id, max_wait=60):
    """监控任务"""
    print(f"\n🔍 监控任务 {task_id[:8]}...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        response = requests.get(
            f"{BASE_URL}/api/v1/sample-generation/status/{task_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code != 200:
            print(f"\n❌ 获取状态失败: {response.text}")
            return False
        
        status = response.json()
        
        print(f"\r进度: {status['progress']}% | {status['status']} | {status['current_step']}", end="")
        
        if status['status'] == 'completed':
            print(f"\n✅ 任务完成!")
            print(f"生成样本: {status['generated_samples']}")
            if status.get('result'):
                result = status['result']
                print(f"训练集: {result.get('train_count', 0)}")
                print(f"验证集: {result.get('val_count', 0)}")
                print(f"测试集: {result.get('test_count', 0)}")
            
            # 显示日志
            if status.get('logs'):
                print(f"\n📋 最后几条日志:")
                for log in status['logs'][-5:]:
                    print(f"  {log}")
            
            return True
        
        elif status['status'] == 'failed':
            print(f"\n❌ 任务失败!")
            print(f"错误: {status.get('error_message', '未知错误')}")
            
            # 显示所有日志
            if status.get('logs'):
                print(f"\n📋 错误日志:")
                for log in status['logs']:
                    print(f"  {log}")
            
            return False
        
        time.sleep(2)
    
    print(f"\n⏱️  超时")
    return False

def test_generation_type(token, dataset_id, generation_type):
    """测试特定生成类型"""
    print("\n" + "=" * 60)
    print(f"测试 {generation_type.upper()} 生成")
    print("=" * 60)
    
    task_id = start_generation(token, dataset_id, generation_type)
    if not task_id:
        return False
    
    success = monitor_task(token, task_id)
    return success

def main():
    print("=" * 60)
    print("完整样本生成测试")
    print("=" * 60)
    
    # 1. 登录
    print("\n1️⃣  登录...")
    token = login()
    if not token:
        return
    print("✅ 登录成功")
    
    # 2. 获取数据集
    print("\n2️⃣  获取数据集...")
    datasets = get_datasets(token)
    if not datasets:
        print("❌ 没有数据集")
        return
    
    dataset_id = datasets[0]['id']
    print(f"✅ 使用数据集: {datasets[0]['filename']} (ID: {dataset_id})")
    
    # 3. 测试规则生成
    rule_success = test_generation_type(token, dataset_id, "rule")
    
    # 4. 测试LLM生成(可选)
    # llm_success = test_generation_type(token, dataset_id, "llm")
    
    # 5. 总结
    print("\n" + "=" * 60)
    print("测试结果:")
    print(f"  规则生成: {'✅ 成功' if rule_success else '❌ 失败'}")
    # print(f"  LLM生成: {'✅ 成功' if llm_success else '❌ 失败'}")
    print("=" * 60)
    
    if rule_success:
        print("\n✅ 所有测试通过!")
        return 0
    else:
        print("\n❌ 测试失败!")
        return 1

if __name__ == "__main__":
    exit(main())
