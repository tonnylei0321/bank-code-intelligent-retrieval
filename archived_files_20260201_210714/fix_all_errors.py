#!/usr/bin/env python3
"""
修复所有系统错误
"""
import os
import sys
import sqlite3
from datetime import datetime

def fix_database_issues():
    """修复数据库相关问题"""
    print("🔧 修复数据库问题...")
    
    db_path = "data/bank_code.db"
    if not os.path.exists(db_path):
        print("❌ 数据库文件不存在")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查user_qa_history表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='user_qa_history'
        """)
        
        if not cursor.fetchone():
            print("创建user_qa_history表...")
            cursor.execute("""
                CREATE TABLE user_qa_history (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    retrieval_strategy VARCHAR(20) NOT NULL DEFAULT 'intelligent',
                    model_type VARCHAR(50),
                    confidence_score FLOAT,
                    response_time INTEGER,
                    context_count INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX ix_user_qa_history_id ON user_qa_history (id)")
            cursor.execute("CREATE INDEX ix_user_qa_history_user_id ON user_qa_history (user_id)")
            print("✅ user_qa_history表创建完成")
        else:
            print("✅ user_qa_history表已存在")
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 数据库修复失败: {e}")
        return False

def fix_env_config():
    """修复环境配置"""
    print("🔧 修复环境配置...")
    
    env_file = ".env"
    if not os.path.exists(env_file):
        print("❌ .env文件不存在")
        return False
    
    try:
        with open(env_file, 'r') as f:
            content = f.read()
        
        # 检查是否需要添加API密钥配置
        changes_made = False
        
        if "OPENAI_API_KEY=" not in content:
            content += "\n# OpenAI API密钥（可选）\nOPENAI_API_KEY=\n"
            changes_made = True
        
        if "ANTHROPIC_API_KEY=" not in content:
            content += "\n# Anthropic API密钥（可选）\nANTHROPIC_API_KEY=\n"
            changes_made = True
        
        if changes_made:
            with open(env_file, 'w') as f:
                f.write(content)
            print("✅ 环境配置已更新")
        else:
            print("✅ 环境配置无需更新")
        
        return True
        
    except Exception as e:
        print(f"❌ 环境配置修复失败: {e}")
        return False

def check_services():
    """检查服务状态"""
    print("🔍 检查服务状态...")
    
    # 检查Redis
    try:
        import subprocess
        result = subprocess.run(['redis-cli', 'ping'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and 'PONG' in result.stdout:
            print("✅ Redis服务正常")
        else:
            print("⚠️ Redis服务未响应，请确保Redis已启动")
    except Exception as e:
        print(f"⚠️ 无法检查Redis状态: {e}")
    
    # 检查数据库
    db_path = "data/bank_code.db"
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM bank_codes")
            bank_count = cursor.fetchone()[0]
            conn.close()
            print(f"✅ 数据库正常 - 用户: {user_count}, 银行记录: {bank_count:,}")
        except Exception as e:
            print(f"⚠️ 数据库检查失败: {e}")
    else:
        print("❌ 数据库文件不存在")

def create_test_script():
    """创建测试脚本"""
    print("📝 创建测试脚本...")
    
    test_script = """#!/usr/bin/env python3
'''
系统错误修复验证脚本
'''
import requests
import json

def test_system():
    base_url = "http://localhost:8000"
    
    # 测试健康检查
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ 系统健康检查通过")
        else:
            print(f"⚠️ 系统健康检查异常: {response.status_code}")
    except Exception as e:
        print(f"❌ 无法连接到后端服务: {e}")
    
    # 测试登录
    try:
        response = requests.post(
            f"{base_url}/api/v1/auth/login",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data="username=admin&password=admin123",
            timeout=10
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            print("✅ 登录测试通过")
            
            # 测试智能问答
            headers = {"Authorization": f"Bearer {token}"}
            qa_response = requests.post(
                f"{base_url}/api/intelligent-qa/ask",
                headers=headers,
                json={
                    "question": "中国工商银行的联行号是什么？",
                    "retrieval_strategy": "redis",
                    "model_type": "local_model"
                },
                timeout=30
            )
            
            if qa_response.status_code == 200:
                print("✅ 智能问答测试通过")
            else:
                print(f"⚠️ 智能问答测试失败: {qa_response.status_code}")
                print(f"错误信息: {qa_response.text}")
        else:
            print(f"❌ 登录失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    print("🧪 系统错误修复验证")
    print("=" * 40)
    test_system()
"""
    
    with open("test_fixes.py", "w") as f:
        f.write(test_script)
    
    print("✅ 测试脚本已创建: test_fixes.py")

def main():
    print("🔧 系统错误修复工具")
    print("=" * 50)
    
    results = []
    
    # 修复数据库问题
    results.append(("数据库修复", fix_database_issues()))
    
    # 修复环境配置
    results.append(("环境配置修复", fix_env_config()))
    
    # 检查服务状态
    check_services()
    
    # 创建测试脚本
    create_test_script()
    
    # 总结结果
    print("\n" + "=" * 50)
    print("📊 修复结果总结:")
    
    success_count = 0
    for task, success in results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  - {task}: {status}")
        if success:
            success_count += 1
    
    print(f"\n总体结果: {success_count}/{len(results)} 项修复成功")
    
    if success_count == len(results):
        print("🎉 所有错误修复完成！")
        print("\n📋 后续步骤:")
        print("1. 重启后端服务: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
        print("2. 运行测试脚本: python test_fixes.py")
        print("3. 检查系统日志确认错误已解决")
    else:
        print("⚠️ 部分错误修复失败，请检查具体错误信息")

if __name__ == "__main__":
    main()