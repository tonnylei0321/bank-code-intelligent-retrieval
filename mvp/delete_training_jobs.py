#!/usr/bin/env python3
"""
训练任务删除脚本

由于后端API存在验证问题，此脚本提供直接操作数据库的方式来删除训练任务。

使用方法：
    python delete_training_jobs.py --ids 1,2,3,4,5
    python delete_training_jobs.py --status failed
    python delete_training_jobs.py --all-failed
    python delete_training_jobs.py --all-completed
"""

import sys
import os
import argparse
import shutil
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.training_job import TrainingJob


def delete_jobs_by_ids(job_ids):
    """根据ID列表删除训练任务"""
    db = SessionLocal()
    try:
        jobs = db.query(TrainingJob).filter(TrainingJob.id.in_(job_ids)).all()
        
        if not jobs:
            print(f"未找到任何匹配的训练任务")
            return
        
        print(f"找到 {len(jobs)} 个训练任务:")
        for job in jobs:
            print(f"  - ID: {job.id}, 模型: {job.model_name}, 状态: {job.status}")
        
        confirm = input(f"\n确认删除这 {len(jobs)} 个任务? (yes/no): ")
        if confirm.lower() != 'yes':
            print("已取消删除")
            return
        
        deleted_count = 0
        for job in jobs:
            try:
                # 删除模型文件
                if job.model_path:
                    model_path = Path(job.model_path)
                    if model_path.exists():
                        if model_path.is_dir():
                            shutil.rmtree(model_path)
                        else:
                            model_path.unlink()
                        print(f"  ✓ 已删除模型文件: {model_path}")
                
                # 删除数据库记录
                db.delete(job)
                deleted_count += 1
                print(f"  ✓ 已删除任务 #{job.id}")
                
            except Exception as e:
                print(f"  ✗ 删除任务 #{job.id} 失败: {e}")
        
        db.commit()
        print(f"\n成功删除 {deleted_count} 个训练任务")
        
    except Exception as e:
        db.rollback()
        print(f"错误: {e}")
    finally:
        db.close()


def delete_jobs_by_status(status):
    """根据状态删除训练任务"""
    db = SessionLocal()
    try:
        jobs = db.query(TrainingJob).filter(TrainingJob.status == status).all()
        
        if not jobs:
            print(f"未找到状态为 '{status}' 的训练任务")
            return
        
        job_ids = [job.id for job in jobs]
        print(f"找到 {len(jobs)} 个状态为 '{status}' 的训练任务:")
        for job in jobs:
            print(f"  - ID: {job.id}, 模型: {job.model_name}, 创建时间: {job.created_at}")
        
        confirm = input(f"\n确认删除这 {len(jobs)} 个任务? (yes/no): ")
        if confirm.lower() != 'yes':
            print("已取消删除")
            return
        
        delete_jobs_by_ids(job_ids)
        
    except Exception as e:
        print(f"错误: {e}")
    finally:
        db.close()


def list_all_jobs():
    """列出所有训练任务"""
    db = SessionLocal()
    try:
        jobs = db.query(TrainingJob).order_by(TrainingJob.created_at.desc()).all()
        
        if not jobs:
            print("没有找到任何训练任务")
            return
        
        print(f"\n共有 {len(jobs)} 个训练任务:\n")
        print(f"{'ID':<5} {'模型名称':<30} {'状态':<10} {'创建时间':<20}")
        print("-" * 70)
        
        for job in jobs:
            print(f"{job.id:<5} {job.model_name:<30} {job.status:<10} {str(job.created_at)[:19]}")
        
        print()
        
    except Exception as e:
        print(f"错误: {e}")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='删除训练任务')
    parser.add_argument('--ids', type=str, help='要删除的任务ID列表，用逗号分隔，例如: 1,2,3,4,5')
    parser.add_argument('--status', type=str, help='根据状态删除任务，例如: failed, completed, stopped')
    parser.add_argument('--all-failed', action='store_true', help='删除所有失败的任务')
    parser.add_argument('--all-completed', action='store_true', help='删除所有已完成的任务')
    parser.add_argument('--all-stopped', action='store_true', help='删除所有已停止的任务')
    parser.add_argument('--list', action='store_true', help='列出所有训练任务')
    
    args = parser.parse_args()
    
    if args.list:
        list_all_jobs()
    elif args.ids:
        job_ids = [int(id.strip()) for id in args.ids.split(',')]
        delete_jobs_by_ids(job_ids)
    elif args.status:
        delete_jobs_by_status(args.status)
    elif args.all_failed:
        delete_jobs_by_status('failed')
    elif args.all_completed:
        delete_jobs_by_status('completed')
    elif args.all_stopped:
        delete_jobs_by_status('stopped')
    else:
        parser.print_help()
        print("\n示例:")
        print("  python delete_training_jobs.py --list")
        print("  python delete_training_jobs.py --ids 1,2,3,4,5")
        print("  python delete_training_jobs.py --all-failed")
        print("  python delete_training_jobs.py --status failed")


if __name__ == "__main__":
    main()
