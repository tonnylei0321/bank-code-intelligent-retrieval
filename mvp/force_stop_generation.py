#!/usr/bin/env python3
"""
强制停止智能生成任务
"""
import sys
import os
import signal
import psutil
import time

def find_and_stop_generation_process():
    """查找并停止生成进程"""
    stopped_processes = []
    
    try:
        # 查找所有Python进程
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                if 'python' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    
                    # 检查是否是生成相关的进程
                    if any(keyword in cmdline.lower() for keyword in [
                        'smart_sample_generator', 
                        'upload_and_generate',
                        'batch_generate',
                        'generate_samples'
                    ]):
                        print(f"🎯 发现生成进程:")
                        print(f"   PID: {proc.info['pid']}")
                        print(f"   命令: {cmdline[:100]}...")
                        print(f"   运行时间: {time.time() - proc.info['create_time']:.0f} 秒")
                        
                        # 尝试温和终止
                        print(f"   正在停止进程 {proc.info['pid']}...")
                        proc.terminate()
                        
                        # 等待进程结束
                        try:
                            proc.wait(timeout=10)
                            print(f"   ✅ 进程 {proc.info['pid']} 已正常停止")
                            stopped_processes.append(proc.info['pid'])
                        except psutil.TimeoutExpired:
                            print(f"   ⚠️  进程 {proc.info['pid']} 未响应，强制终止...")
                            proc.kill()
                            proc.wait(timeout=5)
                            print(f"   ✅ 进程 {proc.info['pid']} 已强制停止")
                            stopped_processes.append(proc.info['pid'])
                            
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
                
    except Exception as e:
        print(f"❌ 查找进程时出错: {e}")
    
    return stopped_processes

def restart_backend_clean():
    """重启后端服务以确保清理状态"""
    try:
        print("🔄 重启后端服务...")
        
        # 停止当前后端
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'uvicorn' in ' '.join(proc.info['cmdline']):
                    print(f"   停止后端进程 {proc.info['pid']}")
                    proc.terminate()
                    proc.wait(timeout=10)
                    break
            except:
                continue
        
        time.sleep(2)
        
        # 重新启动后端
        import subprocess
        cmd = "source venv/bin/activate && nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > backend.log 2>&1 &"
        subprocess.run(cmd, shell=True, cwd="/Users/leitao/工作目录/1_交易银行/0-个人目录/L-雷涛/12_WorkSpace/PProject/QWen-Create/mvp")
        
        print("   ✅ 后端服务已重启")
        return True
        
    except Exception as e:
        print(f"   ❌ 重启后端失败: {e}")
        return False

def main():
    print("=" * 60)
    print("🛑 强制停止智能生成任务")
    print("=" * 60)
    
    # 1. 查找并停止生成进程
    print("1. 查找生成进程...")
    stopped = find_and_stop_generation_process()
    
    if stopped:
        print(f"✅ 已停止 {len(stopped)} 个生成进程: {stopped}")
    else:
        print("ℹ️  未找到活跃的生成进程")
    
    # 2. 重启后端服务
    print("\n2. 重启后端服务...")
    restarted = restart_backend_clean()
    
    if restarted:
        print("✅ 后端服务已重启，生成任务已清理")
    else:
        print("❌ 后端重启失败")
    
    print("\n" + "=" * 60)
    print("🎯 建议下一步:")
    print("1. 使用现有的训练数据集进行训练")
    print("2. 或者重新上传小文件进行快速生成测试")
    print("3. 避免使用大文件进行LLM生成（太慢）")
    print("=" * 60)

if __name__ == "__main__":
    main()