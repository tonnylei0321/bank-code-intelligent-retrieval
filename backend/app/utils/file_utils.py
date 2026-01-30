"""
文件处理工具函数
"""

import os
import hashlib
import mimetypes
from typing import List, Optional, Tuple
from pathlib import Path
import pandas as pd
from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import ValidationError, DataError


def get_file_hash(file_path: str) -> str:
    """
    计算文件SHA256哈希值
    """
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def get_file_extension(filename: str) -> str:
    """
    获取文件扩展名
    """
    return Path(filename).suffix.lower()


def is_allowed_file(filename: str) -> bool:
    """
    检查文件扩展名是否允许
    """
    extension = get_file_extension(filename)
    return extension in settings.UPLOAD_ALLOWED_EXTENSIONS


def validate_file_size(file_size: int) -> bool:
    """
    验证文件大小
    """
    return file_size <= settings.UPLOAD_MAX_SIZE


async def save_upload_file(upload_file: UploadFile, save_path: str) -> Tuple[str, int]:
    """
    保存上传的文件
    
    Returns:
        Tuple[str, int]: (文件路径, 文件大小)
    """
    # 验证文件类型
    if not is_allowed_file(upload_file.filename):
        raise ValidationError(f"不支持的文件类型: {get_file_extension(upload_file.filename)}")
    
    # 创建保存目录
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    # 保存文件
    file_size = 0
    with open(save_path, "wb") as f:
        while chunk := await upload_file.read(8192):
            file_size += len(chunk)
            
            # 检查文件大小
            if file_size > settings.UPLOAD_MAX_SIZE:
                # 删除已保存的部分文件
                os.remove(save_path)
                raise ValidationError(f"文件大小超过限制: {settings.UPLOAD_MAX_SIZE} bytes")
            
            f.write(chunk)
    
    return save_path, file_size


def read_dataset_file(file_path: str, file_format: str) -> pd.DataFrame:
    """
    读取数据集文件
    """
    try:
        if file_format == "csv":
            df = pd.read_csv(file_path, encoding='utf-8')
        elif file_format == "txt":
            df = pd.read_csv(file_path, sep='\t', encoding='utf-8')
        elif file_format == "excel":
            df = pd.read_excel(file_path)
        else:
            raise DataError(f"不支持的文件格式: {file_format}")
        
        return df
    except Exception as e:
        raise DataError(f"读取文件失败: {str(e)}")


def validate_bank_data_format(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    验证银行数据格式
    
    Returns:
        Tuple[bool, List[str]]: (是否有效, 错误信息列表)
    """
    errors = []
    
    # 检查列数
    if len(df.columns) != 3:
        errors.append(f"数据列数不正确，期望3列，实际{len(df.columns)}列")
        return False, errors
    
    # 重命名列
    df.columns = ['bank_name', 'bank_code', 'clearing_code']
    
    # 检查必需列
    required_columns = ['bank_name', 'bank_code', 'clearing_code']
    for col in required_columns:
        if col not in df.columns:
            errors.append(f"缺少必需列: {col}")
    
    if errors:
        return False, errors
    
    # 检查数据类型和格式
    for index, row in df.iterrows():
        line_errors = []
        
        # 检查银行名称
        if pd.isna(row['bank_name']) or str(row['bank_name']).strip() == '':
            line_errors.append("银行名称不能为空")
        
        # 检查联行号
        bank_code = str(row['bank_code']).strip()
        if not bank_code or len(bank_code) != 12 or not bank_code.isdigit():
            line_errors.append("联行号格式错误（应为12位数字）")
        
        # 检查清算行行号
        clearing_code = str(row['clearing_code']).strip()
        if not clearing_code or len(clearing_code) != 12 or not clearing_code.isdigit():
            line_errors.append("清算行行号格式错误（应为12位数字）")
        
        if line_errors:
            errors.append(f"第{index + 1}行: {'; '.join(line_errors)}")
    
    return len(errors) == 0, errors


def generate_unique_filename(original_filename: str, user_id: int) -> str:
    """
    生成唯一的文件名
    """
    import uuid
    from datetime import datetime
    
    # 获取文件扩展名
    extension = get_file_extension(original_filename)
    
    # 生成唯一标识
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    
    # 构造新文件名
    new_filename = f"user_{user_id}_{timestamp}_{unique_id}{extension}"
    
    return new_filename


def get_file_info(file_path: str) -> dict:
    """
    获取文件信息
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    stat = os.stat(file_path)
    
    return {
        "size": stat.st_size,
        "created_at": stat.st_ctime,
        "modified_at": stat.st_mtime,
        "mime_type": mimetypes.guess_type(file_path)[0]
    }