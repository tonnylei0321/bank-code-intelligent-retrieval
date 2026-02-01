#!/bin/bash

# 项目清理脚本
# 清理临时文件、测试文件和过时的报告文档

echo "🧹 开始清理项目空间..."

# 创建备份目录
BACKUP_DIR="archived_files_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "📦 备份目录: $BACKUP_DIR"

# 1. 清理根目录下的测试脚本
echo ""
echo "1️⃣ 清理测试脚本..."
TEST_SCRIPTS=(
    "test_api_endpoints.sh"
    "test_api_intelligent_qa.py"
    "test_api_transaction.py"
    "test_cleanup_script.sh"
    "test_dataset_centric_sample_management.py"
    "test_dataset_preview.py"
    "test_direct_db_delete.py"
    "test_error_fixes.py"
    "test_frontend_login.py"
    "test_frontend_upload.py"
    "test_intelligent_qa_api.py"
    "test_intelligent_qa_fix.py"
    "test_intelligent_qa_with_redis.py"
    "test_llm_generation.py"
    "test_login.py"
    "test_redis_api_fix.py"
    "test_redis_data_loading.py"
    "test_redis_page_fix.py"
    "test_sample_detail_view.py"
    "test_sample_generation_complete.py"
    "test_sample_generation_datasets.py"
    "test_sample_generation_error_fix.py"
    "test_sample_generation_fix.py"
    "test_sample_generation_real_usage.py"
    "test_sample_generation_restart.py"
    "test_sample_generation_ui_fix.py"
    "test_sample_management_api.py"
    "test_unl_upload.py"
    "test_upload_fix.py"
    "simple_test.sh"
)

for file in "${TEST_SCRIPTS[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" "$BACKUP_DIR/"
        echo "  ✓ 移动: $file"
    fi
done

# 2. 清理临时测试数据
echo ""
echo "2️⃣ 清理测试数据..."
TEST_DATA=(
    "test_preview_data.csv"
    "test_sample.unl"
    "test_upload_page.html"
    "T_BANK_LINE_NO_ICBC_ALL.unl"
)

for file in "${TEST_DATA[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" "$BACKUP_DIR/"
        echo "  ✓ 移动: $file"
    fi
done

# 3. 清理调试脚本
echo ""
echo "3️⃣ 清理调试脚本..."
DEBUG_SCRIPTS=(
    "debug_redis_search.py"
    "debug_sample_generation.py"
    "check_dataset.py"
    "check_mps.py"
    "system_monitor.py"
)

for file in "${DEBUG_SCRIPTS[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" "$BACKUP_DIR/"
        echo "  ✓ 移动: $file"
    fi
done

# 4. 清理修复脚本（已完成的）
echo ""
echo "4️⃣ 清理已完成的修复脚本..."
FIX_SCRIPTS=(
    "fix_intelligent_qa_search.py"
    "fix_sample_generation_api_key.py"
    "fix_user_password.py"
    "create_simple_user.py"
    "create_test_user.py"
    "quick_sample_generation_test.py"
    "quick_test_sample_generation.py"
)

for file in "${FIX_SCRIPTS[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" "$BACKUP_DIR/"
        echo "  ✓ 移动: $file"
    fi
done

# 5. 整理过时的报告文档（保留最新的）
echo ""
echo "5️⃣ 整理过时的报告文档..."
OLD_REPORTS=(
    "✅样本生成错误修复完成报告.md"
    "✅样本生成UI双Tab页面完成报告.md"
    "✅样本生成UI优化完成报告.md"
    "🔧系统监控和错误排除完成报告.md"
    "🎨前端菜单重构完成报告.md"
    "🎨前端界面美化完成报告.md"
    "🎨前端现代化设计完成报告.md"
    "🔧登录问题修复完成报告.md"
    "🔧后台错误修复完成.md"
    "🔧前端编译错误修复完成报告.md"
    "🔧前端运行时错误修复完成报告.md"
    "🔧数据集预览功能修复完成报告.md"
    "🔧样本管理API错误修复完成报告.md"
    "🔧Redis页面错误修复完成报告.md"
    "🔧UNL文件格式支持完成报告.md"
    "🔧UNL文件上传问题修复报告.md"
    "智能问答系统测试完成报告.md"
    "智能问答RAG开关功能说明.md"
    "智能问答RAG开关功能验证完成报告.md"
    "Redis文件上传功能使用指南.md"
    "Redis文件上传过滤功能测试报告.md"
    "🎉样本生成功能修复成功.md"
    "✅数据管理页面选择功能修复完成.md"
    "✅样本管理页面重构完成报告.md"
    "✅样本生成系统完整复用和增强完成报告.md"
    "✅样本生成功能完整修复总结.md"
    "✅样本生成历史记录功能实现完成.md"
    "✅样本详情查看功能实现完成报告.md"
    "🎯样本生成进度查看指南.md"
    "📊样本生成进度显示说明.md"
    "📝样本生成历史记录使用说明.md"
    "🔧后端服务重启说明.md"
    "🔍系统状态检查报告.md"
    "🎯项目中文化工作完成.txt"
    "FILES_TO_COMMENT_AND_TRANSLATE.md"
    "TRANSLATION_GUIDE.md"
)

for file in "${OLD_REPORTS[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" "$BACKUP_DIR/"
        echo "  ✓ 移动: $file"
    fi
done

# 6. 清理过时的技术报告
echo ""
echo "6️⃣ 清理过时的技术报告..."
OLD_TECH_REPORTS=(
    "RAG_CONFIG_FIX_REPORT.md"
    "RAG_CONFIG_UPDATE_FIX_REPORT.md"
    "RAG_SYSTEM_FIX_REPORT.md"
    "PROJECT_ANALYSIS_REPORT.md"
    "IMPLEMENTATION_ROADMAP.md"
    "GITHUB_SETUP_GUIDE.md"
)

