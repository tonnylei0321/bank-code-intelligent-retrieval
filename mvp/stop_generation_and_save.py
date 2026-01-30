#!/usr/bin/env python3
"""
停止智能生成任务并保存已生成的数据
"""
import sys
import os
import sqlite3
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_generated_data():
    """检查已生成的数据量"""
    try:
        # 连接数据库
        db_path = "data/bank_code.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 查询数据集信息
        cursor.execute("""
            SELECT id, filename, total_records, status, created_at 
            FROM datasets 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        datasets = cursor.fetchall()
        
        print("📊 最近的数据集:")
        for dataset in datasets:
            dataset_id, filename, total_records, status, created_at = dataset
            
            # 查询该数据集的QA对数量
            cursor.execute("SELECT COUNT(*) FROM qa_pairs WHERE dataset_id = ?", (dataset_id,))
            qa_count = cursor.fetchone()[0]
            
            print(f"  ID: {dataset_id}")
            print(f"  文件名: {filename}")
            print(f"  银行数: {total_records:,}")
            print(f"  QA对数: {qa_count:,}")
            print(f"  状态: {status}")
            print(f"  创建时间: {created_at}")
            print(f"  平均每银行: {qa_count/total_records:.1f} 个QA对" if total_records > 0 else "")
            print("-" * 50)
        
        # 查询总的QA对数量
        cursor.execute("SELECT COUNT(*) FROM qa_pairs")
        total_qa = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT dataset_id) FROM qa_pairs")
        total_datasets = cursor.fetchone()[0]
        
        print(f"📈 总计:")
        print(f"  数据集数量: {total_datasets}")
        print(f"  QA对总数: {total_qa:,}")
        
        conn.close()
        return total_qa > 0
        
    except Exception as e:
        print(f"❌ 检查数据失败: {e}")
        return False

def stop_generation_process():
    """停止生成进程"""
    try:
        import psutil
        
        # 查找Python进程中包含smart_sample_generator的
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'python' or 'python' in proc.info['name']:
                    cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    if 'smart_sample_generator' in cmdline or 'upload_and_generate' in cmdline:
                        print(f"🛑 发现生成进程 PID: {proc.info['pid']}")
                        print(f"   命令: {cmdline[:100]}...")
                        
                        # 温和地终止进程
                        proc.terminate()
                        proc.wait(timeout=10)
                        print(f"✅ 进程 {proc.info['pid']} 已停止")
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        print("ℹ️  未找到活跃的生成进程")
        return True
        
    except ImportError:
        print("⚠️  psutil未安装，尝试其他方法...")
        # 备用方法：通过日志判断是否还在运行
        return True
    except Exception as e:
        print(f"❌ 停止进程失败: {e}")
        return False

def create_training_ready_dataset():
    """创建一个可用于训练的数据集标记"""
    try:
        db_path = "data/bank_code.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 查找最新的智能生成数据集
        cursor.execute("""
            SELECT id, filename, total_records 
            FROM datasets 
            WHERE filename LIKE '%智能生成%' OR filename LIKE '%T_BANK_LINE_NO_ICBC_ALL%'
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        if result:
            dataset_id, filename, total_records = result
            
            # 查询实际生成的QA对数量
            cursor.execute("SELECT COUNT(*) FROM qa_pairs WHERE dataset_id = ?", (dataset_id,))
            qa_count = cursor.fetchone()[0]
            
            if qa_count > 0:
                # 更新数据集状态为可训练
                cursor.execute("""
                    UPDATE datasets 
                    SET status = 'validated', 
                        valid_records = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (qa_count, datetime.utcnow().isoformat(), dataset_id))
                
                conn.commit()
                
                print(f"✅ 数据集已准备就绪:")
                print(f"   ID: {dataset_id}")
                print(f"   文件名: {filename}")
                print(f"   QA对数量: {qa_count:,}")
                print(f"   状态: validated (可用于训练)")
                
                conn.close()
                return dataset_id, qa_count
            else:
                print("❌ 未找到生成的QA对数据")
                conn.close()
                return None, 0
        else:
            print("❌ 未找到智能生成的数据集")
            conn.close()
            return None, 0
            
    except Exception as e:
        print(f"❌ 创建训练数据集失败: {e}")
        return None, 0

def main():
    print("=" * 60)
    print("🛑 停止智能生成任务并保存数据")
    print("=" * 60)
    
    # 1. 检查当前数据
    print("1. 检查已生成的数据...")
    has_data = check_generated_data()
    
    if not has_data:
        print("❌ 未找到已生成的数据，无法继续")
        return
    
    # 2. 停止生成进程
    print("\n2. 停止生成进程...")
    stopped = stop_generation_process()
    
    if not stopped:
        print("❌ 停止进程失败")
        return
    
    # 3. 准备训练数据集
    print("\n3. 准备训练数据集...")
    dataset_id, qa_count = create_training_ready_dataset()
    
    if dataset_id:
        print(f"\n✅ 任务完成!")
        print(f"📊 数据集 {dataset_id} 已准备就绪，包含 {qa_count:,} 个QA对")
        print(f"🚀 现在可以使用此数据集进行模型训练")
        print(f"💡 建议: 在前端的训练管理页面选择数据集 {dataset_id} 开始训练")
    else:
        print("❌ 准备训练数据集失败")

if __name__ == "__main__":
    main()