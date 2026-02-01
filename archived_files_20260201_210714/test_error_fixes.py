#!/usr/bin/env python3
"""
测试错误修复效果
"""
import requests
import json
import time

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

def test_intelligent_qa_service(token):
    """测试智能问答服务"""
    print("🔍 测试智能问答服务...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 测试智能问答
    response = requests.post(
        f"{BASE_URL}/api/intelligent-qa/ask",
        headers=headers,
        json={
            "question": "中国工商银行的联行号是什么？",
            "retrieval_strategy": "redis",
            "model_type": "local_model"
        }
    )
    
    print(f"智能问答响应状态: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("✅ 智能问答服务正常")
        print(f"  - 答案: {data.get('answer', 'N/A')[:100]}...")
        print(f"  - 检索策略: {data.get('retrieval_strategy', 'N/A')}")
        print(f"  - 响应时间: {data.get('response_time', 'N/A')}s")
    else:
        print(f"❌ 智能问答服务错误: {response.text}")
    
    return response.status_code == 200

def test_user_history(token):
    """测试用户历史记录"""
    print("\n🔍 测试用户历史记录...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 获取用户历史
    response = requests.get(
        f"{BASE_URL}/api/intelligent-qa/history",
        headers=headers
    )
    
    print(f"历史记录响应状态: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("✅ 用户历史记录服务正常")
        print(f"  - 历史记录数量: {len(data)}")
        if data:
            print(f"  - 最新记录: {data[0].get('question', 'N/A')[:50]}...")
        else:
            print("  - 暂无历史记录")
    else:
        print(f"❌ 用户历史记录错误: {response.text}")
    
    return response.status_code == 200

def test_database_health():
    """测试数据库健康状态"""
    print("\n🔍 测试数据库健康状态...")
    
    import sqlite3
    import os
    
    db_path = "mvp/data/bank_code.db"
    if not os.path.exists(db_path):
        print("❌ 数据库文件不存在")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查新表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='user_qa_history'
        """)
        
        if cursor.fetchone():
            print("✅ user_qa_history 表存在")
            
            # 检查表结构
            cursor.execute("PRAGMA table_info(user_qa_history)")
            columns = cursor.fetchall()
            print(f"  - 字段数量: {len(columns)}")
            
            # 检查记录数
            cursor.execute("SELECT COUNT(*) FROM user_qa_history")
            count = cursor.fetchone()[0]
            print(f"  - 记录数量: {count}")
            
        else:
            print("❌ user_qa_history 表不存在")
            return False
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 数据库检查失败: {e}")
        return False

def test_api_key_handling():
    """测试API密钥处理"""
    print("\n🔍 测试API密钥处理...")
    
    # 检查配置文件
    env_file = "mvp/.env"
    try:
        with open(env_file, 'r') as f:
            content = f.read()
        
        if "QWEN_API_KEY=" in content:
            print("✅ QWEN_API_KEY 配置项存在")
        else:
            print("❌ QWEN_API_KEY 配置项缺失")
            return False
        
        # 检查是否有实际值（不是默认值）
        import re
        match = re.search(r'QWEN_API_KEY=(.+)', content)
        if match:
            value = match.group(1).strip()
            if value and not value.startswith('your_') and not value.startswith('#'):
                print("✅ QWEN_API_KEY 已配置实际值")
            else:
                print("⚠️ QWEN_API_KEY 使用默认值或被注释")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置文件检查失败: {e}")
        return False

def main():
    print("🔧 测试错误修复效果")
    print("=" * 50)
    
    # 登录
    token = login()
    if not token:
        print("❌ 无法登录，终止测试")
        return
    
    print("✅ 登录成功")
    
    # 测试各个修复项
    results = {}
    
    results['intelligent_qa'] = test_intelligent_qa_service(token)
    results['user_history'] = test_user_history(token)
    results['database'] = test_database_health()
    results['api_key'] = test_api_key_handling()
    
    # 总结结果
    print("\n" + "=" * 50)
    print("📊 修复效果总结:")
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  - {test_name}: {status}")
    
    success_count = sum(results.values())
    total_count = len(results)
    
    print(f"\n总体结果: {success_count}/{total_count} 项测试通过")
    
    if success_count == total_count:
        print("🎉 所有错误修复验证通过！")
    else:
        print("⚠️ 部分错误仍需进一步修复")

if __name__ == "__main__":
    main()