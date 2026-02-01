#!/usr/bin/env python3
"""
创建测试用户脚本
"""
import sys
import os

# 添加mvp目录到Python路径
mvp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mvp')
sys.path.insert(0, mvp_path)
os.chdir(mvp_path)

from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

def create_test_users():
    """创建测试用户"""
    db = SessionLocal()
    
    try:
        # 检查是否已存在测试用户
        existing_user = db.query(User).filter(User.username == "testuser").first()
        if existing_user:
            print("测试用户 'testuser' 已存在")
            print(f"用户名: testuser")
            print(f"邮箱: {existing_user.email}")
            print(f"角色: {existing_user.role}")
        else:
            # 创建普通测试用户
            test_user = User(
                username="testuser",
                email="test@example.com",
                hashed_password=get_password_hash("test123456"),
                role="user",
                is_active=1
            )
            db.add(test_user)
            print("✅ 创建测试用户成功")
            print(f"用户名: testuser")
            print(f"密码: test123456")
            print(f"角色: user")
        
        print()
        
        # 检查是否已存在管理员用户
        existing_admin = db.query(User).filter(User.username == "admin").first()
        if not existing_admin:
            # 创建管理员用户
            admin_user = User(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("admin123456"),
                role="admin",
                is_active=1
            )
            db.add(admin_user)
            db.commit()
            print("✅ 创建管理员用户成功")
            print(f"用户名: admin")
            print(f"密码: admin123456")
            print(f"角色: admin")
        else:
            print("管理员用户 'admin' 已存在")
            print(f"用户名: admin")
            print(f"邮箱: {existing_admin.email}")
            print(f"角色: {existing_admin.role}")
        
        print()
        print("现在可以在前端使用这些凭证登录了：")
        print("- 前端地址: http://localhost:3000")
        print("- 测试用户: testuser / test123456")
        print("- 管理员: admin / admin123456")
        
    except Exception as e:
        print(f"❌ 创建用户失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_users()
