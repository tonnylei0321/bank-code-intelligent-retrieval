#!/usr/bin/env python3
"""
检查数据库中是否存在工商银行西单支行
"""

import sqlite3
import sys
import os

def check_xidan_data():
    """检查西单相关的银行数据"""
    
    db_path = "data/bank_code.db"
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 检查所有包含"西单"的银行
        print("1. 检查所有包含'西单'的银行:")
        cursor.execute("""
            SELECT bank_name, bank_code, clearing_code 
            FROM bank_codes 
            WHERE bank_name LIKE '%西单%' 
            ORDER BY bank_name
        """)
        
        results = cursor.fetchall()
        if results:
            for bank_name, bank_code, clearing_code in results:
                print(f"   {bank_name}")
                print(f"   联行号: {bank_code}")
                print(f"   清算代码: {clearing_code or 'N/A'}")
                print()
        else:
            print("   ❌ 没有找到包含'西单'的银行")
        
        # 2. 检查工商银行的所有北京支行
        print("\n2. 检查工商银行的北京支行（前20个）:")
        cursor.execute("""
            SELECT bank_name, bank_code 
            FROM bank_codes 
            WHERE bank_name LIKE '%工商银行%' 
            AND bank_name LIKE '%北京%'
            ORDER BY bank_name
            LIMIT 20
        """)
        
        results = cursor.fetchall()
        if results:
            for bank_name, bank_code in results:
                print(f"   {bank_name} - {bank_code}")
        else:
            print("   ❌ 没有找到工商银行北京支行")
        
        # 3. 模糊搜索工商银行西单相关
        print("\n3. 模糊搜索工商银行西单相关:")
        cursor.execute("""
            SELECT bank_name, bank_code 
            FROM bank_codes 
            WHERE bank_name LIKE '%工商银行%' 
            AND (bank_name LIKE '%西单%' OR bank_name LIKE '%西%')
            ORDER BY bank_name
        """)
        
        results = cursor.fetchall()
        if results:
            for bank_name, bank_code in results:
                print(f"   {bank_name} - {bank_code}")
        else:
            print("   ❌ 没有找到工商银行西单相关支行")
        
        # 4. 统计各银行的数量
        print("\n4. 统计各主要银行的数量:")
        banks = [
            "工商银行",
            "农业银行", 
            "建设银行",
            "中国银行",
            "交通银行"
        ]
        
        for bank in banks:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM bank_codes 
                WHERE bank_name LIKE ?
            """, (f'%{bank}%',))
            
            count = cursor.fetchone()[0]
            print(f"   {bank}: {count} 个")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 数据库查询失败: {e}")
        return False

if __name__ == "__main__":
    success = check_xidan_data()
    sys.exit(0 if success else 1)