#!/usr/bin/env python3
"""
测试LLM提示词管理功能
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mvp'))

import requests
import json

# 配置
BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"

def login():
    """登录获取token"""
    print("🔐 登录...")
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

def test_init_defaults(token):
    """测试初始化默认模板"""
    print("\n📝 测试初始化默认模板...")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.post(
        f"{BASE_URL}/api/v1/llm-prompt-templates/init-defaults",
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ {result['message']}")
        return True
    else:
        print(f"❌ 初始化失败: {response.text}")
        return False

def test_list_templates(token):
    """测试获取模板列表"""
    print("\n📋 测试获取模板列表...")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{BASE_URL}/api/v1/llm-prompt-templates",
        headers=headers
    )
    
    if response.status_code == 200:
        templates = response.json()
        print(f"✅ 获取到 {len(templates)} 个模板")
        
        # 按提供商分组统计
        providers = {}
        for t in templates:
            provider = t['provider']
            if provider not in providers:
                providers[provider] = 0
            providers[provider] += 1
        
        for provider, count in providers.items():
            print(f"   - {provider}: {count} 个模板")
        
        return templates
    else:
        print(f"❌ 获取失败: {response.text}")
        return []

def test_get_template(token, template_id):
    """测试获取单个模板"""
    print(f"\n🔍 测试获取模板 {template_id}...")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{BASE_URL}/api/v1/llm-prompt-templates/{template_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        template = response.json()
        print(f"✅ 获取成功")
        print(f"   提供商: {template['provider']}")
        print(f"   问题类型: {template['question_type']}")
        print(f"   状态: {'启用' if template['is_active'] else '禁用'}")
        return template
    else:
        print(f"❌ 获取失败: {response.text}")
        return None

def test_update_template(token, template_id):
    """测试更新模板"""
    print(f"\n✏️  测试更新模板 {template_id}...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "description": "测试更新的描述",
        "is_active": True
    }
    
    response = requests.put(
        f"{BASE_URL}/api/v1/llm-prompt-templates/{template_id}",
        headers=headers,
        json=data
    )
    
    if response.status_code == 200:
        print(f"✅ 更新成功")
        return True
    else:
        print(f"❌ 更新失败: {response.text}")
        return False

def test_reset_template(token, template_id):
    """测试重置模板"""
    print(f"\n🔄 测试重置模板 {template_id}...")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.post(
        f"{BASE_URL}/api/v1/llm-prompt-templates/{template_id}/reset",
        headers=headers
    )
    
    if response.status_code == 200:
        print(f"✅ 重置成功")
        return True
    else:
        print(f"❌ 重置失败: {response.text}")
        return False

def test_filter_templates(token):
    """测试过滤模板"""
    print("\n🔍 测试过滤模板...")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 按提供商过滤
    print("   测试按提供商过滤 (qwen)...")
    response = requests.get(
        f"{BASE_URL}/api/v1/llm-prompt-templates?provider=qwen",
        headers=headers
    )
    
    if response.status_code == 200:
        templates = response.json()
        print(f"   ✅ 获取到 {len(templates)} 个qwen模板")
    else:
        print(f"   ❌ 过滤失败")
    
    # 按问题类型过滤
    print("   测试按问题类型过滤 (exact)...")
    response = requests.get(
        f"{BASE_URL}/api/v1/llm-prompt-templates?question_type=exact",
        headers=headers
    )
    
    if response.status_code == 200:
        templates = response.json()
        print(f"   ✅ 获取到 {len(templates)} 个exact类型模板")
    else:
        print(f"   ❌ 过滤失败")

def main():
    """主测试流程"""
    print("=" * 60)
    print("LLM提示词管理功能测试")
    print("=" * 60)
    
    # 登录
    token = login()
    if not token:
        print("\n❌ 测试失败：无法登录")
        return
    
    # 初始化默认模板
    if not test_init_defaults(token):
        print("\n⚠️  初始化失败，但继续测试...")
    
    # 获取模板列表
    templates = test_list_templates(token)
    if not templates:
        print("\n❌ 测试失败：无法获取模板列表")
        return
    
    # 获取第一个模板的详情
    if templates:
        template_id = templates[0]['id']
        test_get_template(token, template_id)
        
        # 更新模板
        test_update_template(token, template_id)
        
        # 重置模板
        test_reset_template(token, template_id)
    
    # 测试过滤
    test_filter_templates(token)
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)
    print("\n📝 后续步骤:")
    print("1. 在浏览器中访问 http://localhost:3000")
    print("2. 登录后进入「样本管理」->「大模型提示词管理」")
    print("3. 查看、编辑和重置提示词模板")
    print("4. 测试样本生成功能，验证提示词是否生效")

if __name__ == "__main__":
    main()
