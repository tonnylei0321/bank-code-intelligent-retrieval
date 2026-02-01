#!/usr/bin/env python3
"""
测试split_sample_set函数
"""
import sys
sys.path.insert(0, 'mvp')

from app.core.database import SessionLocal
from app.models.qa_pair import QAPair
from app.models.sample_set import SampleSet

def test_split_sample_set():
    """测试样本集划分函数"""
    from mvp.app.api.sample_generation_async import split_sample_set
    
    db = SessionLocal()
    
    try:
        # 查找一个有样本的样本集
        sample_set = db.query(SampleSet).join(
            QAPair, QAPair.sample_set_id == SampleSet.id
        ).first()
        
        if not sample_set:
            print("❌ 没有找到包含样本的样本集")
            return
        
        print(f"✅ 找到样本集: {sample_set.name} (ID: {sample_set.id})")
        
        # 统计样本数
        qa_count = db.query(QAPair).filter(
            QAPair.sample_set_id == sample_set.id
        ).count()
        
        print(f"📊 样本数: {qa_count}")
        
        # 测试划分
        print("\n🔄 开始划分...")
        result = split_sample_set(
            db=db,
            sample_set_id=sample_set.id,
            train_ratio=0.8,
            val_ratio=0.1,
            test_ratio=0.1,
            random_seed=42
        )
        
        print(f"\n✅ 划分完成!")
        print(f"训练集: {result['train_count']}")
        print(f"验证集: {result['val_count']}")
        print(f"测试集: {result['test_count']}")
        print(f"总计: {result['train_count'] + result['val_count'] + result['test_count']}")
        
        # 验证
        total = result['train_count'] + result['val_count'] + result['test_count']
        if total == qa_count:
            print("\n✅ 验证通过: 划分数量正确")
        else:
            print(f"\n❌ 验证失败: 期望 {qa_count}, 实际 {total}")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("测试 split_sample_set 函数")
    print("=" * 60)
    test_split_sample_set()
