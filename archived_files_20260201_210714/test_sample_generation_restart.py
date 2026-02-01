#!/usr/bin/env python3
"""
测试样本生成功能（重启后验证）

验证后端服务重启后，样本生成功能是否正常工作
"""
import requests
import json
import time

# API配置
BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"

def login():
    """登录获取token"""
    print("🔐 登录中...")
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        data={
            "username": USERNAME,
            "password": PASSWORD
        }
    )
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"✅ 登录成功")
        return token
    else:
        print(f"❌ 登录失败: {response.text}")
        return None

def get_datasets(token):
    """获取数据集列表"""
    print("\n📊 获取数据集列表...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/v1/datasets", headers=headers)
    
    if response.status_code == 200:
        datasets = response.json()
        print(f"✅ 找到 {len(datasets)} 个数据集")
        for ds in datasets[:3]:
            name = ds.get('name', ds.get('filename', 'Unknown'))
            record_count = ds.get('record_count', ds.get('total_records', 0))
            print(f"   - ID: {ds['id']}, 名称: {name}, 记录数: {record_count}")
        return datasets
    else:
        print(f"❌ 获取数据集失败: {response.text}")
        return []

def test_generate_samples(token, dataset_id):
    """测试样本生成功能"""
    print(f"\n🎯 测试样本生成（数据集ID: {dataset_id}）...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 测试配置
    test_configs = [
        {
            "name": "本地模板生成器",
            "payload": {
                "dataset_id": dataset_id,
                "generation_type": "llm",
                "llm_provider": "local",
                "question_types": ["exact"],
                "selection_strategy": "all",
                "record_count_strategy": "custom",
                "custom_count": 2,
                "train_ratio": 0.8,
                "val_ratio": 0.1,
                "test_ratio": 0.1
            }
        },
        {
            "name": "通义千问API",
            "payload": {
                "dataset_id": dataset_id,
                "generation_type": "llm",
                "llm_provider": "qwen",
                "question_types": ["natural"],
                "selection_strategy": "all",
                "record_count_strategy": "custom",
                "custom_count": 1,
                "train_ratio": 0.8,
                "val_ratio": 0.1,
                "test_ratio": 0.1
            }
        }
    ]
    
    for config in test_configs:
        print(f"\n📝 测试: {config['name']}")
        print(f"   配置: {json.dumps(config['payload'], ensure_ascii=False, indent=2)}")
        
        response = requests.post(
            f"{BASE_URL}/api/v1/qa-pairs/generate",
            headers=headers,
            json=config['payload']
        )
        
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 201:
            result = response.json()
            print(f"   ✅ 生成成功!")
            print(f"   - 总计生成: {result.get('total_generated', 0)}")
            print(f"   - 训练集: {result.get('train_count', 0)}")
            print(f"   - 验证集: {result.get('val_count', 0)}")
            print(f"   - 测试集: {result.get('test_count', 0)}")
            
            if result.get('errors'):
                print(f"   ⚠️  错误信息:")
                for error in result['errors'][:3]:
                    print(f"      - {error}")
        else:
            print(f"   ❌ 生成失败: {response.text}")
            
            # 如果是第一个测试失败，说明还有问题
            if config['name'] == "本地模板生成器":
                print("\n❌ 本地模板生成器测试失败，可能需要进一步检查代码")
                return False
        
        # 等待一下再进行下一个测试
        time.sleep(1)
    
    return True

def main():
    """主函数"""
    print("=" * 60)
    print("样本生成功能测试（重启后验证）")
    print("=" * 60)
    
    # 登录
    token = login()
    if not token:
        return
    
    # 获取数据集
    datasets = get_datasets(token)
    if not datasets:
        print("\n❌ 没有可用的数据集")
        return
    
    # 使用第一个数据集进行测试
    dataset_id = datasets[0]['id']
    
    # 测试样本生成
    success = test_generate_samples(token, dataset_id)
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 测试完成！样本生成功能已修复")
        print("\n下一步:")
        print("1. 打开前端页面: http://localhost:3000")
        print("2. 进入 样本管理 -> 样本管理")
        print("3. 点击 生成样本 按钮")
        print("4. 选择数据集和LLM提供商")
        print("5. 配置生成参数并开始生成")
    else:
        print("❌ 测试失败，请检查日志")
        print("\n查看日志:")
        print("  tail -100 mvp/logs/app_2026-02-01.log")
    print("=" * 60)

if __name__ == "__main__":
    main()
