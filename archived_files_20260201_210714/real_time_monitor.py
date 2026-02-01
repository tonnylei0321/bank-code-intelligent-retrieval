#!/usr/bin/env python3
"""
实时系统监控脚本
监控日志文件变化，实时检测和报告错误
"""
import os
import time
import re
from datetime import datetime
from collections import defaultdict
import subprocess

class RealTimeMonitor:
    def __init__(self):
        self.mvp_dir = "."
        self.logs_dir = os.path.join(self.mvp_dir, "logs")
        self.error_patterns = {
            "数据库错误": r"sqlite3\.OperationalError|no such column|database.*locked",
            "API密钥错误": r"QWEN_API_KEY|OPENAI_API_KEY.*failed|Illegal header value.*Bearer",
            "智能问答错误": r"智能问答服务.*失败|Failed to get user history|QA.*failed",
            "模型服务错误": r"NoneType.*object has no attribute.*chat|Local model not initialized",
            "Redis错误": r"Redis.*failed|Redis.*error|Redis.*timeout",
            "训练任务错误": r"training_jobs.*retry_count|Training.*failed",
            "文件上传错误": r"上传失败|upload.*failed|File.*error",
            "权限错误": r"Not authenticated|Unauthorized|Permission denied",
            "HTTP错误": r"HTTPException|status_code.*[45]\d\d",
            "内存错误": r"MemoryError|OutOfMemoryError|memory.*exceeded"
        }
        
        self.last_positions = {}
        self.error_counts = defaultdict(int)
        self.last_check_time = datetime.now()
        
    def get_log_files(self):
        """获取需要监控的日志文件"""
        log_files = []
        
        # 主要日志文件
        main_logs = [
            "backend.log",
            os.path.join("logs", "app_2026-02-01.log"),
            os.path.join("logs", "error_2026-02-01.log")
        ]
        
        for log_file in main_logs:
            full_path = os.path.join(self.mvp_dir, log_file)
            if os.path.exists(full_path):
                log_files.append(full_path)
        
        return log_files
    
    def read_new_lines(self, file_path):
        """读取文件中的新行"""
        try:
            current_size = os.path.getsize(file_path)
            last_position = self.last_positions.get(file_path, 0)
            
            if current_size < last_position:
                # 文件被重置，从头开始读
                last_position = 0
            
            if current_size == last_position:
                # 没有新内容
                return []
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(last_position)
                new_lines = f.readlines()
                self.last_positions[file_path] = f.tell()
            
            return new_lines
            
        except Exception as e:
            print(f"⚠️ 读取日志文件失败 {file_path}: {e}")
            return []
    
    def analyze_lines(self, lines, file_path):
        """分析日志行，检测错误"""
        errors_found = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 检查错误模式
            for error_type, pattern in self.error_patterns.items():
                if re.search(pattern, line, re.IGNORECASE):
                    self.error_counts[error_type] += 1
                    
                    # 提取时间戳
                    timestamp_match = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', line)
                    timestamp = timestamp_match.group() if timestamp_match else "未知时间"
                    
                    errors_found.append({
                        'type': error_type,
                        'timestamp': timestamp,
                        'file': os.path.basename(file_path),
                        'message': line[:200] + "..." if len(line) > 200 else line
                    })
                    break  # 避免重复匹配
        
        return errors_found
    
    def check_service_status(self):
        """检查服务状态"""
        services = {}
        
        # 检查后端服务
        try:
            result = subprocess.run(['lsof', '-ti:8000'], capture_output=True, text=True, timeout=2)
            services['backend'] = result.returncode == 0 and result.stdout.strip()
        except:
            services['backend'] = False
        
        # 检查前端服务
        try:
            result = subprocess.run(['lsof', '-ti:3000'], capture_output=True, text=True, timeout=2)
            services['frontend'] = result.returncode == 0 and result.stdout.strip()
        except:
            services['frontend'] = False
        
        # 检查Redis
        try:
            result = subprocess.run(['redis-cli', 'ping'], capture_output=True, text=True, timeout=2)
            services['redis'] = result.returncode == 0 and 'PONG' in result.stdout
        except:
            services['redis'] = False
        
        return services
    
    def print_status_header(self):
        """打印状态头部"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n{'='*80}")
        print(f"🔍 实时系统监控 - {current_time}")
        print(f"{'='*80}")
        
        # 检查服务状态
        services = self.check_service_status()
        print("📊 服务状态:")
        for service, status in services.items():
            status_icon = "🟢" if status else "🔴"
            print(f"  {status_icon} {service.capitalize()}: {'运行中' if status else '未运行'}")
        
        # 显示错误统计
        if self.error_counts:
            print("\n⚠️ 错误统计:")
            for error_type, count in sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  - {error_type}: {count} 次")
        else:
            print("\n✅ 暂无错误")
        
        print(f"\n🕐 监控中... (按 Ctrl+C 停止)")
    
    def print_error(self, error):
        """打印错误信息"""
        print(f"\n🚨 [{error['timestamp']}] {error['type']}")
        print(f"📁 文件: {error['file']}")
        print(f"💬 消息: {error['message']}")
        
        # 根据错误类型提供修复建议
        suggestions = {
            "数据库错误": "建议检查数据库连接和表结构",
            "API密钥错误": "建议检查.env文件中的API密钥配置",
            "智能问答错误": "建议检查Redis连接和模型服务状态",
            "模型服务错误": "建议检查API密钥配置和网络连接",
            "Redis错误": "建议检查Redis服务状态",
            "训练任务错误": "建议检查训练任务配置和资源",
            "HTTP错误": "建议检查API请求参数和权限"
        }
        
        if error['type'] in suggestions:
            print(f"💡 建议: {suggestions[error['type']]}")
    
    def run(self):
        """运行实时监控"""
        print("🚀 启动实时系统监控...")
        
        # 初始化日志文件位置
        log_files = self.get_log_files()
        for file_path in log_files:
            try:
                self.last_positions[file_path] = os.path.getsize(file_path)
            except:
                self.last_positions[file_path] = 0
        
        print(f"📋 监控文件: {len(log_files)} 个")
        for file_path in log_files:
            print(f"  - {os.path.basename(file_path)}")
        
        self.print_status_header()
        
        try:
            while True:
                current_time = datetime.now()
                
                # 每30秒打印一次状态头部
                if (current_time - self.last_check_time).seconds >= 30:
                    self.print_status_header()
                    self.last_check_time = current_time
                
                # 检查所有日志文件
                for file_path in log_files:
                    new_lines = self.read_new_lines(file_path)
                    if new_lines:
                        errors = self.analyze_lines(new_lines, file_path)
                        for error in errors:
                            self.print_error(error)
                
                time.sleep(1)  # 每秒检查一次
                
        except KeyboardInterrupt:
            print(f"\n\n🛑 监控已停止")
            print(f"📊 本次监控统计:")
            if self.error_counts:
                for error_type, count in sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True):
                    print(f"  - {error_type}: {count} 次")
            else:
                print("  ✅ 未发现错误")

def main():
    monitor = RealTimeMonitor()
    monitor.run()

if __name__ == "__main__":
    main()