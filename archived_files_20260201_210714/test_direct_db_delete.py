#!/usr/bin/env python3
"""
直接测试数据库删除操作
"""

import sys
import os

# 切换到mvp目录
os.chdir('mvp')
sys.path.insert(0, '.')

def test_direct_delete():
    """直接测试数据库删除操作"""
    from app.core.database import SessionLocal
    from app.models.qa_pair import QAPair
    
    db = SessionLocal()
    
    try:
        # 查询现有的QA pairs
        qa_pairs = db.query(QAPair).limit(5).all()
        print(f"找到 {len(qa_pairs)} 个QA pairs")
        
        if qa_pairs:
            # 选择第一个进行删除测试
            test_qa = qa_pairs[0]
            test_id = test_qa.id
            print(f"准备删除QA pair ID: {test_id}")
            
            # 删除操作
            db.delete(test_qa)
            db.commit()
            print(f"✅ 删除操作已提交")
            
            # 验证删除
            remaining = db.query(QAPair).filter(QAPair.id == test_id).first()
            if remaining is None:
                print(f"✅ 验证成功：QA pair {test_id} 已被删除")
            else:
                print(f"❌ 验证失败：QA pair {test_id} 仍然存在")
            
            # 统计剩余数量
            total_count = db.query(QAPair).count()
            print(f"剩余QA pairs总数: {total_count}")
        else:
            print("没有找到QA pairs进行测试")
            
    except Exception as e:
        print(f"❌ 删除操作失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    test_direct_delete()