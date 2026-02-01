#!/usr/bin/env python3
"""
RAG系统依赖安装脚本

本脚本用于安装RAG系统所需的依赖包，包括：
- ChromaDB向量数据库
- sentence-transformers嵌入模型
- 相关的机器学习依赖

使用方法：
    python install_rag_dependencies.py
"""
import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """运行命令并处理错误"""
    print(f"\n🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description}完成")
        if result.stdout:
            print(f"输出: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description}失败")
        print(f"错误: {e.stderr.strip()}")
        return False

def main():
    print("🚀 开始安装RAG系统依赖...")
    
    # 检查是否在虚拟环境中
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  建议在虚拟环境中运行此脚本")
        response = input("是否继续？(y/N): ")
        if response.lower() != 'y':
            print("安装已取消")
            return
    
    # 检查当前目录
    current_dir = Path.cwd()
    if not (current_dir / "requirements.txt").exists():
        print("❌ 请在mvp目录中运行此脚本")
        return
    
    # 安装依赖
    commands = [
        ("pip install --upgrade pip", "升级pip"),
        ("pip install chromadb==0.4.18", "安装ChromaDB向量数据库"),
        ("pip install sentence-transformers==2.2.2", "安装sentence-transformers"),
        ("pip install numpy==1.24.3", "安装NumPy"),
    ]
    
    failed_commands = []
    
    for command, description in commands:
        if not run_command(command, description):
            failed_commands.append(description)
    
    # 验证安装
    print("\n🔍 验证安装...")
    
    try:
        import chromadb
        print("✅ ChromaDB安装成功")
    except ImportError:
        print("❌ ChromaDB安装失败")
        failed_commands.append("ChromaDB验证")
    
    try:
        import sentence_transformers
        print("✅ sentence-transformers安装成功")
    except ImportError:
        print("❌ sentence-transformers安装失败")
        failed_commands.append("sentence-transformers验证")
    
    try:
        import numpy
        print("✅ NumPy安装成功")
    except ImportError:
        print("❌ NumPy安装失败")
        failed_commands.append("NumPy验证")
    
    # 创建必要的目录
    print("\n📁 创建必要的目录...")
    directories = [
        "data/vector_db",
        "reports"
    ]
    
    for directory in directories:
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ 创建目录: {directory}")
    
    # 总结
    print("\n" + "="*50)
    if failed_commands:
        print("❌ 安装过程中遇到以下问题:")
        for cmd in failed_commands:
            print(f"   - {cmd}")
        print("\n请手动解决这些问题后重新运行脚本")
    else:
        print("🎉 RAG系统依赖安装完成！")
        print("\n下一步:")
        print("1. 重启后端服务: ./cleanup_and_restart.sh")
        print("2. 在管理界面中初始化RAG向量数据库")
        print("3. 测试RAG检索功能")
    
    print("="*50)

if __name__ == "__main__":
    main()