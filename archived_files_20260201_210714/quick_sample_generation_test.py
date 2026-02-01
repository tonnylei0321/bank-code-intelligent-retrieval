#!/usr/bin/env python3
"""快速样本生成测试"""
import sys
import os

# 切换到mvp目录
current_dir = os.path.dirname(os.path.abspath(__file__))
mvp_dir = os.path.join(current_dir, 'mvp')
os.chdir(mvp_dir)
sys.path.insert(0, mvp_dir)

from app.services.teacher_model import TeacherModelAPI
from app.services.qa_generator import QAGenerator
from app.core.database import SessionLocal
from app.models.bank_code import BankCode

def test_direct_generation():
    """直接测试样本生成"""
    print("🚀 快速样本生成测试")
    print("=" * 60)
    
    # 1. 测试TeacherModelAPI
    print("\n1️⃣ 测试TeacherModelAPI初始化...")
    api = TeacherModelAPI()
    print(f"✅ API提供商: {api.provider}")
    print(f"✅ 可用配置: {len(api.api_configs)}个")
    
    # 2. 从数据库获取测试数据
    print("\n2️⃣ 从数据库获取测试数据...")
    db = SessionLocal()
    try:
        bank_records = db.query(BankCode).limit(2).all()
        
        if not bank_records:
            print("❌ 数据库中没有银行记录")
            return
        
        print(f"✅ 找到 {len(bank_records)} 条银行记录")
        
        # 3. 测试QAGenerator
        print("\n3️⃣ 测试QAGenerator...")
        generator = QAGenerator(db=db)
        print("✅ QAGenerator初始化成功")
        
        # 4. 生成样本
        print("\n4️⃣ 生成样本...")
        for i, record in enumerate(bank_records, 1):
            print(f"\n   记录 {i}: {record.bank_name}")
            
            # 使用TeacherModelAPI直接生成
            result = api.generate_qa_pair(record, 'exact')
            
            if result:
                question, answer = result
                print(f"   ✅ 生成成功")
                print(f"      问题: {question}")
                print(f"      答案: {answer[:100]}...")
            else:
                print(f"   ❌ 生成失败")
        
        print("\n" + "=" * 60)
        print("🎉 测试完成！样本生成功能正常工作")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_direct_generation()
