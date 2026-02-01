#!/usr/bin/env python3
"""
训练任务内存优化启动脚本
专门解决MPS内存溢出问题的训练启动器
"""

import os
import sys
import sqlite3
import subprocess
import time
import json
from datetime import datetime
from pathlib import Path

def setup_memory_environment():
    """设置内存优化环境变量"""
    print("🔧 配置内存优化环境...")
    
    # 更激进的内存限制
    os.environ['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.5'  # 降到50%
    os.environ['PYTORCH_MPS_LOW_WATERMARK_RATIO'] = '0.3'   # 降到30%
    os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
    os.environ['PYTORCH_MPS_ALLOCATOR_POLICY'] = 'garbage_collection'
    
    # 限制OMP线程数，减少内存使用
    os.environ['OMP_NUM_THREADS'] = '2'
    os.environ['MKL_NUM_THREADS'] = '2'
    
    print("✅ 内存环境配置完成")
    print(f"   MPS高水位: {os.environ['PYTORCH_MPS_HIGH_WATERMARK_RATIO']}")
    print(f"   MPS低水位: {os.environ['PYTORCH_MPS_LOW_WATERMARK_RATIO']}")

def clear_memory():
    """清理系统内存"""
    print("🧹 清理系统内存...")
    
    # 停止可能占用内存的进程
    subprocess.run(['pkill', '-f', 'python.*training'], capture_output=True)
    time.sleep(2)
    
    # 清理Python缓存
    subprocess.run(['find', '.', '-type', 'd', '-name', '__pycache__', '-exec', 'rm', '-rf', '{}', '+'], 
                  capture_output=True, cwd='mvp')
    
    print("✅ 内存清理完成")

def create_small_training_dataset():
    """创建更小的训练数据集 - 5万样本"""
    print("📊 创建小型训练数据集...")
    
    try:
        conn = sqlite3.connect('mvp/data/bank_code.db')
        cursor = conn.cursor()
        
        # 检查最新数据集
        cursor.execute("SELECT id, sample_count FROM datasets ORDER BY created_at DESC LIMIT 1")
        latest_dataset = cursor.fetchone()
        
        if not latest_dataset:
            print("❌ 没有找到数据集")
            return None
            
        latest_id, total_samples = latest_dataset
        print(f"📋 最新数据集: {latest_id}, 总样本: {total_samples}")
        
        # 创建5万样本的小数据集
        target_samples = 50000
        
        # 随机抽取5万样本
        cursor.execute(f"""
            INSERT INTO datasets (name, description, sample_count, created_at)
            VALUES ('小型训练集-5万样本', '从数据集{latest_id}中随机抽取5万样本用于内存优化训练', {target_samples}, ?)
        """, (datetime.now().isoformat(),))
        
        new_dataset_id = cursor.lastrowid
        
        # 复制样本数据
        cursor.execute(f"""
            INSERT INTO qa_pairs (dataset_id, question, answer, question_type, bank_name, bank_code, created_at)
            SELECT {new_dataset_id}, question, answer, question_type, bank_name, bank_code, ?
            FROM qa_pairs 
            WHERE dataset_id = {latest_id}
            ORDER BY RANDOM()
            LIMIT {target_samples}
        """, (datetime.now().isoformat(),))
        
        conn.commit()
        conn.close()
        
        print(f"✅ 创建小型数据集成功: ID={new_dataset_id}, 样本数={target_samples}")
        return new_dataset_id
        
    except Exception as e:
        print(f"❌ 创建数据集失败: {e}")
        return None

def start_optimized_training(dataset_id):
    """启动内存优化的训练任务"""
    print("🚀 启动内存优化训练...")
    
    # 训练配置 - 极度保守的内存设置
    training_config = {
        "model_name": "Qwen/Qwen2.5-0.5B",  # 使用最小的模型
        "dataset_id": dataset_id,
        "epochs": 2,  # 减少到2个epoch
        "batch_size": 8,  # 进一步减小batch size
        "learning_rate": 2e-4,
        "max_length": 256,  # 减少序列长度
        "gradient_accumulation_steps": 4,  # 使用梯度累积
        "dataloader_num_workers": 0,  # 不使用多进程
        "fp16": True,  # 使用半精度
        "gradient_checkpointing": True,  # 启用梯度检查点
        "save_steps": 500,
        "eval_steps": 500,
        "logging_steps": 50,
        "warmup_steps": 100
    }
    
    try:
        conn = sqlite3.connect('mvp/data/bank_code.db')
        cursor = conn.cursor()
        
        # 创建训练任务
        cursor.execute("""
            INSERT INTO training_jobs (
                status, model_name, dataset_id, epochs, batch_size, learning_rate,
                total_steps, created_at, started_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'running',
            training_config['model_name'],
            dataset_id,
            training_config['epochs'],
            training_config['batch_size'],
            training_config['learning_rate'],
            0,  # total_steps will be calculated during training
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        job_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"✅ 训练任务创建成功: ID={job_id}")
        print("📋 训练配置:")
        for key, value in training_config.items():
            print(f"   {key}: {value}")
        
        # 启动训练进程
        cmd = [
            sys.executable, '-c', f"""
import os
import sys
sys.path.append('mvp')

# 设置内存优化环境
os.environ['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.5'
os.environ['PYTORCH_MPS_LOW_WATERMARK_RATIO'] = '0.3'
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
os.environ['OMP_NUM_THREADS'] = '2'

from app.services.model_trainer import ModelTrainer

trainer = ModelTrainer()
trainer.train_model({job_id})
"""
        ]
        
        # 在后台启动训练
        process = subprocess.Popen(
            cmd,
            cwd='.',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy()
        )
        
        print(f"🎯 训练进程已启动: PID={process.pid}")
        return job_id, process.pid
        
    except Exception as e:
        print(f"❌ 启动训练失败: {e}")
        return None, None

def monitor_training(job_id):
    """监控训练进度"""
    print(f"📊 开始监控训练任务 {job_id}...")
    
    for i in range(10):  # 监控10次，每次间隔30秒
        try:
            conn = sqlite3.connect('mvp/data/bank_code.db')
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT status, current_step, total_steps, progress_percentage, train_loss
                FROM training_jobs WHERE id = ?
            """, (job_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                status, current_step, total_steps, progress, train_loss = result
                print(f"⏰ [{datetime.now().strftime('%H:%M:%S')}] 状态: {status}")
                if current_step and total_steps:
                    print(f"   进度: {current_step}/{total_steps} ({progress:.2f}%)")
                if train_loss:
                    print(f"   损失: {train_loss:.4f}")
                
                if status in ['completed', 'failed']:
                    print(f"🏁 训练结束: {status}")
                    break
            else:
                print("❌ 无法获取训练状态")
                
        except Exception as e:
            print(f"⚠️ 监控出错: {e}")
        
        time.sleep(30)

def main():
    """主函数"""
    print("=" * 60)
    print("🏦 银行代码检索系统 - 内存优化训练启动器")
    print("=" * 60)
    
    # 1. 设置内存环境
    setup_memory_environment()
    
    # 2. 清理内存
    clear_memory()
    
    # 3. 创建小数据集
    dataset_id = create_small_training_dataset()
    if not dataset_id:
        print("❌ 无法创建数据集，退出")
        return
    
    # 4. 启动训练
    job_id, pid = start_optimized_training(dataset_id)
    if not job_id:
        print("❌ 无法启动训练，退出")
        return
    
    print("\n" + "=" * 60)
    print("🎉 内存优化训练已启动!")
    print("=" * 60)
    print(f"📋 训练任务ID: {job_id}")
    print(f"📊 数据集ID: {dataset_id} (5万样本)")
    print(f"🔧 进程ID: {pid}")
    print(f"💾 内存限制: 50% MPS内存")
    print(f"⚙️ 配置: 2 epochs, batch_size=8, 半精度训练")
    
    print("\n📊 监控命令:")
    print(f"   python3 mvp/system_monitor.py")
    print(f"   tail -f mvp/logs/error_{datetime.now().strftime('%Y-%m-%d')}.log")
    
    # 5. 开始监控
    print("\n🔍 开始监控训练进度...")
    monitor_training(job_id)

if __name__ == "__main__":
    main()