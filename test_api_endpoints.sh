#!/bin/bash

echo "=========================================="
echo "  API端点测试脚本"
echo "=========================================="
echo ""

BASE_URL="http://localhost:8000"

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试函数
test_endpoint() {
    local name=$1
    local url=$2
    local method=${3:-GET}
    
    echo -n "测试 $name ... "
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$url")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$url")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "${GREEN}✓ 成功${NC} (HTTP $http_code)"
        echo "$body" | python3 -m json.tool 2>/dev/null | head -10
    else
        echo -e "${RED}✗ 失败${NC} (HTTP $http_code)"
        echo "$body"
    fi
    echo ""
}

echo "1. 测试健康检查端点"
test_endpoint "健康检查" "$BASE_URL/health"

echo "2. 测试API文档"
echo -n "测试 API文档 ... "
if curl -s "$BASE_URL/docs" | grep -q "Swagger"; then
    echo -e "${GREEN}✓ 成功${NC}"
    echo "API文档可访问: $BASE_URL/docs"
else
    echo -e "${YELLOW}⚠ 警告${NC}"
    echo "API文档可能不可用"
fi
echo ""

echo "3. 测试认证端点"
echo "尝试登录（使用默认管理员账号）..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123")

echo "$LOGIN_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$LOGIN_RESPONSE"
echo ""

# 提取token
TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('access_token', ''))" 2>/dev/null)

if [ -n "$TOKEN" ]; then
    echo -e "${GREEN}✓ 登录成功，获取到访问令牌${NC}"
    echo ""
    
    echo "4. 测试需要认证的端点"
    echo "获取当前用户信息..."
    curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/users/me" | python3 -m json.tool 2>/dev/null
    echo ""
    
    echo "5. 测试数据集列表"
    curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/datasets?page=1&size=10" | python3 -m json.tool 2>/dev/null | head -20
    echo ""
else
    echo -e "${RED}✗ 登录失败，无法测试需要认证的端点${NC}"
fi

echo "=========================================="
echo "  测试完成"
echo "=========================================="
echo ""
echo "可用的API端点："
echo "  - 健康检查: $BASE_URL/health"
echo "  - API文档: $BASE_URL/docs"
echo "  - ReDoc文档: $BASE_URL/redoc"
echo "  - 登录: POST $BASE_URL/api/auth/login"
echo "  - 用户信息: GET $BASE_URL/api/users/me"
echo "  - 数据集列表: GET $BASE_URL/api/datasets"
echo ""
