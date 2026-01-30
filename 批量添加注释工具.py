#!/usr/bin/env python3
"""
批量添加中文注释工具

本工具用于辅助为Python代码文件添加中文注释。
提供交互式界面，逐个文件处理。

使用方法:
    python 批量添加注释工具.py

功能:
1. 扫描指定目录下的所有Python文件
2. 显示文件内容
3. 提供注释模板
4. 保存修改后的文件
"""

import os
import sys
from pathlib import Path
from typing import List, Dict
import ast


class CommentHelper:
    """中文注释辅助工具类"""
    
    # 注释模板
    MODULE_TEMPLATE = '''"""
{module_name}模块

{description}

主要功能:
1. {feature1}
2. {feature2}
3. {feature3}
"""'''
    
    CLASS_TEMPLATE = '''    """
    {class_name}类
    
    {description}
    
    Attributes:
        {attributes}
    """'''
    
    FUNCTION_TEMPLATE = '''    """
    {function_name}
    
    {description}
    
    Args:
        {args}
    
    Returns:
        {returns}
    
    Raises:
        {raises}
    """'''
    
    def __init__(self, base_dir: str = "mvp/app"):
        """
        初始化注释辅助工具
        
        Args:
            base_dir: 要处理的基础目录
        """
        self.base_dir = Path(base_dir)
        self.processed_files: List[str] = []
        self.skipped_files: List[str] = []
    
    def find_python_files(self) -> List[Path]:
        """
        查找所有Python文件
        
        Returns:
            Python文件路径列表
        """
        python_files = []
        for root, dirs, files in os.walk(self.base_dir):
            # 跳过__pycache__目录
            dirs[:] = [d for d in dirs if d != '__pycache__']
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        return sorted(python_files)
    
    def analyze_file(self, file_path: Path) -> Dict:
        """
        分析Python文件结构
        
        Args:
            file_path: 文件路径
        
        Returns:
            文件结构信息字典
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            info = {
                'path': file_path,
                'has_module_doc': ast.get_docstring(tree) is not None,
                'classes': [],
                'functions': [],
                'imports': []
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    info['classes'].append({
                        'name': node.name,
                        'has_doc': ast.get_docstring(node) is not None,
                        'line': node.lineno
                    })
                elif isinstance(node, ast.FunctionDef):
                    if not any(node.name == c['name'] for c in info['classes']):
                        info['functions'].append({
                            'name': node.name,
                            'has_doc': ast.get_docstring(node) is not None,
                            'line': node.lineno
                        })
            
            return info
        except Exception as e:
            print(f"分析文件失败 {file_path}: {e}")
            return None
    
    def display_file_info(self, info: Dict) -> None:
        """
        显示文件信息
        
        Args:
            info: 文件结构信息
        """
        print(f"\n{'='*60}")
        print(f"文件: {info['path']}")
        print(f"{'='*60}")
        print(f"模块文档: {'✓ 已有' if info['has_module_doc'] else '✗ 缺失'}")
        print(f"\n类 ({len(info['classes'])}个):")
        for cls in info['classes']:
            status = '✓' if cls['has_doc'] else '✗'
            print(f"  {status} {cls['name']} (行 {cls['line']})")
        
        print(f"\n函数 ({len(info['functions'])}个):")
        for func in info['functions']:
            status = '✓' if func['has_doc'] else '✗'
            print(f"  {status} {func['name']} (行 {func['line']})")
    
    def get_comment_suggestions(self, info: Dict) -> str:
        """
        生成注释建议
        
        Args:
            info: 文件结构信息
        
        Returns:
            注释建议文本
        """
        suggestions = []
        
        if not info['has_module_doc']:
            suggestions.append("需要添加模块级文档字符串")
        
        for cls in info['classes']:
            if not cls['has_doc']:
                suggestions.append(f"类 {cls['name']} 需要添加文档字符串")
        
        for func in info['functions']:
            if not func['has_doc']:
                suggestions.append(f"函数 {func['name']} 需要添加文档字符串")
        
        return "\n".join(suggestions) if suggestions else "所有项目都有文档字符串 ✓"
    
    def process_files(self) -> None:
        """处理所有文件的主流程"""
        files = self.find_python_files()
        total = len(files)
        
        print(f"\n找到 {total} 个Python文件")
        print("="*60)
        
        for idx, file_path in enumerate(files, 1):
            print(f"\n进度: {idx}/{total}")
            
            info = self.analyze_file(file_path)
            if not info:
                self.skipped_files.append(str(file_path))
                continue
            
            self.display_file_info(info)
            
            print(f"\n注释建议:")
            print(self.get_comment_suggestions(info))
            
            print(f"\n操作选项:")
            print("  1. 在编辑器中打开此文件")
            print("  2. 显示文件内容")
            print("  3. 标记为已处理")
            print("  4. 跳过此文件")
            print("  5. 退出程序")
            
            choice = input("\n请选择 (1-5): ").strip()
            
            if choice == '1':
                os.system(f"code {file_path}")  # 使用VS Code打开
                input("按Enter继续...")
                self.processed_files.append(str(file_path))
            elif choice == '2':
                self.display_file_content(file_path)
                input("按Enter继续...")
            elif choice == '3':
                self.processed_files.append(str(file_path))
                print(f"✓ 已标记为已处理")
            elif choice == '4':
                self.skipped_files.append(str(file_path))
                print(f"⊘ 已跳过")
            elif choice == '5':
                print("\n退出程序")
                break
        
        self.show_summary()
    
    def display_file_content(self, file_path: Path, lines: int = 50) -> None:
        """
        显示文件内容
        
        Args:
            file_path: 文件路径
            lines: 显示的行数
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.readlines()
            
            print(f"\n文件内容 (前{lines}行):")
            print("-"*60)
            for i, line in enumerate(content[:lines], 1):
                print(f"{i:4d} | {line}", end='')
            
            if len(content) > lines:
                print(f"\n... (还有 {len(content) - lines} 行)")
        except Exception as e:
            print(f"读取文件失败: {e}")
    
    def show_summary(self) -> None:
        """显示处理摘要"""
        print(f"\n{'='*60}")
        print("处理摘要")
        print(f"{'='*60}")
        print(f"已处理文件: {len(self.processed_files)}")
        print(f"跳过文件: {len(self.skipped_files)}")
        
        if self.processed_files:
            print(f"\n已处理的文件:")
            for f in self.processed_files:
                print(f"  ✓ {f}")
        
        if self.skipped_files:
            print(f"\n跳过的文件:")
            for f in self.skipped_files:
                print(f"  ⊘ {f}")


