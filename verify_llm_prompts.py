#!/usr/bin/env python3
"""
验证LLM提示词模板功能
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mvp'))

from app.core.database import SessionLocal
from app.models.llm_prompt_template import LLMPromptTemplate

def main():
    print("=" * 60)
    print("LLM提示词模板验证")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # 统计总数
        total = db.query(LLMPromptTemplate).count()
        print(f"\n📊 总计: {total} 个模板")
        
        # 按提供商统计
        print("\n📋 按提供商分组:")
        for provider in ['qwen', 'deepseek', 'volces']:
            count = db.query(LLMPromptTemplate).filter(
                LLMPromptTemplate.provider == provider
            ).count()
            provider_name = {
                'qwen': '通义千问',
                'deepseek': 'DeepSeek',
                'volces': '火山引擎'
            }[provider]
            print(f"  - {provider_name}: {count} 个")
        
        # 按问题类型统计
        print("\n📋 按问题类型分组:")
        for qtype in ['exact', 'fuzzy', 'reverse', 'natural']:
            count = db.query(LLMPromptTemplate).filter(
                LLMPromptTemplate.question_type == qtype
            ).count()
            qtype_name = {
                'exact': '精确查询',
                'fuzzy': '模糊查询',
                'reverse': '反向查询',
                'natural': '自然语言'
            }[qtype]
            print(f"  - {qtype_name}: {count} 个")
        
        # 显示所有模板
        print("\n📝 所有模板详情:")
        templates = db.query(LLMPromptTemplate).order_by(
            LLMPromptTemplate.provider,
            LLMPromptTemplate.question_type
        ).all()
        
        for t in templates:
            status = "✅ 启用" if t.is_active else "❌ 禁用"
            default = "⭐ 默认" if t.is_default else "📝 自定义"
            print(f"\n  ID: {t.id}")
            print(f"  提供商: {t.provider}")
            print(f"  问题类型: {t.question_type}")
            print(f"  状态: {status}")
            print(f"  类型: {default}")
            print(f"  描述: {t.description or '无'}")
            print(f"  模板预览: {t.template[:80]}...")
        
        print("\n" + "=" * 60)
        print("✅ 验证完成！")
        print("=" * 60)
        
        print("\n📝 前端访问步骤:")
        print("1. 访问 http://localhost:3000")
        print("2. 登录 (admin/admin123)")
        print("3. 点击「样本管理」展开菜单")
        print("4. 点击「大模型提示词管理」")
        print("5. 应该看到 12 个模板")
        print("\n💡 提示:")
        print("- 如果看不到模板，点击「刷新」按钮")
        print("- 如果菜单没有子项，硬刷新浏览器 (Cmd+Shift+R)")
        print("- 初始化按钮显示 0 个是正常的，因为模板已存在")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
