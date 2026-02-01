#!/usr/bin/env python3
"""
测试Redis文件上传功能

测试文件上传、解析和Redis加载功能
"""

import requests
import json
import os
from pathlib import Path

# 配置
BASE_URL = "http://localhost:8000"
TEST_FILE_PATH = "../data/T_BANK_LINE_NO_ICBC_ALL.unl"

def get_auth_token():
    """获取认证token"""
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"登录失败: {response.text}")

def test_file_upload():
    """测试文件上传功能"""
    print("🧪 测试Redis文件上传功能")
    print("=" * 50)
    
    try:
        # 获取认证token
        print("1️⃣ 获取认证token...")
        token = get_auth_token()
        print("   ✅ 认证成功")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # 检查测试文件
        if not os.path.exists(TEST_FILE_PATH):
            print(f"   ❌ 测试文件不存在: {TEST_FILE_PATH}")
            return
        
        print(f"2️⃣ 准备上传文件: {TEST_FILE_PATH}")
        file_size = os.path.getsize(TEST_FILE_PATH)
        print(f"   📊 文件大小: {file_size / 1024 / 1024:.2f} MB")
        
        # 上传文件
        print("3️⃣ 上传文件到Redis管理API...")
        with open(TEST_FILE_PATH, 'rb') as f:
            files = {'file': (os.path.basename(TEST_FILE_PATH), f, 'text/plain')}
            data = {'force_reload': 'false'}
            
            response = requests.post(
                f"{BASE_URL}/api/redis/upload-file",
                files=files,
                data=data,
                headers=headers
            )
        
        if response.status_code == 200:
            result = response.json()
            print("   ✅ 文件上传成功")
            print(f"   📊 上传结果:")
            print(f"      - 文件名: {result['data']['filename']}")
            print(f"      - 文件大小: {result['data']['file_size'] / 1024 / 1024:.2f} MB")
            print(f"      - 解析记录数: {result['data']['parsed_count']}")
            print(f"      - 保存记录数: {result['data']['saved_count']}")
            print(f"      - Redis更新: {'成功' if result['data']['redis_updated'] else '失败'}")
            print(f"      - 处理时间: {result['data']['processing_time']:.2f}秒")
            
            # 显示示例数据
            if result['data']['sample_data']:
                print("   📋 示例数据:")
                for i, bank in enumerate(result['data']['sample_data'][:3], 1):
                    print(f"      {i}. {bank['bank_name']} ({bank['bank_code']})")
        else:
            print(f"   ❌ 文件上传失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return
        
        # 测试Redis搜索
        print("4️⃣ 测试Redis搜索功能...")
        search_response = requests.get(
            f"{BASE_URL}/api/redis/search",
            params={"query": "工商银行", "limit": 5},
            headers=headers
        )
        
        if search_response.status_code == 200:
            search_result = search_response.json()
            print(f"   ✅ 搜索成功，找到 {search_result['data']['count']} 条记录")
            
            for i, bank in enumerate(search_result['data']['results'][:3], 1):
                print(f"      {i}. {bank['bank_name']} ({bank['bank_code']})")
        else:
            print(f"   ⚠️ 搜索测试失败: {search_response.status_code}")
        
        # 获取Redis统计信息
        print("5️⃣ 获取Redis统计信息...")
        stats_response = requests.get(
            f"{BASE_URL}/api/redis/stats",
            headers=headers
        )
        
        if stats_response.status_code == 200:
            stats = stats_response.json()['data']
            print("   ✅ 统计信息获取成功")
            print(f"   📊 Redis统计:")
            print(f"      - 银行总数: {stats['total_banks']}")
            print(f"      - 内存使用: {stats['memory_usage']}")
            print(f"      - 键总数: {stats['key_statistics']['total_keys']}")
            print(f"      - 最后更新: {stats['last_updated']}")
        else:
            print(f"   ⚠️ 统计信息获取失败: {stats_response.status_code}")
        
        print("\n🎉 文件上传功能测试完成!")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def test_file_preview():
    """测试文件预览功能"""
    print("\n🔍 测试文件预览功能")
    print("=" * 30)
    
    try:
        # 获取认证token
        token = get_auth_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # 创建测试文件
        test_content = """102290002916|中国工商银行股份有限公司上海市西虹桥支行|102290002916
102290002924|中国工商银行股份有限公司上海市徐汇支行|102290002924
102290002932|中国工商银行股份有限公司上海市黄浦支行|102290002932"""
        
        test_file_path = "test_banks.unl"
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        print(f"📄 创建测试文件: {test_file_path}")
        
        # 预览文件
        with open(test_file_path, 'rb') as f:
            files = {'file': (test_file_path, f, 'text/plain')}
            data = {'lines': '10'}
            
            response = requests.get(
                f"{BASE_URL}/api/redis/parse-preview",
                files=files,
                data=data,
                headers=headers
            )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 文件预览成功")
            print(f"📊 预览结果:")
            print(f"   - 总行数: {result['data']['total_lines']}")
            print(f"   - 解析记录数: {result['data']['parsed_count']}")
            print(f"   - 预览记录数: {result['data']['preview_count']}")
            
            print("📋 预览数据:")
            for bank in result['data']['preview_data']:
                print(f"   {bank['line_number']}. {bank['bank_name']} ({bank['bank_code']})")
        else:
            print(f"❌ 文件预览失败: {response.status_code}")
            print(f"错误信息: {response.text}")
        
        # 清理测试文件
        os.remove(test_file_path)
        print(f"🧹 清理测试文件: {test_file_path}")
        
    except Exception as e:
        print(f"❌ 预览测试失败: {e}")

if __name__ == "__main__":
    test_file_upload()
    test_file_preview()