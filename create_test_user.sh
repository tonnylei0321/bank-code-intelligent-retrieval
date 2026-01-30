#!/bin/bash

# 创建测试用户脚本

echo "正在创建测试用户..."

# 注册测试用户
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "test123456",
    "role": "user"
  }'

echo ""
echo ""
echo "测试用户创建完成！"
echo "用户名: testuser"
echo "密码: test123456"
echo ""
echo "现在可以在前端使用这些凭证登录了。"
