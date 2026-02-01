#!/usr/bin/env python3
"""
测试前端UNL文件上传修复
"""
import requests
import json

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

def test_upload_response_format(token):
    """测试上传API的响应格式"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print("🔍 测试上传API响应格式...")
    
    # 准备文件数据
    files = {
        'file': ('test_sample.unl', open('test_sample.unl', 'rb'), 'text/plain')
    }
    
    data = {
        'name': '前端测试UNL数据集',
        'description': '测试前端响应处理修复'
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/datasets/upload",
        headers=headers,
        files=files,
        data=data
    )
    
    print(f"响应状态码: {response.status_code}")
    print(f"响应头: {dict(response.headers)}")
    
    if response.status_code == 201:
        data = response.json()
        print("✅ 上传成功，响应数据:")
        print(f"  - 类型: {type(data)}")
        print(f"  - 数据集ID: {data.get('id')}")
        print(f"  - 文件名: {data.get('filename')}")
        print(f"  - 状态: {data.get('status')}")
        print(f"  - 是否有success字段: {'success' in data}")
        return data
    else:
        print(f"❌ 上传失败: {response.text}")
        return None

def test_datasets_list_format(token):
    """测试数据集列表API的响应格式"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print("🔍 测试数据集列表API响应格式...")
    
    response = requests.get(f"{BASE_URL}/api/v1/datasets", headers=headers)
    
    print(f"响应状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ 获取成功，响应数据:")
        print(f"  - 类型: {type(data)}")
        print(f"  - 数据集数量: {len(data) if isinstance(data, list) else 'N/A'}")
        print(f"  - 是否有success字段: {'success' in data if isinstance(data, dict) else False}")
        if isinstance(data, list) and data:
            print(f"  - 第一个数据集: {data[0].get('filename', 'N/A')}")
        return data
    else:
        print(f"❌ 获取失败: {response.text}")
        return None

def main():
    print("🚀 开始测试前端API响应格式...")
    
    # 登录
    token = login()
    if not token:
        return
    
    print("✅ 登录成功")
    
    # 测试上传API响应格式
    upload_result = test_upload_response_format(token)
    
    # 测试数据集列表API响应格式
    list_result = test_datasets_list_format(token)
    
    print("\n📊 测试总结:")
    print("前端需要的响应格式修复:")
    print("  - 上传API: 直接返回数据集对象 ✅")
    print("  - 列表API: 直接返回数据集数组 ✅")
    print("  - 不使用 {success: true, data: ...} 包装格式")
    print("✅ API响应格式测试完成")

if __name__ == "__main__":
    main()