#!/usr/bin/env python3
"""
检查数据库中是否存在西单支行
"""
import os
import sys

# 设置环境变量
os.environ['SECRET_KEY'] = 'test-secret-key'
os.environ['DATABASE_URL'] = 'sqlite:///./data/bank_code.db'

from app.core.database import get_db
from app.models.bank_code import BankCode

def main():
    db = next(get_db())
    try:
        print("搜索包含'西单'的银行...")
        
        # 搜索包含"西单"的银行
        results = db.query(BankCode).filter(
            BankCode.bank_name.contains("西单")
        ).all()
        
        print(f"找到 {len(results)} 个包含'西单'的银行:")
        for i, bank in enumerate(results):
            print(f"  {i+1}. {bank.bank_name} -> {bank.bank_code}")
        
        print("\n" + "="*50)
        print("搜索包含'工商银行'和'北京'的银行...")
        
        # 搜索工商银行北京的支行
        icbc_beijing = db.query(BankCode).filter(
            BankCode.bank_name.contains("工商银行"),
            BankCode.bank_name.contains("北京")
        ).limit(10).all()
        
        print(f"找到 {len(icbc_beijing)} 个工商银行北京支行（显示前10个）:")
        for i, bank in enumerate(icbc_beijing):
            print(f"  {i+1}. {bank.bank_name} -> {bank.bank_code}")
            
        print("\n" + "="*50)
        print("搜索包含'工商银行'和'西'的银行...")
        
        # 搜索工商银行包含"西"的支行
        icbc_xi = db.query(BankCode).filter(
            BankCode.bank_name.contains("工商银行"),
            BankCode.bank_name.contains("西")
        ).limit(10).all()
        
        print(f"找到 {len(icbc_xi)} 个工商银行包含'西'的支行（显示前10个）:")
        for i, bank in enumerate(icbc_xi):
            print(f"  {i+1}. {bank.bank_name} -> {bank.bank_code}")
            
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()