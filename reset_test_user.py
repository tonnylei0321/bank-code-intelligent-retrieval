"""重置测试用户密码"""
import sys
sys.path.insert(0, 'mvp')

from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

db = SessionLocal()

# 更新 testuser 密码
user = db.query(User).filter(User.username == "testuser").first()
if user:
    user.hashed_password = get_password_hash("test123")
    db.commit()
    print("✅ testuser 密码已重置为: test123")
else:
    print("❌ 用户不存在")

db.close()
