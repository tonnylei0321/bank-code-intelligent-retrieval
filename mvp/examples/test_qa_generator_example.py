"""
Example usage of QA Generator Service
示例：如何使用问答对生成服务

注意：需要配置有效的数据库和QWEN_API_KEY才能运行此示例
"""
from sqlalchemy.orm import Session
from app.services.qa_generator import QAGenerator
from app.services.teacher_model import TeacherModelAPI
from app.core.database import SessionLocal
from app.models.dataset import Dataset
from app.models.bank_code import BankCode


def example_basic_generation():
    """基本生成示例"""
    print("=" * 60)
    print("示例 1: 基本问答对生成")
    print("=" * 60)
    
    # 创建数据库会话
    db = SessionLocal()
    
    try:
        # 创建QA生成器
        generator = QAGenerator(db=db)
        
        # 假设已经有一个数据集 ID=1
        dataset_id = 1
        
        print(f"\n为数据集 {dataset_id} 生成问答对...")
        print("问题类型: exact, fuzzy, reverse, natural")
        
        # 生成问答对（实际使用时需要有效的API key）
        # results = generator.generate_for_dataset(
        #     dataset_id=dataset_id,
        #     question_types=["exact", "fuzzy", "reverse", "natural"]
        # )
        # 
        # print(f"\n生成结果:")
        # print(f"  数据集ID: {results['dataset_id']}")
        # print(f"  总记录数: {results['total_records']}")
        # print(f"  总尝试次数: {results['total_attempts']}")
        # print(f"  成功: {results['successful']}")
        # print(f"  失败: {results['failed']}")
        # print(f"  创建的问答对: {results['qa_pairs_created']}")
        # print(f"  失败的记录数: {len(results['failed_records'])}")
        
        print("\n注意: 实际调用需要配置有效的QWEN_API_KEY和数据库")
    
    finally:
        db.close()


def example_generation_with_progress():
    """带进度跟踪的生成示例"""
    print("\n" + "=" * 60)
    print("示例 2: 带进度跟踪的生成")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        generator = QAGenerator(db=db)
        
        # 定义进度回调函数
        def progress_callback(current, total, record_id):
            percentage = (current / total) * 100
            print(f"  进度: {current}/{total} ({percentage:.1f}%) - 处理记录 ID: {record_id}")
        
        dataset_id = 1
        
        print(f"\n为数据集 {dataset_id} 生成问答对（带进度跟踪）...")
        
        # 生成问答对
        # results = generator.generate_for_dataset(
        #     dataset_id=dataset_id,
        #     progress_callback=progress_callback
        # )
        # 
        # print(f"\n生成完成!")
        # print(f"  成功: {results['successful']}")
        # print(f"  失败: {results['failed']}")
        
        print("\n注意: 实际调用需要配置有效的QWEN_API_KEY和数据库")
    
    finally:
        db.close()


def example_custom_question_types():
    """自定义问题类型示例"""
    print("\n" + "=" * 60)
    print("示例 3: 自定义问题类型")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        generator = QAGenerator(db=db)
        
        dataset_id = 1
        
        # 只生成精确查询和模糊查询
        custom_types = ["exact", "fuzzy"]
        
        print(f"\n为数据集 {dataset_id} 生成问答对...")
        print(f"自定义问题类型: {custom_types}")
        
        # results = generator.generate_for_dataset(
        #     dataset_id=dataset_id,
        #     question_types=custom_types
        # )
        # 
        # print(f"\n生成结果:")
        # print(f"  问题类型: {results['question_types']}")
        # print(f"  总尝试次数: {results['total_attempts']}")
        # print(f"  创建的问答对: {results['qa_pairs_created']}")
        
        print("\n注意: 实际调用需要配置有效的QWEN_API_KEY和数据库")
    
    finally:
        db.close()


def example_dataset_split():
    """数据集划分示例"""
    print("\n" + "=" * 60)
    print("示例 4: 数据集划分")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        generator = QAGenerator(db=db)
        
        dataset_id = 1
        
        print(f"\n划分数据集 {dataset_id}...")
        print("划分比例: 训练集 80%, 验证集 10%, 测试集 10%")
        print("随机种子: 42 (确保可重复性)")
        
        # 划分数据集
        # results = generator.split_dataset(
        #     dataset_id=dataset_id,
        #     train_ratio=0.8,
        #     val_ratio=0.1,
        #     test_ratio=0.1,
        #     random_seed=42
        # )
        # 
        # print(f"\n划分结果:")
        # print(f"  总问答对数: {results['total_qa_pairs']}")
        # print(f"  训练集: {results['train_count']} ({results['train_ratio']:.2%})")
        # print(f"  验证集: {results['val_count']} ({results['val_ratio']:.2%})")
        # print(f"  测试集: {results['test_count']} ({results['test_ratio']:.2%})")
        # print(f"  问题类型: {results['question_types']}")
        
        print("\n注意: 实际调用需要配置有效的数据库")
    
    finally:
        db.close()


