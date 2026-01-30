#!/bin/bash

echo "🧪 测试智能样本生成器"
echo ""

cd mvp
source venv/bin/activate

python3 test_smart_generation.py

deactivate
cd ..
