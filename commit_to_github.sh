#!/bin/bash

echo "=========================================="
echo "📦 准备提交到GitHub"
echo "=========================================="

# 添加所有新文件和修改
echo ""
echo "📝 1. 添加所有更改..."
git add .

# 查看状态
echo ""
echo "📊 2. 查看提交状态..."
git status --short | head -20
echo "..."
echo "（显示前20行，完整列表请运行 git status）"

# 创建提交信息
COMMIT_MSG="✨ 大模型提示词管理功能完成

主要更新:
- ✅ 实现LLM提示词模板管理功能
- ✅ 支持三个大模型提供商（通义千问/DeepSeek/火山引擎）
- ✅ 支持四种问题类型（精确/模糊/反向/自然语言）
- ✅ 前端页面完整实现（查看/编辑/重置）
- ✅ 样本生成集成数据库提示词
- ✅ 三层样本管理结构（数据集→样本集→样本）
- ✅ 异步样本生成功能
- ✅ 菜单结构优化（样本管理子菜单）
- ✅ 项目文件清理和归档
- ✅ 完整的文档和测试脚本

技术细节:
- 新增数据库表: llm_prompt_templates, sample_sets
- 新增API端点: /api/v1/llm-prompt-templates, /api/v1/sample-sets
- 新增前端页面: LLMPromptManagement.tsx
- 优化TeacherModelAPI支持数据库提示词
- 完善的迁移脚本和测试工具

文档:
- ✅大模型提示词管理功能实现完成.md
- 🎯大模型提示词管理使用指南.md
- 🎯最终验证步骤.md
- 其他20+个功能文档和指南"

# 提交
echo ""
echo "💾 3. 创建提交..."
git commit -m "$COMMIT_MSG"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 提交成功！"
    
    # 推送到GitHub
    echo ""
    echo "🚀 4. 推送到GitHub..."
    git push origin main
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "=========================================="
        echo "✅ 成功推送到GitHub！"
        echo "=========================================="
        echo ""
        echo "📝 提交信息:"
        echo "$COMMIT_MSG"
        echo ""
        echo "🔗 查看仓库:"
        git remote get-url origin
    else
        echo ""
        echo "❌ 推送失败，请检查网络连接和权限"
        echo ""
        echo "💡 手动推送命令:"
        echo "   git push origin main"
    fi
else
    echo ""
    echo "❌ 提交失败"
    echo ""
    echo "💡 可能的原因:"
    echo "   - 没有更改需要提交"
    echo "   - Git配置问题"
    echo ""
    echo "💡 手动提交命令:"
    echo "   git add ."
    echo "   git commit -m \"你的提交信息\""
    echo "   git push origin main"
fi
