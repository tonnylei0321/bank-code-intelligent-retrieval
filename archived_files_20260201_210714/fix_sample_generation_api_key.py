#!/usr/bin/env python3
"""
修复样本生成API密钥问题
创建一个不依赖外部API的本地样本生成方案
"""
import os
import sys
import random
from datetime import datetime
from sqlalchemy import func

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'mvp'))

from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.bank_code import BankCode
from app.models.qa_pair import QAPair
from app.models.dataset import Dataset

def create_local_qa_generator():
    """创建本地问答生成器"""
    
    # 问题模板
    question_templates = {
        "exact": [
            "{bank_name}的联行号是什么？",
            "请问{bank_name}的银行代码是多少？",
            "{bank_name}的清算代码是什么？",
            "我需要{bank_name}的联行号信息",
        ],
        "fuzzy": [
            "{bank_name}的代码",
            "{bank_name}联行号",
            "查询{bank_name}",
            "{bank_name}银行信息",
        ],
        "reverse": [
            "{bank_code}是哪个银行的联行号？",
            "联行号{bank_code}对应哪家银行？",
            "银行代码{bank_code}是什么银行？",
            "这个联行号{bank_code}属于哪个银行？",
        ],
        "natural": [
            "我想查询{bank_name}的联行号信息",
            "请帮我找一下{bank_name}的银行代码",
            "能告诉我{bank_name}的清算代码吗？",
            "我需要办理业务，请问{bank_name}的联行号是多少？",
        ]
    }
    
    def generate_answer(bank_record: BankCode, question: str, question_type: str) -> str:
        """生成答案"""
        if question_type == "reverse":
            return f"联行号{bank_record.bank_code}属于{bank_record.bank_name}。"
        else:
            answer_parts = [f"{bank_record.bank_name}的相关信息如下："]
            answer_parts.append(f"联行号：{bank_record.bank_code}")
            
            if bank_record.clearing_code and bank_record.clearing_code != bank_record.bank_code:
                answer_parts.append(f"清算代码：{bank_record.clearing_code}")
            
            return "\n".join(answer_parts)
    
    return question_templates, generate_answer

def generate_qa_pairs_for_dataset(dataset_id: int, max_records: int = 100):
    """为数据集生成问答对"""
    print(f"🔄 开始为数据集 {dataset_id} 生成问答对...")
    
    # 获取数据库会话
    db = next(get_db())
    
    try:
        # 检查数据集
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            print(f"❌ 数据集 {dataset_id} 不存在")
            return
        
        print(f"📊 数据集: {dataset.filename}")
        
        # 获取银行记录
        bank_records = db.query(BankCode)\
            .filter(BankCode.dataset_id == dataset_id)\
            .limit(max_records)\
            .all()
        
        if not bank_records:
            print(f"❌ 数据集 {dataset_id} 中没有银行记录")
            return
        
        print(f"📝 找到 {len(bank_records)} 条银行记录")
        
        # 删除现有的问答对
        existing_count = db.query(QAPair).filter(QAPair.dataset_id == dataset_id).count()
        if existing_count > 0:
            print(f"🗑️  删除现有的 {existing_count} 个问答对")
            db.query(QAPair).filter(QAPair.dataset_id == dataset_id).delete()
            db.commit()
        
        # 创建本地生成器
        question_templates, generate_answer = create_local_qa_generator()
        
        # 生成问答对
        total_generated = 0
        question_types = ["exact", "fuzzy", "reverse", "natural"]
        split_types = ["train", "val", "test"]
        
        for i, bank_record in enumerate(bank_records):
            print(f"🔄 处理记录 {i+1}/{len(bank_records)}: {bank_record.bank_name}")
            
            # 为每种问题类型生成1-2个问答对
            for question_type in question_types:
                templates = question_templates[question_type]
                num_questions = random.randint(1, 2)
                
                for _ in range(num_questions):
                    try:
                        # 选择模板
                        template = random.choice(templates)
                        
                        # 生成问题
                        if question_type == "reverse":
                            question = template.format(bank_code=bank_record.bank_code)
                        else:
                            question = template.format(bank_name=bank_record.bank_name)
                        
                        # 生成答案
                        answer = generate_answer(bank_record, question, question_type)
                        
                        # 随机分配数据集类型
                        split_type = random.choices(
                            split_types, 
                            weights=[0.8, 0.1, 0.1]  # 80% train, 10% val, 10% test
                        )[0]
                        
                        # 创建问答对
                        qa_pair = QAPair(
                            dataset_id=dataset_id,
                            question=question,
                            answer=answer,
                            question_type=question_type,
                            split_type=split_type,
                            source_record_id=bank_record.id,
                            generated_at=datetime.now()
                        )
                        
                        db.add(qa_pair)
                        total_generated += 1
                        
                    except Exception as e:
                        print(f"⚠️  生成问答对失败: {e}")
                        continue
            
            # 每处理10条记录提交一次
            if (i + 1) % 10 == 0:
                db.commit()
                print(f"💾 已提交 {total_generated} 个问答对")
        
        # 最终提交
        db.commit()
        
        # 统计结果
        stats = db.query(QAPair.question_type, QAPair.split_type, func.count(QAPair.id))\
            .filter(QAPair.dataset_id == dataset_id)\
            .group_by(QAPair.question_type, QAPair.split_type)\
            .all()
        
        print(f"\n✅ 问答对生成完成！")
        print(f"📊 总计生成: {total_generated} 个问答对")
        print(f"\n📈 详细统计:")
        
        type_stats = {}
        split_stats = {}
        
        for question_type, split_type, count in stats:
            type_stats[question_type] = type_stats.get(question_type, 0) + count
            split_stats[split_type] = split_stats.get(split_type, 0) + count
            print(f"  {question_type} - {split_type}: {count}")
        
        print(f"\n📋 按类型统计:")
        for qtype, count in type_stats.items():
            print(f"  {qtype}: {count}")
        
        print(f"\n📋 按数据集统计:")
        for stype, count in split_stats.items():
            print(f"  {stype}: {count}")
        
    except Exception as e:
        print(f"❌ 生成过程出错: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    print("🚀 本地样本生成工具")
    print("=" * 50)
    
    # 获取数据库会话
    db = next(get_db())
    
    try:
        # 列出可用的数据集
        datasets = db.query(Dataset).all()
        
        if not datasets:
            print("❌ 没有找到数据集")
            return
        
        print("📋 可用数据集:")
        for dataset in datasets:
            record_count = db.query(BankCode).filter(BankCode.dataset_id == dataset.id).count()
            qa_count = db.query(QAPair).filter(QAPair.dataset_id == dataset.id).count()
            print(f"  {dataset.id}: {dataset.filename} ({record_count} 条记录, {qa_count} 个问答对)")
        
        # 为每个数据集生成问答对
        for dataset in datasets:
            record_count = db.query(BankCode).filter(BankCode.dataset_id == dataset.id).count()
            if record_count > 0:
                print(f"\n🎯 处理数据集: {dataset.filename}")
                generate_qa_pairs_for_dataset(dataset.id, max_records=50)  # 限制50条记录进行测试
        
    finally:
        db.close()
    
    print("\n🎉 所有数据集处理完成！")

if __name__ == "__main__":
    main()