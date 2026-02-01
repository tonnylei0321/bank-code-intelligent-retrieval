#!/bin/bash

echo "🧹 开始清理冗余文件..."

# 1. 删除完成报告文档（✅ 开头）
echo "1️⃣ 删除完成报告文档..."
rm -f ✅*.md
echo "   ✅ 删除完成报告文档"

# 2. 删除修复报告文档（🔧 开头）
echo "2️⃣ 删除修复报告文档..."
rm -f 🔧*.md
echo "   ✅ 删除修复报告文档"

# 3. 删除状态报告文档（🎯 开头，保留核心脚本使用指南）
echo "3️⃣ 删除状态报告文档..."
find . -name "🎯*.md" -not -name "🎯核心脚本使用指南.md" -delete
echo "   ✅ 删除状态报告文档"

# 4. 删除其他冗余文档
echo "4️⃣ 删除其他冗余文档..."
rm -f 🔴*.md 🧠*.md 🧪*.md 🚀*.md 🟢*.md
rm -f 📊*.md 📋*.md 📦*.md 🔍*.md 👨‍💼*.md 🌐*.md
rm -f 🎉*.md 🎊*.md ⚡*.md
rm -f 中文化*.md 项目中文化*.md 前端*.md 训练*.md 如何*.md
rm -f 监控*.sh 清理*.sh 清理*.py 批量*.py 文件*.sh
echo "   ✅ 删除其他冗余文档"

# 5. 删除MVP目录下的冗余脚本
echo "5️⃣ 删除MVP冗余脚本..."
cd mvp

# 删除训练脚本（保留test_intelligent_training.py）
rm -f start_*_training.py
rm -f create_*_dataset.py
echo "   ✅ 删除训练脚本"

# 删除测试脚本（保留核心测试）
rm -f test_*_api.py test_*_direct.py test_*_generation.py
rm -f test_auth_manual.py test_llm_*.py test_upload_*.py
rm -f test_optimized_*.py test_parallel_*.py test_new_*.py
# 保留: test_intelligent_training.py, test_smart_generation.py, test_query_logging_fix.py
echo "   ✅ 删除冗余测试脚本"

# 删除生成和监控脚本
rm -f *_generation.py monitor_*.py debug_*.py force_*.py
rm -f stop_*.py quick_*.py quick_*.sh
echo "   ✅ 删除生成监控脚本"

# 删除验证和检查脚本
rm -f *_verification.py *_test.py load_*.py
rm -f checkpoint_*.py final_*.py detailed_*.py
echo "   ✅ 删除验证检查脚本"

# 删除测试数据库
rm -f test_*.db
echo "   ✅ 删除测试数据库"

# 删除冗余文档
rm -f *.md
rm -f run_*.sh start_*.sh
echo "   ✅ 删除MVP冗余文档"

cd ..

# 6. 删除根目录冗余脚本
echo "6️⃣ 删除根目录冗余脚本..."
rm -f test_memory_fix.sh test_smart_gen_simple.sh
rm -f connect_github.sh push_to_github.sh
rm -f create_test_user.sh reset_test_user.py
rm -f fix_mps_memory.sh start_with_memory_limit.sh
rm -f monitor_services.sh CLEANUP_SCRIPT.sh
echo "   ✅ 删除根目录冗余脚本"

# 7. 清理临时文件和缓存
echo "7️⃣ 清理临时文件..."
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
rm -rf temp/temp_files/*
echo "   ✅ 清理临时文件"

# 8. 统计清理结果
echo "8️⃣ 统计清理结果..."
echo ""
echo "🎉 清理完成!"
echo "=" * 50
echo "📊 保留的核心文件:"
echo ""
echo "🚀 服务管理:"
echo "   start_mvp_backend.sh"
echo "   start_frontend.sh" 
echo "   cleanup_and_restart.sh"
echo "   mvp/system_monitor.py"
echo ""
echo "🧪 测试验证:"
echo "   simple_test.sh"
echo "   test_api_endpoints.sh"
echo "   mvp/test_intelligent_training.py"
echo "   mvp/test_smart_generation.py"
echo "   mvp/test_query_logging_fix.py"
echo ""
echo "🔧 工具脚本:"
echo "   create_simple_user.py"
echo "   create_test_user.py"
echo ""
echo "📚 核心文档:"
echo "   README.md"
echo "   QUICKSTART.md"
echo "   🎯核心脚本使用指南.md"
echo ""
echo "✅ 项目文件已大幅精简，提高可维护性!"