def example_generation_stats():
    """生成统计信息示例"""
    print("\n" + "=" * 60)
    print("示例 5: 获取生成统计信息")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        generator = QAGenerator(db=db)
        
        dataset_id = 1
        
        print(f"\n获取数据集 {dataset_id} 的统计信息...")
        
        # 获取统计信息
        # stats = generator.get_generation_stats(dataset_id=dataset_id)
        # 
        # print(f"\n统计信息:")
        # print(f"  数据集ID: {stats['dataset_id']}")
        # print(f"  总问答对数: {stats['total_qa_pairs']}")
        # 
        # print(f"\n  按问题类型:")
        # for q_type, count in stats['by_question_type'].items():
        #     print(f"    {q_type}: {count}")
        # 
        # print(f"\n  按划分类型:")
        # for s_type, count in stats['by_split_type'].items():
        #     print(f"    {s_type}: {count}")
        
        print("\n注意: 实际调用需要配置有效的数据库")
    
    finally:
        db.close()


def example_complete_workflow():
    """完整工作流示例"""
    print("\n" + "=" * 60)
    print("示例 6: 完整工作流")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # 创建QA生成器
        generator = QAGenerator(db=db)
        
        dataset_id = 1
        
        print("\n步骤 1: 生成问答对")
        print("-" * 40)
        
        # 定义进度回调
        def progress_callback(current, total, record_id):
            if current % 10 == 0 or current == total:
                print(f"  进度: {current}/{total} ({(current/total)*100:.1f}%)")
        
        # 生成问答对
        # gen_results = generator.generate_for_dataset(
        #     dataset_id=dataset_id,
        #     question_types=["exact", "fuzzy", "reverse", "natural"],
        #     progress_callback=progress_callback
        # )
        # 
        # print(f"\n生成完成:")
        # print(f"  成功: {gen_results['successful']}")
        # print(f"  失败: {gen_results['failed']}")
        # print(f"  创建的问答对: {gen_results['qa_pairs_created']}")
        
        print("\n步骤 2: 划分数据集")
        print("-" * 40)
        
        # 划分数据集
        # split_results = generator.split_dataset(
        #     dataset_id=dataset_id,
        #     train_ratio=0.8,
        #     val_ratio=0.1,
        #     test_ratio=0.1,
        #     random_seed=42
        # )
        # 
        # print(f"\n划分完成:")
        # print(f"  训练集: {split_results['train_count']}")
        # print(f"  验证集: {split_results['val_count']}")
        # print(f"  测试集: {split_results['test_count']}")
        
        print("\n步骤 3: 查看统计信息")
        print("-" * 40)
        
        # 获取统计信息
        # stats = generator.get_generation_stats(dataset_id=dataset_id)
        # 
        # print(f"\n最终统计:")
        # print(f"  总问答对数: {stats['total_qa_pairs']}")
        # print(f"  问题类型分布: {stats['by_question_type']}")
        # print(f"  数据集划分: {stats['by_split_type']}")
        
        print("\n注意: 实际调用需要配置有效的QWEN_API_KEY和数据库")
    
    finally:
        db.close()


def example_error_handling():
    """错误处理示例"""
    print("\n" + "=" * 60)
    print("示例 7: 错误处理")
    print("=" * 60)
    
    print("\n常见错误场景:")
    print("  1. 数据集不存在")
    print("     - 抛出 QAGenerationError: 'Dataset X not found'")
    print("  2. 数据集没有有效记录")
    print("     - 抛出 QAGenerationError: 'No valid bank code records found'")
    print("  3. 划分比例不正确")
    print("     - 抛出 QAGenerationError: 'Split ratios must sum to 1.0'")
    print("  4. 数据库提交失败")
    print("     - 抛出 QAGenerationError: 'Database commit failed'")
    print("     - 自动回滚事务")
    
    print("\n错误处理最佳实践:")
    print("  - 使用 try-except 捕获 QAGenerationError")
    print("  - 记录失败的记录和原因")
    print("  - 提供详细的错误信息给用户")
    print("  - 在失败后清理资源（关闭数据库连接）")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("QA Generator Service 使用示例")
    print("=" * 60)
    
    example_basic_generation()
    example_generation_with_progress()
    example_custom_question_types()
    example_dataset_split()
    example_generation_stats()
    example_complete_workflow()
    example_error_handling()
    
    print("\n" + "=" * 60)
    print("示例完成")
    print("=" * 60)
    print("\n提示:")
    print("  1. 在.env文件中配置QWEN_API_KEY")
    print("  2. 确保数据库已初始化并包含数据集")
    print("  3. 取消注释代码以实际运行示例")
