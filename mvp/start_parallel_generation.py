#!/usr/bin/env python3
"""
启动并行训练数据生成

使用多线程和多LLM API并行生成大规模训练数据
"""

import sys
import os
import logging
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.parallel_training_generator import ParallelTrainingGenerator, create_training_dataset

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'parallel_generation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """主函数"""
    print("🚀 启动并行训练数据生成系统")
    print("=" * 60)
    print("配置信息：")
    print("- 3个LLM API并行处理")
    print("- 每个银行生成7个训练样本")
    print("- 多线程并发处理")
    print("- 数据库批量写入优化")
    print("=" * 60)
    
    try:
        # 创建数据集
        dataset_name = f"大规模银行训练数据集_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        dataset_id = create_training_dataset(dataset_name)
        
        # 创建生成器
        generator = ParallelTrainingGenerator(dataset_id)
        
        # 询问用户是否要测试模式
        test_mode = input("是否启用测试模式？(y/N): ").lower().strip()
        
        if test_mode == 'y':
            limit = input("请输入测试银行数量 (默认1000): ").strip()
            limit = int(limit) if limit.isdigit() else 1000
            print(f"🧪 测试模式：处理 {limit} 个银行")
            generator.run_parallel_generation(limit=limit)
        else:
            print("🏭 生产模式：处理所有银行数据")
            confirm = input("确认开始生成？这将处理15万条银行数据 (y/N): ").lower().strip()
            if confirm == 'y':
                generator.run_parallel_generation()
            else:
                print("❌ 已取消")
                return
        
        print("✅ 训练数据生成完成！")
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断，正在安全退出...")
    except Exception as e:
        logger.error(f"生成过程出错: {e}")
        print(f"❌ 生成失败: {e}")


if __name__ == "__main__":
    main()