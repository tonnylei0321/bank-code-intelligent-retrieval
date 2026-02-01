#!/usr/bin/env python3
"""
检查MPS (Apple Silicon GPU) 可用性

这个脚本会检查：
1. PyTorch版本
2. MPS是否可用
3. MPS是否已构建
4. 当前会使用的设备
"""

import torch
import sys

def check_mps():
    """检查MPS可用性"""
    print("=" * 60)
    print("MPS (Apple Silicon GPU) 可用性检查")
    print("=" * 60)
    print()
    
    # 1. PyTorch版本
    print(f"✓ PyTorch版本: {torch.__version__}")
    
    # 2. MPS可用性
    if hasattr(torch.backends, 'mps'):
        mps_available = torch.backends.mps.is_available()
        mps_built = torch.backends.mps.is_built()
        
        print(f"{'✓' if mps_available else '✗'} MPS可用: {mps_available}")
        print(f"{'✓' if mps_built else '✗'} MPS已构建: {mps_built}")
        
        if mps_available and mps_built:
            print()
            print("🎉 MPS加速已启用！")
            print("   您的M1 MacBook Pro将使用GPU进行训练")
            print()
        else:
            print()
            print("⚠️  MPS不可用")
            if not mps_built:
                print("   原因: PyTorch未编译MPS支持")
                print("   解决: pip install --upgrade torch")
            print()
    else:
        print("✗ MPS不可用: PyTorch版本过旧")
        print("  需要PyTorch >= 1.12")
        print("  当前版本:", torch.__version__)
        print()
    
    # 3. CUDA检查
    cuda_available = torch.cuda.is_available()
    print(f"{'✓' if cuda_available else '✗'} CUDA可用: {cuda_available}")
    
    # 4. 确定使用的设备
    print()
    print("当前会使用的设备:")
    if torch.cuda.is_available():
        device = "cuda"
        print(f"  🚀 {device} (NVIDIA GPU)")
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device = "mps"
        print(f"  🍎 {device} (Apple Silicon GPU)")
    else:
        device = "cpu"
        print(f"  💻 {device}")
    
    print()
    print("=" * 60)
    
    # 5. 测试MPS
    if device == "mps":
        print()
        print("测试MPS设备...")
        try:
            # 创建一个小张量并移动到MPS
            x = torch.randn(10, 10)
            x_mps = x.to('mps')
            y_mps = x_mps @ x_mps.T
            y = y_mps.to('cpu')
            
            print("✓ MPS设备测试成功！")
            print(f"  张量形状: {y.shape}")
            print(f"  计算结果: {y[0, 0]:.4f}")
        except Exception as e:
            print(f"✗ MPS设备测试失败: {e}")
        print()
        print("=" * 60)
    
    return device

if __name__ == "__main__":
    device = check_mps()
    
    # 返回状态码
    if device == "mps":
        sys.exit(0)  # 成功
    else:
        sys.exit(1)  # MPS不可用