for file in "${OLD_TECH_REPORTS[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" "$BACKUP_DIR/"
        echo "  ✓ 移动: $file"
    fi
done

# 7. 清理重复的启动脚本（保留主要的）
echo ""
echo "7️⃣ 清理重复的启动脚本..."
REDUNDANT_SCRIPTS=(
    "cleanup_and_restart.sh"
    "cleanup_redundant_files.sh"
    "start_backend.sh"
    "start_frontend.sh"
    "start_mvp_backend.sh"
)

for file in "${REDUNDANT_SCRIPTS[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" "$BACKUP_DIR/"
        echo "  ✓ 移动: $file"
    fi
done

# 8. 清理 .DS_Store 文件
echo ""
echo "8️⃣ 清理系统文件..."
find . -name ".DS_Store" -type f -delete
echo "  ✓ 删除所有 .DS_Store 文件"

# 9. 清理 mvp 目录下的测试文件
echo ""
echo "9️⃣ 清理 mvp 目录下的测试文件..."
MVP_TEST_FILES=(
    "mvp/test_banks_100.unl"
    "mvp/test_banks_sample.unl"
    "mvp/test_filter_mixed.unl"
    "mvp/test_filter_sample.unl"
    "mvp/quick_fix.py"
    "mvp/real_time_monitor.py"
    "mvp/fix_all_errors.py"
    "mvp/fix_training_jobs_schema.py"
    "mvp/fix_database_schema.py"
    "mvp/fix_priority_field.py"
    "mvp/fix_rag_database.py"
    "mvp/delete_training_jobs.py"
    "mvp/debug_entity_extraction.py"
    "mvp/debug_full_retrieval.py"
    "mvp/debug_rag_issue.py"
    "mvp/debug_rag_xidan.py"
    "mvp/test_xidan_query.py"
    "mvp/test_rag_config.py"
    "mvp/test_rag_config_fix.py"
    "mvp/test_rag_direct.py"
    "mvp/test_rag_fix.py"
    "mvp/test_rag_optimization.py"
    "mvp/test_rag_performance.py"
    "mvp/test_rag_retrieval_with_config.py"
    "mvp/test_rag_simple.py"
    "mvp/test_rag_simple_fix.py"
    "mvp/test_rag_standalone.py"
    "mvp/test_sample_generation.py"
    "mvp/test_specific_query.py"
    "mvp/test_system_checkpoint.py"
    "mvp/test_training_management.py"
    "mvp/test_full_name_query.py"
    "mvp/test_intelligent_qa_simple.py"
    "mvp/test_intelligent_qa_switch.py"
    "mvp/test_intelligent_training.py"
    "mvp/test_optimized_answer_generation.py"
    "mvp/test_query_logging_fix.py"
    "mvp/test_fallback_analysis.py"
    "mvp/test_file_upload.py"
    "mvp/test_fixes.py"
    "mvp/check_xidan_branch.py"
    "mvp/check_xidan_data.py"
    "mvp/analyze_rag_performance.py"
    "mvp/add_smart_generation_fields.py"
    "mvp/install_rag_dependencies.py"
    "mvp/migrate_add_user_qa_history.py"
    "mvp/start_intelligent_qa.sh"
    "mvp/start_training_with_memory_fix.py"
    "mvp/system_monitor.py"
    "mvp/test_auth.py"
    "mvp/upload_test_data_via_api.py"
)

for file in "${MVP_TEST_FILES[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" "$BACKUP_DIR/"
        echo "  ✓ 移动: $file"
    fi
done

# 10. 清理 mvp 目录下的报告文档
echo ""
echo "🔟 清理 mvp 目录下的报告文档..."
MVP_REPORTS=(
    "mvp/RAG_CONFIG_IMPLEMENTATION_SUMMARY.md"
    "mvp/RAG_OPTIMIZATION_REPORT.md"
    "mvp/TRAINING_SYSTEM_ENHANCEMENT_SUMMARY.md"
)

for file in "${MVP_REPORTS[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" "$BACKUP_DIR/"
        echo "  ✓ 移动: $file"
    fi
done

# 11. 清理空的或临时的目录
echo ""
echo "1️⃣1️⃣ 清理临时目录..."
if [ -d "temp/cache" ] && [ -z "$(ls -A temp/cache)" ]; then
    rmdir temp/cache
    echo "  ✓ 删除空目录: temp/cache"
fi

if [ -d "temp/temp_files" ] && [ -z "$(ls -A temp/temp_files)" ]; then
    rmdir temp/temp_files
    echo "  ✓ 删除空目录: temp/temp_files"
fi

# 12. 清理前端未使用的页面
echo ""
echo "1️⃣2️⃣ 清理前端未使用的页面..."
UNUSED_FRONTEND=(
    "frontend/src/pages/SampleManagement.tsx"
    "frontend/src/pages/SampleGenerationManagement.tsx"
    "frontend/src/pages/SampleGeneration.tsx"
)

for file in "${UNUSED_FRONTEND[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" "$BACKUP_DIR/"
        echo "  ✓ 移动: $file"
    fi
done

# 统计
echo ""
echo "📊 清理统计:"
MOVED_COUNT=$(ls -1 "$BACKUP_DIR" 2>/dev/null | wc -l)
echo "  • 已移动文件数: $MOVED_COUNT"
echo "  • 备份位置: $BACKUP_DIR"

echo ""
echo "✅ 清理完成！"
echo ""
echo "💡 提示:"
echo "  • 所有文件已移动到备份目录，未直接删除"
echo "  • 如需恢复，可从备份目录中找回"
echo "  • 确认无误后，可手动删除备份目录: rm -rf $BACKUP_DIR"
echo ""
