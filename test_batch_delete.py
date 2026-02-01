#!/usr/bin/env python3
"""
测试批量删除样本集功能
"""
import requests
import json

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

def get_sample_sets(token, dataset_id):
    """获取样本集列表"""
    response = requests.get(
        f"{BASE_URL}/api/v1/sample-sets/dataset/{dataset_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ 获取样本集失败: {response.text}")
        return []

def batch_delete_sample_sets(token, sample_set_ids):
    """批量删除样本集"""
    response = requests.post(
        f"{BASE_URL}/api/v1/sample-sets/batch-delete",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={"sample_set_ids": sample_set_ids}
    )
    
    print(f"\n📤 请求: POST /api/v1/sample-sets/batch-delete")
    print(f"Body: {json.dumps({'sample_set_ids': sample_set_ids}, indent=2)}")
    print(f"\n📥 响应状态: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 批量删除成功!")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return True
    else:
        print(f"❌ 批量删除失败!")
        print(f"错误: {response.text}")
        return False

def main():
    print("=" * 60)
    print("测试批量删除样本集功能")
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
        print(f"  - ID: {ds['id']}, 名称: {ds['filename']}")
    
    # 3. 选择第一个数据集
    dataset_id = datasets[0]['id']
    print(f"\n3️⃣  使用数据集 ID: {dataset_id}")
    
    # 4. 获取样本集
    print("\n4️⃣  获取样本集列表...")
    sample_sets = get_sample_sets(token, dataset_id)
    
    if not sample_sets:
        print("❌ 该数据集没有样本集")
        return
    
    print(f"✅ 找到 {len(sample_sets)} 个样本集:")
    for ss in sample_sets:
        print(f"  - ID: {ss['id']}, 名称: {ss['name']}, 样本数: {ss.get('total_samples', 0)}")
    
    # 5. 选择要删除的样本集
    if len(sample_sets) < 2:
        print("\n⚠️  样本集数量少于2个,跳过批量删除测试")
        print("提示: 先生成一些样本集再测试批量删除")
        return
    
    # 选择前2个样本集进行删除
    sample_set_ids = [ss['id'] for ss in sample_sets[:2]]
    print(f"\n5️⃣  选择删除样本集: {sample_set_ids}")
    
    # 6. 执行批量删除
    print("\n6️⃣  执行批量删除...")
    success = batch_delete_sample_sets(token, sample_set_ids)
    
    # 7. 验证删除结果
    if success:
        print("\n7️⃣  验证删除结果...")
        remaining_sample_sets = get_sample_sets(token, dataset_id)
        print(f"✅ 剩余样本集数量: {len(remaining_sample_sets)}")
        
        # 检查被删除的样本集是否还存在
        remaining_ids = [ss['id'] for ss in remaining_sample_sets]
        deleted_ids = [sid for sid in sample_set_ids if sid not in remaining_ids]
        
        if len(deleted_ids) == len(sample_set_ids):
            print(f"✅ 所有选中的样本集都已删除")
        else:
            print(f"⚠️  部分样本集未删除: {set(sample_set_ids) - set(deleted_ids)}")
    
    # 8. 总结
    print("\n" + "=" * 60)
    if success:
        print("✅ 批量删除测试成功!")
    else:
        print("❌ 批量删除测试失败!")
    print("=" * 60)

if __name__ == "__main__":
    main()