def main():
    """主函数"""
    print("="*60)
    print("Python代码中文注释辅助工具")
    print("="*60)
    
    print("\n请选择要处理的目录:")
    print("  1. mvp/app/core (核心模块)")
    print("  2. mvp/app/services (业务服务)")
    print("  3. mvp/app/models (数据模型)")
    print("  4. mvp/app/api (API接口)")
    print("  5. mvp/app/schemas (数据验证)")
    print("  6. mvp/app (所有模块)")
    print("  7. backend/app (后端项目)")
    print("  8. 自定义目录")
    
    choice = input("\n请选择 (1-8): ").strip()
    
    dir_map = {
        '1': 'mvp/app/core',
        '2': 'mvp/app/services',
        '3': 'mvp/app/models',
        '4': 'mvp/app/api',
        '5': 'mvp/app/schemas',
        '6': 'mvp/app',
        '7': 'backend/app'
    }
    
    if choice in dir_map:
        base_dir = dir_map[choice]
    elif choice == '8':
        base_dir = input("请输入目录路径: ").strip()
    else:
        print("无效选择")
        return
    
    if not os.path.exists(base_dir):
        print(f"目录不存在: {base_dir}")
        return
    
    helper = CommentHelper(base_dir)
    helper.process_files()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
        sys.exit(0)
