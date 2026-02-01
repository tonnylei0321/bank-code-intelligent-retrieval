#!/usr/bin/env python3
"""
快速错误修复工具
根据检测到的错误类型，提供快速修复方案
"""
import os
import sys
import subprocess
import sqlite3
from datetime import datetime

class QuickFix:
    def __init__(self):
        self.fixes = {
            "restart_backend": self.restart_backend,
            "restart_redis": self.restart_redis,
            "check_database": self.check_database,
            "clear_logs": self.clear_logs,
            "fix_permissions": self.fix_permissions,
            "check_api_keys": self.check_api_keys
        }
    
    def restart_backend(self):
        """重启后端服务"""
        print("🔄 重启后端服务...")
        try:
            # 停止现有服务
            subprocess.run(['pkill', '-f', 'uvicorn'], capture_output=True)
            
            # 启动新服务
            cmd = "source venv/bin/activate && nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > backend.log 2>&1 &"
            subprocess.run(cmd, shell=True, cwd=".")
            
            print("✅ 后端服务重启完成")
            return True
        except Exception as e:
            print(f"❌ 后端服务重启失败: {e}")
            return False
    
    def restart_redis(self):
        """重启Redis服务"""
        print("🔄 重启Redis服务...")
        try:
            subprocess.run(['redis-cli', 'shutdown'], capture_output=True)
            subprocess.run(['redis-server', '--daemonize', 'yes'], capture_output=True)
            print("✅ Redis服务重启完成")
            return True
        except Exception as e:
            print(f"❌ Redis服务重启失败: {e}")
            return False
    
    def check_database(self):
        """检查数据库状态"""
        print("🔍 检查数据库状态...")
        db_path = "data/bank_code.db"
        
        if not os.path.exists(db_path):
            print("❌ 数据库文件不存在")
            return False
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 检查主要表
            tables = ['users', 'datasets', 'bank_codes', 'training_jobs', 'user_qa_history']
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  ✅ {table}: {count:,} 条记录")
            
            conn.close()
            print("✅ 数据库状态正常")
            return True
            
        except Exception as e:
            print(f"❌ 数据库检查失败: {e}")
            return False
    
    def clear_logs(self):
        """清理日志文件"""
        print("🧹 清理日志文件...")
        try:
            log_files = [
                "backend.log",
                "logs/app_2026-02-01.log",
                "logs/error_2026-02-01.log"
            ]
            
            for log_file in log_files:
                if os.path.exists(log_file):
                    # 备份大文件
                    if os.path.getsize(log_file) > 50 * 1024 * 1024:  # 50MB
                        backup_name = f"{log_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        os.rename(log_file, backup_name)
                        print(f"  📦 备份大文件: {backup_name}")
                    else:
                        # 清空小文件
                        open(log_file, 'w').close()
                        print(f"  🧹 清空文件: {log_file}")
            
            print("✅ 日志清理完成")
            return True
            
        except Exception as e:
            print(f"❌ 日志清理失败: {e}")
            return False
    
    def fix_permissions(self):
        """修复文件权限"""
        print("🔧 修复文件权限...")
        try:
            # 修复关键目录权限
            dirs = ["data", "logs", "uploads", "models"]
            for dir_name in dirs:
                if os.path.exists(dir_name):
                    subprocess.run(['chmod', '-R', '755', dir_name], capture_output=True)
                    print(f"  ✅ 修复权限: {dir_name}")
            
            print("✅ 权限修复完成")
            return True
            
        except Exception as e:
            print(f"❌ 权限修复失败: {e}")
            return False
    
    def check_api_keys(self):
        """检查API密钥配置"""
        print("🔑 检查API密钥配置...")
        
        env_file = ".env"
        if not os.path.exists(env_file):
            print("❌ .env文件不存在")
            return False
        
        try:
            with open(env_file, 'r') as f:
                content = f.read()
            
            keys = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'QWEN_API_KEY']
            for key in keys:
                if f"{key}=" in content:
                    # 检查是否有实际值
                    import re
                    match = re.search(rf"{key}=(.+)", content)
                    if match and match.group(1).strip() and not match.group(1).strip().startswith('#'):
                        print(f"  ✅ {key}: 已配置")
                    else:
                        print(f"  ⚠️ {key}: 未配置或被注释")
                else:
                    print(f"  ❌ {key}: 缺失")
            
            return True
            
        except Exception as e:
            print(f"❌ API密钥检查失败: {e}")
            return False
    
    def run_fix(self, fix_name):
        """运行指定的修复"""
        if fix_name in self.fixes:
            return self.fixes[fix_name]()
        else:
            print(f"❌ 未知的修复类型: {fix_name}")
            return False
    
    def list_fixes(self):
        """列出可用的修复选项"""
        print("🔧 可用的快速修复选项:")
        fixes_desc = {
            "restart_backend": "重启后端服务",
            "restart_redis": "重启Redis服务", 
            "check_database": "检查数据库状态",
            "clear_logs": "清理日志文件",
            "fix_permissions": "修复文件权限",
            "check_api_keys": "检查API密钥配置"
        }
        
        for fix_name, desc in fixes_desc.items():
            print(f"  - {fix_name}: {desc}")

def main():
    if len(sys.argv) < 2:
        print("用法: python quick_fix.py <fix_name>")
        print("或者: python quick_fix.py list")
        return
    
    fixer = QuickFix()
    
    if sys.argv[1] == "list":
        fixer.list_fixes()
    else:
        fix_name = sys.argv[1]
        success = fixer.run_fix(fix_name)
        if success:
            print(f"🎉 修复 '{fix_name}' 完成")
        else:
            print(f"❌ 修复 '{fix_name}' 失败")

if __name__ == "__main__":
    main()