#!/usr/bin/env python3
"""
监控训练数据生成进度

实时查看生成进度、统计信息和性能指标
"""

import sys
import os
import time
from datetime import datetime, timedelta
from sqlalchemy import func

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_db
from app.models.qa_pair import QAPair
from app.models.dataset import Dataset
from app.models.bank_code import BankCode


class GenerationMonitor:
    """生成进度监控器"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.last_count = 0
        self.last_check_time = datetime.now()
    
    def get_latest_dataset_id(self):
        """获取最新的数据集ID"""
        db = next(get_db())
        try:
            latest_dataset = db.query(Dataset).order_by(Dataset.id.desc()).first()
            return latest_dataset.id if latest_dataset else None
        finally:
            db.close()
    
    def get_generation_stats(self, dataset_id: int = None):
        """获取生成统计信息"""
        db = next(get_db())
        try:
            # 总银行数
            total_banks = db.query(BankCode).count()
            
            # 如果没有指定数据集，使用最新的
            if dataset_id is None:
                dataset_id = self.get_latest_dataset_id()
            
            if dataset_id is None:
                return {
                    "total_banks": total_banks,
                    "generated_samples": 0,
                    "processed_banks": 0,
                    "dataset_name": "无数据集"
                }
            
            # 数据集信息
            dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
            dataset_name = dataset.name if dataset else f"数据集 {dataset_id}"
            
            # 生成的样本数
            generated_samples = db.query(QAPair).filter(QAPair.dataset_id == dataset_id).count()
            
            # 处理的银行数（去重）
            processed_banks = db.query(func.count(func.distinct(QAPair.source_record_id))).filter(
                QAPair.dataset_id == dataset_id
            ).scalar()
            
            return {
                "dataset_id": dataset_id,
                "dataset_name": dataset_name,
                "total_banks": total_banks,
                "generated_samples": generated_samples,
                "processed_banks": processed_banks or 0
            }
            
        finally:
            db.close()
    
    def calculate_performance_metrics(self, stats):
        """计算性能指标"""
        current_time = datetime.now()
        elapsed_total = (current_time - self.start_time).total_seconds()
        elapsed_interval = (current_time - self.last_check_time).total_seconds()
        
        # 总体速度
        if elapsed_total > 0:
            samples_per_second = stats["generated_samples"] / elapsed_total
            banks_per_minute = (stats["processed_banks"] * 60) / elapsed_total
        else:
            samples_per_second = 0
            banks_per_minute = 0
        
        # 区间速度
        interval_samples = stats["generated_samples"] - self.last_count
        if elapsed_interval > 0:
            interval_speed = interval_samples / elapsed_interval
        else:
            interval_speed = 0
        
        # 预估完成时间
        remaining_banks = stats["total_banks"] - stats["processed_banks"]
        if banks_per_minute > 0:
            eta_minutes = remaining_banks / banks_per_minute
            eta_time = current_time + timedelta(minutes=eta_minutes)
        else:
            eta_minutes = 0
            eta_time = None
        
        # 更新状态
        self.last_count = stats["generated_samples"]
        self.last_check_time = current_time
        
        return {
            "samples_per_second": samples_per_second,
            "banks_per_minute": banks_per_minute,
            "interval_speed": interval_speed,
            "eta_minutes": eta_minutes,
            "eta_time": eta_time,
            "elapsed_minutes": elapsed_total / 60
        }
    
    def print_status(self, stats, metrics):
        """打印状态信息"""
        # 清屏
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("🚀 训练数据生成监控")
        print("=" * 80)
        print(f"数据集: {stats['dataset_name']}")
        print(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # 进度信息
        progress = (stats["processed_banks"] / stats["total_banks"]) * 100 if stats["total_banks"] > 0 else 0
        
        print("📊 进度统计")
        print(f"总银行数: {stats['total_banks']:,}")
        print(f"已处理银行: {stats['processed_banks']:,}")
        print(f"生成样本数: {stats['generated_samples']:,}")
        print(f"完成进度: {progress:.2f}%")
        
        # 进度条
        bar_length = 50
        filled_length = int(bar_length * progress / 100)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        print(f"进度条: [{bar}] {progress:.1f}%")
        
        print("-" * 80)
        
        # 性能指标
        print("⚡ 性能指标")
        print(f"样本生成速度: {metrics['samples_per_second']:.2f} 样本/秒")
        print(f"银行处理速度: {metrics['banks_per_minute']:.2f} 银行/分钟")
        print(f"区间速度: {metrics['interval_speed']:.2f} 样本/秒")
        print(f"运行时间: {metrics['elapsed_minutes']:.1f} 分钟")
        
        if metrics['eta_time']:
            print(f"预计完成时间: {metrics['eta_time'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"剩余时间: {metrics['eta_minutes']:.1f} 分钟")
        
        print("-" * 80)
        
        # 质量指标
        if stats["processed_banks"] > 0:
            avg_samples_per_bank = stats["generated_samples"] / stats["processed_banks"]
            print("📈 质量指标")
            print(f"平均每银行样本数: {avg_samples_per_bank:.2f}")
            
            if avg_samples_per_bank < 5:
                print("⚠️  警告: 平均样本数偏低，可能存在生成问题")
            elif avg_samples_per_bank > 8:
                print("⚠️  警告: 平均样本数偏高，可能存在重复生成")
            else:
                print("✅ 样本生成质量正常")
        
        print("=" * 80)
        print("按 Ctrl+C 退出监控")
    
    def run_monitor(self, dataset_id: int = None, interval: int = 5):
        """运行监控"""
        print("🔍 启动生成进度监控...")
        
        try:
            while True:
                stats = self.get_generation_stats(dataset_id)
                metrics = self.calculate_performance_metrics(stats)
                self.print_status(stats, metrics)
                
                # 检查是否完成
                if stats["processed_banks"] >= stats["total_banks"] and stats["total_banks"] > 0:
                    print("\n🎉 生成完成！")
                    break
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n👋 监控已停止")


def main():
    """主函数"""
    monitor = GenerationMonitor()
    
    # 检查命令行参数
    dataset_id = None
    interval = 5
    
    if len(sys.argv) > 1:
        try:
            dataset_id = int(sys.argv[1])
            print(f"监控数据集 ID: {dataset_id}")
        except ValueError:
            print("无效的数据集ID，将监控最新数据集")
    
    if len(sys.argv) > 2:
        try:
            interval = int(sys.argv[2])
            print(f"刷新间隔: {interval} 秒")
        except ValueError:
            print("无效的刷新间隔，使用默认值 5 秒")
    
    monitor.run_monitor(dataset_id, interval)


if __name__ == "__main__":
    main()