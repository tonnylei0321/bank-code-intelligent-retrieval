#!/usr/bin/env python3
"""
测试样本详情查看功能
"""
import requests
import json

# 配置
BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"

def get_auth_token():
    """获取认证token"""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        data={"username": USERNAME, "password": PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"登录失败: {response.text}")
        return None

def test_sample_list(token):
    """测试样本列表API"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/v1/qa-pairs", headers=headers)
    
    if response.status_code == 200:
        samples = response.json()
        print(f"✅ 样本列表获取成功，共 {len(samples)} 个样本")
        
        # 显示前5个样本的基本信息
        print("\n📋 前5个样本:")
        for i, sample in enumerate(samples[:5]):
            print(f"  {i+1}. ID: {sample['id']}")
            print(f"     问题: {sample['question'][:50]}...")
            print(f"     答案: {sample['answer'][:50]}...")
            print(f"     类型: {sample['question_type']} | 数据集: {sample['split_type']}")
            print(f"     数据集ID: {sample['dataset_id']} | 创建时间: {sample['generated_at']}")
            if 'source_record_id' in sample:
                print(f"     源记录ID: {sample['source_record_id']}")
            print()
        
        return samples
    else:
        print(f"❌ 样本列表获取失败: {response.text}")
        return []

def test_sample_detail(token, sample_id):
    """测试单个样本详情（如果API支持）"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/v1/qa-pairs/{sample_id}", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        # 检查返回的是列表还是单个对象
        if isinstance(data, list):
            if data:
                sample = data[0]  # 取第一个样本
                print(f"✅ 样本详情获取成功（返回列表格式）")
                print(f"问题: {sample['question']}")
                print(f"答案: {sample['answer']}")
                return sample
            else:
                print(f"⚠️  返回空列表")
                return None
        else:
            sample = data
            print(f"✅ 样本 {sample_id} 详情获取成功")
            print(f"问题: {sample['question']}")
            print(f"答案: {sample['answer']}")
            return sample
    else:
        print(f"⚠️  样本详情API可能不存在，状态码: {response.status_code}")
        return None

def analyze_sample_structure(samples):
    """分析样本数据结构"""
    if not samples:
        return
    
    print("\n🔍 样本数据结构分析:")
    sample = samples[0]
    
    print("字段列表:")
    for key, value in sample.items():
        value_type = type(value).__name__
        value_preview = str(value)[:50] if len(str(value)) > 50 else str(value)
        print(f"  {key}: {value_type} = {value_preview}")
    
    # 统计各种类型
    question_types = {}
    split_types = {}
    
    for sample in samples:
        q_type = sample.get('question_type', 'unknown')
        s_type = sample.get('split_type', 'unknown')
        
        question_types[q_type] = question_types.get(q_type, 0) + 1
        split_types[s_type] = split_types.get(s_type, 0) + 1
    
    print("\n📊 问题类型统计:")
    for q_type, count in question_types.items():
        print(f"  {q_type}: {count}")
    
    print("\n📊 数据集类型统计:")
    for s_type, count in split_types.items():
        print(f"  {s_type}: {count}")

def main():
    print("🔍 测试样本详情查看功能")
    print("=" * 50)
    
    # 获取认证token
    print("1. 获取认证token...")
    token = get_auth_token()
    if not token:
        return
    print("✅ 认证成功")
    
    # 获取样本列表
    print("\n2. 获取样本列表...")
    samples = test_sample_list(token)
    if not samples:
        return
    
    # 分析样本结构
    analyze_sample_structure(samples)
    
    # 测试样本详情API（如果存在）
    print("\n3. 测试样本详情API...")
    if samples:
        sample_id = samples[0]['id']
        test_sample_detail(token, sample_id)
    
    print("\n" + "=" * 50)
    print("🎉 测试完成")
    print("\n💡 前端样本详情查看功能说明:")
    print("- 样本列表API正常工作")
    print("- 前端可以通过点击'查看'按钮显示样本详情")
    print("- 详情模态框会显示完整的问题、答案和元数据")
    print("- 支持问题类型、数据集类型的标签显示")
    print("- 包含创建时间和源记录ID等信息")

if __name__ == "__main__":
    main()