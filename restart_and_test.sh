#!/bin/bash

echo "=========================================="
echo "后端服务重启和测试脚本"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 检查数据库迁移
echo -e "\n${YELLOW}1️⃣  检查数据库迁移...${NC}"
if [ -f "mvp/data/bank_code.db" ]; then
    # 检查sample_sets表是否存在
    TABLE_EXISTS=$(sqlite3 mvp/data/bank_code.db "SELECT name FROM sqlite_master WHERE type='table' AND name='sample_sets';" 2>/dev/null)
    if [ -z "$TABLE_EXISTS" ]; then
        echo -e "${RED}❌ sample_sets表不存在，需要运行迁移${NC}"
        echo -e "${YELLOW}运行迁移脚本...${NC}"
        cd mvp && python migrate_add_sample_sets.py
        cd ..
    else
        echo -e "${GREEN}✅ 数据库迁移已完成${NC}"
    fi
else
    echo -e "${RED}❌ 数据库文件不存在${NC}"
    exit 1
fi

# 2. 查找并停止后端服务
echo -e "\n${YELLOW}2️⃣  停止后端服务...${NC}"
PID=$(ps aux | grep "uvicorn.*app.main" | grep -v grep | awk '{print $2}')
if [ -n "$PID" ]; then
    echo -e "${YELLOW}找到进程 PID: $PID${NC}"
    kill $PID
    sleep 2
    echo -e "${GREEN}✅ 后端服务已停止${NC}"
else
    echo -e "${YELLOW}⚠️  后端服务未运行${NC}"
fi

# 3. 启动后端服务
echo -e "\n${YELLOW}3️⃣  启动后端服务...${NC}"
cd mvp
nohup ./venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info > backend.log 2>&1 &
BACKEND_PID=$!
cd ..

echo -e "${GREEN}✅ 后端服务已启动 (PID: $BACKEND_PID)${NC}"
echo -e "${YELLOW}等待服务启动...${NC}"
sleep 5

# 4. 检查服务是否启动成功
echo -e "\n${YELLOW}4️⃣  检查服务状态...${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs 2>/dev/null)
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ 后端服务运行正常${NC}"
else
    echo -e "${RED}❌ 后端服务启动失败 (HTTP $HTTP_CODE)${NC}"
    echo -e "${YELLOW}查看日志: tail -f mvp/backend.log${NC}"
    exit 1
fi

# 5. 运行测试
echo -e "\n${YELLOW}5️⃣  运行测试...${NC}"
echo -e "${YELLOW}----------------------------------------${NC}"
python test_complete_generation.py
TEST_RESULT=$?
echo -e "${YELLOW}----------------------------------------${NC}"

# 6. 总结
echo -e "\n=========================================="
if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ 所有测试通过！${NC}"
    echo -e "${GREEN}系统已就绪，可以提交给用户验证${NC}"
else
    echo -e "${RED}❌ 测试失败！${NC}"
    echo -e "${YELLOW}请检查错误日志: tail -f mvp/logs/error_2026-02-01.log${NC}"
fi
echo -e "==========================================\n"

exit $TEST_RESULT
