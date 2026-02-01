#!/usr/bin/env python3
"""
银行代码检索系统 - 全面系统监控脚本
监控系统资源、进程状态、数据库状态、训练进度等
每20秒刷新一次，提供实时监控信息
"""

import os
import sys
import time
import sqlite3
import psutil
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path
import requests
from typing import Dict, List, Optional, Tuple

class SystemMonitor:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.db_path = self.project_root / "data" / "bank_code.db"
        self.log_path = self.project_root / "logs"
        self.models_path = self.project_root / "models"
        self.backend_port = 8000
        self.frontend_port = 3000
        
        # 项目相关进程关键词
        self.process_keywords = [
            "uvicorn", "fastapi", "python.*mvp", "node.*frontend", 
            "npm.*start", "yarn.*start", "vite", "react"
        ]
        
        # 监控开始时间
        self.start_time = datetime.now()
        
    def clear_screen(self):
        """清屏"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def get_system_resources(self) -> Dict:
        """获取系统资源使用情况"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            
            # 网络IO
            net_io = psutil.net_io_counters()
            
            # 系统负载 (仅Unix系统)
            load_avg = None
            if hasattr(os, 'getloadavg'):
                load_avg = os.getloadavg()
            
            return {
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count,
                    'load_avg': load_avg
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used,
                    'free': memory.free
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': (disk.used / disk.total) * 100
                },
                'network': {
                    'bytes_sent': net_io.bytes_sent,
                    'bytes_recv': net_io.bytes_recv,
                    'packets_sent': net_io.packets_sent,
                    'packets_recv': net_io.packets_recv
                }
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_project_processes(self) -> List[Dict]:
        """获取项目相关进程"""
        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent', 'create_time']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    
                    # 检查是否是项目相关进程
                    is_project_process = False
                    for keyword in self.process_keywords:
                        if keyword in cmdline.lower() or keyword in proc.info['name'].lower():
                            is_project_process = True
                            break
                    
                    # 检查端口占用
                    if proc.info['pid']:
                        try:
                            connections = proc.connections()
                            for conn in connections:
                                if conn.laddr.port in [self.backend_port, self.frontend_port]:
                                    is_project_process = True
                                    break
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    
                    if is_project_process:
                        # 计算运行时长
                        create_time = datetime.fromtimestamp(proc.info['create_time'])
                        runtime = datetime.now() - create_time
                        
                        processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cmdline': cmdline[:100] + '...' if len(cmdline) > 100 else cmdline,
                            'cpu_percent': proc.info['cpu_percent'],
                            'memory_percent': proc.info['memory_percent'],
                            'runtime': str(runtime).split('.')[0],  # 去掉微秒
                            'create_time': create_time.strftime('%H:%M:%S')
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            processes.append({'error': str(e)})
            
        return processes
    
    def get_port_status(self) -> Dict:
        """检查端口占用状态"""
        ports = {}
        for port in [self.backend_port, self.frontend_port]:
            try:
                result = subprocess.run(
                    ['lsof', '-i', f':{port}'], 
                    capture_output=True, 
                    text=True, 
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    lines = result.stdout.strip().split('\n')[1:]  # 跳过标题行
                    if lines:
                        parts = lines[0].split()
                        ports[port] = {
                            'status': 'occupied',
                            'process': parts[0],
                            'pid': parts[1]
                        }
                    else:
                        ports[port] = {'status': 'free'}
                else:
                    ports[port] = {'status': 'free'}
            except Exception as e:
                ports[port] = {'status': 'error', 'error': str(e)}
        
        return ports
    
    def get_database_status(self) -> Dict:
        """获取数据库状态"""
        try:
            if not self.db_path.exists():
                return {'status': 'not_found', 'path': str(self.db_path)}
            
            # 数据库文件大小
            db_size = self.db_path.stat().st_size
            
            # 连接数据库获取统计信息
            conn = sqlite3.connect(str(self.db_path), timeout=5)
            cursor = conn.cursor()
            
            # 获取表信息
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            # 获取各表记录数
            table_counts = {}
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    table_counts[table] = cursor.fetchone()[0]
                except Exception:
                    table_counts[table] = 'error'
            
            # 获取最近的活动
            recent_activity = {}
            try:
                # 查询日志表最新记录
                cursor.execute("SELECT created_at FROM query_logs ORDER BY created_at DESC LIMIT 1")
                result = cursor.fetchone()
                if result:
                    recent_activity['last_query'] = result[0]
                
                # 训练任务最新记录
                cursor.execute("SELECT updated_at FROM training_jobs ORDER BY updated_at DESC LIMIT 1")
                result = cursor.fetchone()
                if result:
                    recent_activity['last_training_update'] = result[0]
                    
            except Exception as e:
                recent_activity['error'] = str(e)
            
            conn.close()
            
            return {
                'status': 'connected',
                'size': db_size,
                'size_mb': round(db_size / 1024 / 1024, 2),
                'tables': table_counts,
                'recent_activity': recent_activity
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def get_training_status(self) -> Dict:
        """获取训练任务状态"""
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=5)
            cursor = conn.cursor()
            
            # 获取所有训练任务
            cursor.execute("""
                SELECT id, status, model_name, dataset_id, epochs, batch_size, learning_rate,
                       current_epoch, current_step, total_steps, progress_percentage, 
                       train_loss, val_loss, created_at, started_at, updated_at, completed_at
                FROM training_jobs 
                ORDER BY id DESC 
                LIMIT 10
            """)
            
            jobs = []
            for row in cursor.fetchall():
                job_id, status, model_name, dataset_id, epochs, batch_size, lr, \
                current_epoch, current_step, total_steps, progress, train_loss, val_loss, \
                created_at, started_at, updated_at, completed_at = row
                
                # 计算运行时长
                runtime = None
                if started_at:
                    start_time = datetime.fromisoformat(started_at)
                    end_time = datetime.fromisoformat(completed_at) if completed_at else datetime.now()
                    runtime = str(end_time - start_time).split('.')[0]
                
                # 估算剩余时间
                eta = None
                if status == 'running' and current_step and total_steps and current_step > 0:
                    if started_at:
                        elapsed = (datetime.now() - datetime.fromisoformat(started_at)).total_seconds()
                        steps_per_second = current_step / elapsed
                        remaining_steps = total_steps - current_step
                        eta_seconds = remaining_steps / steps_per_second if steps_per_second > 0 else 0
                        eta = str(timedelta(seconds=int(eta_seconds)))
                
                jobs.append({
                    'id': job_id,
                    'status': status,
                    'model_name': model_name,
                    'dataset_id': dataset_id,
                    'epochs': epochs,
                    'batch_size': batch_size,
                    'learning_rate': lr,
                    'current_epoch': current_epoch,
                    'current_step': current_step,
                    'total_steps': total_steps,
                    'progress': progress,
                    'train_loss': train_loss,
                    'val_loss': val_loss,
                    'runtime': runtime,
                    'eta': eta,
                    'updated_at': updated_at
                })
            
            conn.close()
            return {'jobs': jobs}
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_log_status(self) -> Dict:
        """获取日志文件状态"""
        try:
            log_files = {}
            if self.log_path.exists():
                for log_file in self.log_path.glob("*.log"):
                    stat = log_file.stat()
                    
                    # 获取最后几行
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            last_lines = lines[-3:] if len(lines) >= 3 else lines
                    except Exception:
                        last_lines = ['无法读取']
                    
                    log_files[log_file.name] = {
                        'size': stat.st_size,
                        'size_mb': round(stat.st_size / 1024 / 1024, 2),
                        'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%H:%M:%S'),
                        'last_lines': [line.strip() for line in last_lines]
                    }
            
            return log_files
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_model_storage_status(self) -> Dict:
        """获取模型存储状态"""
        try:
            models_info = {}
            if self.models_path.exists():
                for model_dir in self.models_path.iterdir():
                    if model_dir.is_dir():
                        # 计算目录大小
                        total_size = 0
                        file_count = 0
                        for file_path in model_dir.rglob('*'):
                            if file_path.is_file():
                                total_size += file_path.stat().st_size
                                file_count += 1
                        
                        models_info[model_dir.name] = {
                            'size': total_size,
                            'size_mb': round(total_size / 1024 / 1024, 2),
                            'file_count': file_count,
                            'modified': datetime.fromtimestamp(model_dir.stat().st_mtime).strftime('%H:%M:%S')
                        }
            
            return models_info
            
        except Exception as e:
            return {'error': str(e)}
    
    def check_service_health(self) -> Dict:
        """检查服务健康状态"""
        health = {}
        
        # 检查后端API
        try:
            response = requests.get(f'http://localhost:{self.backend_port}/health', timeout=5)
            health['backend'] = {
                'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                'response_time': response.elapsed.total_seconds(),
                'status_code': response.status_code
            }
        except Exception as e:
            health['backend'] = {'status': 'down', 'error': str(e)}
        
        # 检查前端
        try:
            response = requests.get(f'http://localhost:{self.frontend_port}', timeout=5)
            health['frontend'] = {
                'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                'response_time': response.elapsed.total_seconds(),
                'status_code': response.status_code
            }
        except Exception as e:
            health['frontend'] = {'status': 'down', 'error': str(e)}
        
        return health
    
    def format_bytes(self, bytes_value: int) -> str:
        """格式化字节数"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    
    def display_monitor_data(self, data: Dict):
        """显示监控数据 - 紧凑一屏显示"""
        self.clear_screen()
        
        current_time = datetime.now()
        uptime = current_time - self.start_time
        
        print("=" * 120)
        print(f"🏦 银行代码检索系统监控 | {current_time.strftime('%H:%M:%S')} | 运行: {str(uptime).split('.')[0]} | 刷新: 20s | Ctrl+C退出")
        print("=" * 120)
        
        # 第一行：系统资源 + 服务状态
        sys_line = ""
        if 'system' in data and 'error' not in data['system']:
            sys_data = data['system']
            sys_line = f"🖥️ CPU:{sys_data['cpu']['percent']:.1f}% | 内存:{sys_data['memory']['percent']:.1f}%({self.format_bytes(sys_data['memory']['used'])}) | 磁盘:{sys_data['disk']['percent']:.1f}%"
        
        health_line = ""
        if 'health' in data:
            backend_status = "✅" if data['health'].get('backend', {}).get('status') == 'healthy' else "❌"
            frontend_status = "✅" if data['health'].get('frontend', {}).get('status') == 'healthy' else "❌"
            health_line = f"🌐 后端:{backend_status} 前端:{frontend_status}"
        
        print(f"{sys_line:<70} {health_line}")
        
        # 第二行：端口 + 数据库
        port_line = ""
        if 'ports' in data:
            port_8000 = "✅" if data['ports'].get(8000, {}).get('status') == 'occupied' else "❌"
            port_3000 = "✅" if data['ports'].get(3000, {}).get('status') == 'occupied' else "❌"
            port_line = f"🔌 端口 8000:{port_8000} 3000:{port_3000}"
        
        db_line = ""
        if 'database' in data:
            db_data = data['database']
            if db_data['status'] == 'connected':
                # 只显示关键表的记录数
                key_tables = ['training_jobs', 'bank_codes', 'qa_pairs']
                table_info = []
                for table in key_tables:
                    if table in db_data['tables']:
                        count = db_data['tables'][table]
                        if isinstance(count, int) and count > 0:
                            table_info.append(f"{table}:{count}")
                db_line = f"🗄️ DB:✅({db_data['size_mb']}MB) {' '.join(table_info[:2])}"
            else:
                db_line = f"🗄️ DB:❌"
        
        print(f"{port_line:<70} {db_line}")
        
        # 第三行：进程状态
        if 'processes' in data and data['processes']:
            proc_info = []
            for proc in data['processes'][:2]:  # 只显示前2个进程
                if 'error' not in proc:
                    proc_info.append(f"PID{proc['pid']}({proc['name'][:8]}):CPU{proc['cpu_percent']:.1f}%")
            if proc_info:
                print(f"🔄 进程: {' | '.join(proc_info)}")
        
        # 训练任务状态 - 重点显示
        if 'training' in data and 'jobs' in data['training']:
            jobs = data['training']['jobs']
            if jobs:
                print("\n🤖 训练任务:")
                for job in jobs[:2]:  # 只显示前2个任务
                    status_icon = "🟢" if job['status'] == 'running' else "✅" if job['status'] == 'completed' else "❌"
                    
                    if job['status'] == 'running':
                        progress_bar = self.create_progress_bar(job['progress'] or 0, 30)
                        print(f"   任务{job['id']}: {status_icon} {job['model_name'][:15]} | {progress_bar} {job['progress']:.2f}%")
                        
                        step_info = f"步骤:{job['current_step']}/{job['total_steps']}" if job['current_step'] and job['total_steps'] else "步骤:计算中"
                        loss_info = f"损失:{job['train_loss']:.4f}" if job['train_loss'] else "损失:--"
                        time_info = f"用时:{job['runtime']}" if job['runtime'] else "用时:--"
                        eta_info = f"剩余:{job['eta']}" if job['eta'] else "剩余:计算中"
                        
                        print(f"          {step_info} | {loss_info} | {time_info} | {eta_info}")
                        
                    elif job['status'] == 'completed':
                        print(f"   任务{job['id']}: {status_icon} {job['model_name'][:15]} | 已完成 | 用时:{job['runtime']} | 损失:{job['train_loss']:.4f}" if job['train_loss'] else "")
                    else:
                        print(f"   任务{job['id']}: {status_icon} {job['status']} | {job['model_name'][:15]}")
            else:
                print("\n🤖 训练任务: 暂无")
        
        # 模型存储 - 简化显示
        if 'models' in data and data['models']:
            total_size = sum(model['size'] for model in data['models'].values() if isinstance(model, dict))
            model_count = len([m for m in data['models'].values() if isinstance(m, dict) and m['size'] > 0])
            print(f"\n💾 模型存储: {self.format_bytes(total_size)} ({model_count}个模型)")
        
        # 最新日志 - 只显示今天的关键日志
        if 'logs' in data and data['logs']:
            today_logs = []
            for log_name, log_info in data['logs'].items():
                if isinstance(log_info, dict) and '2026-01-31' in log_name and log_info['size'] > 0:
                    today_logs.append((log_name, log_info))
            
            if today_logs:
                print(f"\n📋 今日日志:")
                for log_name, log_info in today_logs[:2]:  # 只显示2个最重要的日志
                    print(f"   {log_name}: {log_info['size_mb']}MB (更新:{log_info['modified']})")
                    if log_info['last_lines']:
                        last_line = log_info['last_lines'][-1]
                        # 提取关键信息
                        if 'ERROR' in last_line:
                            key_part = last_line.split('ERROR')[1][:60] if 'ERROR' in last_line else last_line[:60]
                            print(f"      ❌ {key_part}...")
                        elif 'Training' in last_line or '训练' in last_line:
                            key_part = last_line.split('|')[-1][:60] if '|' in last_line else last_line[:60]
                            print(f"      🤖 {key_part.strip()}...")
        
        print("\n" + "=" * 120)
    
    def create_progress_bar(self, percentage: float, width: int = 20) -> str:
        """创建进度条"""
        filled = int(width * percentage / 100)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}]"
    
    def run_monitor(self):
        """运行监控循环"""
        print("🚀 启动银行代码检索系统监控...")
        print("📊 正在收集系统信息...")
        
        try:
            while True:
                # 收集所有监控数据
                monitor_data = {
                    'system': self.get_system_resources(),
                    'processes': self.get_project_processes(),
                    'ports': self.get_port_status(),
                    'health': self.check_service_health(),
                    'database': self.get_database_status(),
                    'training': self.get_training_status(),
                    'models': self.get_model_storage_status(),
                    'logs': self.get_log_status()
                }
                
                # 显示监控数据
                self.display_monitor_data(monitor_data)
                
                # 等待20秒
                time.sleep(20)
                
        except KeyboardInterrupt:
            print("\n\n👋 监控已停止")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ 监控出错: {e}")
            sys.exit(1)

if __name__ == "__main__":
    monitor = SystemMonitor()
    monitor.run_monitor()