#!/usr/bin/env python3
"""
测试登录功能
"""
import sys
import os

# 添加mvp目录到Python路径
mvp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mvp')
sys.path.insert(0, mvp_path)
os.chdir(mvp_path)

from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import verify_password, get_password_hash

def test_login():
    """测试登录功能"""
    db = SessionLocal()
    
    try:
        # 查找admin用户
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            print("❌ 未找到admin用户")
            return
        
        print(f"✅ 找到用户: {admin_user.username}")
        print(f"角色: {admin_user.role}")
        print(f"激活状态: {admin_user.is_active}")
        
        # 测试密码验证
        test_password = "admin123456"
        is_valid = verify_password(test_password, admin_user.hashed_password)
        print(f"密码验证结果: {is_valid}")
        
        if not is_valid:
            print("❌ 密码验证失败，重新设置密码...")
            # 重新设置密码
            admin_user.hashed_password = get_password_hash(test_password)
            db.commit()
            print("✅ 密码已重新设置")
            
            # 再次验证
            is_valid = verify_password(test_password, admin_user.hashed_password)
            print(f"重新验证结果: {is_valid}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    test_login()