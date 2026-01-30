#!/usr/bin/env python3
"""
GPU内存清理工具

用于清理PyTorch在MPS设备上的内存占用，解决内存不足问题。
"""

import torch
import gc
import os
import psutil

def get_memory_info():
    """获取系统内存信息"""
    memory = psutil.virtual_memory()
    print(f"系统内存:")
    print(f"  总内存: {memory.total / (1024**3):.2f} GB")
    print(f"  已使用: {memory.used / (1024**3):.2f} GB")
    print(f"  可用内存: {memory.available / (1024**3):.2f} GB")
    print(f"  使用率: {memory.percent:.1f}%")

def clear_pytorch_cache():
    """清理PyTorch缓存"""
    print("\n清理PyTorch缓存...")
    
    # 清理CUDA缓存（如果有）
    if torch.cuda.is_available():
        print("清理CUDA缓存...")
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
    
    # 清理MPS缓存（Apple Silicon）
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        print("清理MPS缓存...")
        torch.mps.empty_cache()
    
    # 强制垃圾回收
    print("执行垃圾回收...")
    gc.collect()
    
    print("✅ PyTorch缓存清理完成")

def clear_model_cache_via_api():
    """通过API清理模型缓存"""
    try:
        import requests
        
        # 获取管理员token（需要先登录）
        print("\n通过API清理模型缓存...")
        print("请确保已经以管理员身份登录系统")
        
        # 这里需要实际的token，用户需要手动提供
        token = input("请输入管理员token（或按Enter跳过API清理）: ").strip()
        
        if token:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.post(
                "http://localhost:8001/api/v1/query/clear-model-cache",
                headers=headers
            )
            
            if response.status_code == 200:
                print("✅ API模型缓存清理成功")
                print(response.json().get('message', ''))
            else:
                print(f"❌ API清理失败: {response.status_code}")
                print(response.text)
        else:
            print("跳过API清理")
            
    except Exception as e:
        print(f"❌ API清理出错: {e}")

def main():
    """主函数"""
    print("🧹 GPU内存清理工具")
    print("=" * 50)
    
    # 显示内存信息
    get_memory_info()
    
    # 清理PyTorch缓存
    clear_pytorch_cache()
    
    # 显示清理后的内存信息
    print("\n清理后的内存状态:")
    get_memory_info()
    
    # 尝试通过API清理模型缓存
    clear_model_cache_via_api()
    
    print("\n🎉 内存清理完成！")
    print("\n💡 如果仍然有内存问题，建议:")
    print("1. 重启后端服务")
    print("2. 使用更小的模型（如Qwen2.5-0.5B）")
    print("3. 设置环境变量: export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0")

if __name__ == "__main__":
    main()