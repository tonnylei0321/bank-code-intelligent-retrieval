#!/usr/bin/env python3
"""创建简单测试用户"""
import sqlite3
import bcrypt

# 连接数据库
conn = sqlite3.connect('mvp/data/bank_code.db')
cursor = conn.cursor()

# 删除现有用户
cursor.execute("DELETE FROM users WHERE username IN ('testuser', 'admin')")

# 创建密码哈希
test_password = bcrypt.hashpw("test123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
admin_password = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# 插入新用户
cursor.execute("""
INSERT INTO users (username, email, hashed_password, role, is_active, created_at, updated_at)
VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
""", ('testuser', 'test@example.com', test_password, 'user', 1))

cursor.execute("""
INSERT INTO users (username, email, hashed_password, role, is_active, created_at, updated_at)
VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
""", ('admin', 'admin@example.com', admin_password, 'admin', 1))

conn.commit()
conn.close()

print("✅ 用户创建成功！")
print("测试用户: testuser / test123")
print("管理员: admin / admin123")