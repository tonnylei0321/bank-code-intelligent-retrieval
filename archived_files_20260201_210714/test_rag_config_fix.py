#!/usr/bin/env python3
"""
测试RAG配置修复
验证权重参数的自动计算功能
"""

import requests
import json
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_rag_config_update():
    """测试RAG配置更新功能"""
    
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
    
    # 2. 获取当前配置
    print("\n2. 获取当前RAG配置...")
    try:
        response = requests.get(f"{base_url}/api/v1/rag/config", headers=headers)
        if response.status_code != 200:
            print(f"获取配置失败: {response.status_code} - {response.text}")
            return False
        
        response_data = response.json()
        current_config = response_data.get('config', response_data)
        print(f"✅ 当前配置获取成功")
        print(f"   vector_weight: {current_config.get('vector_weight', 'N/A')}")
        print(f"   keyword_weight: {current_config.get('keyword_weight', 'N/A')}")
        
    except Exception as e:
        print(f"❌ 获取配置失败: {e}")
        return False
    
    # 3. 测试只修改vector_weight
    print("\n3. 测试只修改vector_weight为0.7...")
    test_config = {"vector_weight": 0.7}
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/rag/config", 
            headers={**headers, "Content-Type": "application/json"},
            json=test_config
        )
        
        if response.status_code != 200:
            print(f"❌ 更新失败: {response.status_code} - {response.text}")
            return False
        
        result = response.json()
        print("✅ 更新成功")
        print(f"   vector_weight: {result['config'].get('vector_weight', 'N/A')}")
        print(f"   keyword_weight: {result['config'].get('keyword_weight', 'N/A')}")
        
        # 验证权重和是否为1.0
        v_weight = result['config'].get('vector_weight', 0)
        k_weight = result['config'].get('keyword_weight', 0)
        total = v_weight + k_weight
        print(f"   权重和: {total}")
        
        if abs(total - 1.0) > 0.01:
            print(f"❌ 权重和不等于1.0: {total}")
            return False
        
    except Exception as e:
        print(f"❌ 更新失败: {e}")
        return False
    
    # 4. 测试只修改keyword_weight
    print("\n4. 测试只修改keyword_weight为0.3...")
    test_config = {"keyword_weight": 0.3}
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/rag/config", 
            headers={**headers, "Content-Type": "application/json"},
            json=test_config
        )
        
        if response.status_code != 200:
            print(f"❌ 更新失败: {response.status_code} - {response.text}")
            return False
        
        result = response.json()
        print("✅ 更新成功")
        print(f"   vector_weight: {result['config'].get('vector_weight', 'N/A')}")
        print(f"   keyword_weight: {result['config'].get('keyword_weight', 'N/A')}")
        
        # 验证权重和是否为1.0
        v_weight = result['config'].get('vector_weight', 0)
        k_weight = result['config'].get('keyword_weight', 0)
        total = v_weight + k_weight
        print(f"   权重和: {total}")
        
        if abs(total - 1.0) > 0.01:
            print(f"❌ 权重和不等于1.0: {total}")
            return False
        
    except Exception as e:
        print(f"❌ 更新失败: {e}")
        return False
    
    # 5. 测试同时修改两个权重（和不等于1.0，应该失败）
    print("\n5. 测试同时修改两个权重（和不等于1.0，应该失败）...")
    test_config = {"vector_weight": 0.8, "keyword_weight": 0.3}  # 和为1.1
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/rag/config", 
            headers={**headers, "Content-Type": "application/json"},
            json=test_config
        )
        
        if response.status_code == 200:
            print(f"❌ 应该失败但成功了: {response.text}")
            return False
        else:
            print("✅ 正确拒绝了无效的权重组合")
        
    except Exception as e:
        print(f"✅ 正确拒绝了无效的权重组合: {e}")
    
    # 6. 测试同时修改两个权重（和等于1.0，应该成功）
    print("\n6. 测试同时修改两个权重（和等于1.0，应该成功）...")
    test_config = {"vector_weight": 0.8, "keyword_weight": 0.2}  # 和为1.0
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/rag/config", 
            headers={**headers, "Content-Type": "application/json"},
            json=test_config
        )
        
        if response.status_code != 200:
            print(f"❌ 更新失败: {response.status_code} - {response.text}")
            return False
        
        result = response.json()
        print("✅ 更新成功")
        print(f"   vector_weight: {result['config'].get('vector_weight', 'N/A')}")
        print(f"   keyword_weight: {result['config'].get('keyword_weight', 'N/A')}")
        
    except Exception as e:
        print(f"❌ 更新失败: {e}")
        return False
    
    print("\n🎉 所有测试通过！RAG配置修复成功！")
    return True

if __name__ == "__main__":
    success = test_rag_config_update()
    sys.exit(0 if success else 1)