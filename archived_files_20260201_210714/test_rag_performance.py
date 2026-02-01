#!/usr/bin/env python3
"""
测试RAG检索性能
"""

import requests
import json
import time
import sys
import os

def test_rag_performance():
    """测试RAG检索性能"""
    
    base_url = "http://localhost:8000"
    
    # 1. 登录获取token
    print("1. 登录获取token...")
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(f"{base_url}/api/v1/auth/login", data=login_data)
        if response.status_code != 200:
            print(f"登录失败: {response.status_code} - {response.text}")
            return False
        
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ 登录成功")
        
    except Exception as e:
        print(f"❌ 登录失败: {e}")
        return False
    
    # 测试用例
    test_cases = [
        {
            "name": "完整银行名称查询",
            "query": "中国工商银行股份有限公司北京西单支行",
            "expected_first": "中国工商银行股份有限公司北京西单支行"
        },
        {
            "name": "简化银行查询",
            "query": "工商银行西单",
            "expected_first": "中国工商银行股份有限公司北京西单支行"
        },
        {
            "name": "地理位置查询",
            "query": "西单",
            "expected_contains": "西单"
        },
        {
            "name": "银行类型查询",
            "query": "建设银行",
            "expected_contains": "建设银行"
        },
        {
            "name": "复合查询",
            "query": "北京农业银行",
            "expected_contains": "农业银行"
        }
    ]
    
    print(f"\n2. 开始性能测试（{len(test_cases)}个测试用例）...")
    
    total_time = 0
    success_count = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n   测试 {i}: {test_case['name']}")
        print(f"   查询: {test_case['query']}")
        
        # 执行查询
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{base_url}/api/v1/rag/search", 
                headers={**headers, "Content-Type": "application/json"},
                json={
                    "question": test_case['query'],
                    "top_k": 5,
                    "similarity_threshold": 0.3
                }
            )
            
            end_time = time.time()
            query_time = end_time - start_time
            total_time += query_time
            
            if response.status_code != 200:
                print(f"   ❌ 查询失败: {response.status_code}")
                continue
            
            result = response.json()
            print(f"   ⏱️  耗时: {query_time:.2f}秒")
            print(f"   📊 结果数: {result['total_found']}")
            
            if result['results']:
                first_result = result['results'][0]['bank_name']
                print(f"   🥇 第一个结果: {first_result}")
                
                # 验证结果正确性
                if 'expected_first' in test_case:
                    if test_case['expected_first'] in first_result:
                        print(f"   ✅ 结果正确")
                        success_count += 1
                    else:
                        print(f"   ❌ 结果不匹配，期望: {test_case['expected_first']}")
                elif 'expected_contains' in test_case:
                    if test_case['expected_contains'] in first_result:
                        print(f"   ✅ 结果包含期望内容")
                        success_count += 1
                    else:
                        print(f"   ❌ 结果不包含期望内容: {test_case['expected_contains']}")
            else:
                print(f"   ❌ 没有找到结果")
                
        except Exception as e:
            print(f"   ❌ 查询异常: {e}")
            continue
    
    # 性能总结
    avg_time = total_time / len(test_cases)
    success_rate = (success_count / len(test_cases)) * 100
    
    print(f"\n📊 性能测试总结:")
    print(f"   总测试用例: {len(test_cases)}")
    print(f"   成功用例: {success_count}")
    print(f"   成功率: {success_rate:.1f}%")
    print(f"   总耗时: {total_time:.2f}秒")
    print(f"   平均耗时: {avg_time:.2f}秒")
    
    # 性能评估
    print(f"\n🎯 性能评估:")
    if avg_time < 1.0:
        print(f"   🚀 优秀 - 平均响应时间 < 1秒")
    elif avg_time < 3.0:
        print(f"   ✅ 良好 - 平均响应时间 < 3秒")
    elif avg_time < 5.0:
        print(f"   ⚠️  一般 - 平均响应时间 < 5秒")
    else:
        print(f"   ❌ 需要优化 - 平均响应时间 > 5秒")
    
    if success_rate >= 80:
        print(f"   🎯 准确性优秀 - 成功率 >= 80%")
    elif success_rate >= 60:
        print(f"   ✅ 准确性良好 - 成功率 >= 60%")
    else:
        print(f"   ❌ 准确性需要改进 - 成功率 < 60%")
    
    return avg_time < 5.0 and success_rate >= 60

if __name__ == "__main__":
    success = test_rag_performance()
    sys.exit(0 if success else 1)