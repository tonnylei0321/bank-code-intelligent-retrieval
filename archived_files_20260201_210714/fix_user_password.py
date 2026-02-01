#!/usr/bin/env python3
"""
修复用户密码
"""
import sys
import os

# 添加mvp目录到Python路径
mvp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mvp')
sys.path.insert(0, mvp_path)
os.chdir(mvp_path)

from app.core.database import SessionLocal
from app.models.user import User
import bcrypt

def fix_user_passwords():
    """修复用户密码"""
    db = SessionLocal()
    
    try:
        # 查找所有用户
        users = db.query(User).all()
        
        for user in users:
            print(f"处理用户: {user.username}")
            
            # 使用简单的密码
            if user.username == "admin":
                password = "admin123456"
            else:
                password = "test123456"
            
            # 使用bcrypt直接加密
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            user.hashed_password = hashed.decode('utf-8')
            
            print(f"✅ 已更新 {user.username} 的密码")
        
        db.commit()
        print("✅ 所有用户密码已更新")
        
        # 验证密码
        print("\n验证密码:")
        for user in users:
            if user.username == "admin":
                test_password = "admin123456"
            else:
                test_password = "test123456"
            
            is_valid = bcrypt.checkpw(test_password.encode('utf-8'), user.hashed_password.encode('utf-8'))
            print(f"{user.username}: {is_valid}")
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_user_passwords()