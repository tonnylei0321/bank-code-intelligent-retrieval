"""
Dataset Schemas - 数据集的Pydantic模式

本模块定义数据集相关的数据模型。

模式列表：
    - DatasetBase: 基础数据集模式
    - DatasetCreate: 创建数据集请求
    - DatasetUpdate: 更新数据集请求
    - DatasetResponse: 数据集响应
    - DatasetStats: 数据集统计信息
    - ValidationResult: 数据验证结果

使用示例：
    >>> # 创建数据集
    >>> dataset = DatasetCreate(
    ...     filename="bank_codes.xlsx",
    ...     file_path="/uploads/bank_codes_20240101.xlsx",
    ...     file_size=1024000,
    ...     total_records=1000,
    ...     valid_records=950,
    ...     invalid_records=50
    ... )
    >>> 
    >>> # 更新数据集状态
    >>> update = DatasetUpdate(status="validated")
    >>> 
    >>> # 验证结果
    >>> result = ValidationResult(
    ...     dataset_id=1,
    ...     total_records=1000,
    ...     valid_records=950,
    ...     invalid_records=50,
    ...     errors=["第10行：联行号格式错误"],
    ...     status="validated"
    ... )

状态说明：
    - uploaded: 已上传，尚未验证
    - validated: 已验证，数据有效
    - indexed: 已索引到Elasticsearch
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DatasetBase(BaseModel):
    """
    基础数据集模式
    
    定义数据集的核心字段。
    
    属性：
        filename (str): 文件名
        file_size (int): 文件大小（字节）
    """
    filename: str
    file_size: int


class DatasetCreate(DatasetBase):
    """
    创建数据集请求模式
    
    用于创建新的数据集记录。
    
    属性：
        继承自DatasetBase的所有字段
        file_path (str): 文件存储路径
        total_records (int): 总记录数，默认为0
        valid_records (int): 有效记录数，默认为0
        invalid_records (int): 无效记录数，默认为0
        uploaded_by (Optional[int]): 上传用户ID
    """
    file_path: str
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    uploaded_by: Optional[int] = None


class DatasetUpdate(BaseModel):
    """
    更新数据集请求模式
    
    用于更新现有的数据集记录。所有字段都是可选的。
    
    属性：
        status (Optional[str]): 新的状态
        total_records (Optional[int]): 新的总记录数
        valid_records (Optional[int]): 新的有效记录数
        invalid_records (Optional[int]): 新的无效记录数
    """
    status: Optional[str] = None
    total_records: Optional[int] = None
    valid_records: Optional[int] = None
    invalid_records: Optional[int] = None


class DatasetResponse(DatasetBase):
    """
    数据集响应模式
    
    用于返回数据集的完整信息。
    
    属性：
        继承自DatasetBase的所有字段
        id (int): 数据集ID
        file_path (str): 文件存储路径
        total_records (int): 总记录数
        valid_records (int): 有效记录数
        invalid_records (int): 无效记录数
        status (str): 数据集状态
        uploaded_by (Optional[int]): 上传用户ID
        created_at (str): 创建时间
        updated_at (str): 更新时间
    """
    id: int
    file_path: str
    total_records: int
    valid_records: int
    invalid_records: int
    status: str
    uploaded_by: Optional[int]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class DatasetStats(BaseModel):
    """
    数据集统计信息模式
    
    用于返回数据集的统计摘要。
    
    属性：
        id (int): 数据集ID
        filename (str): 文件名
        total_records (int): 总记录数
        valid_records (int): 有效记录数
        invalid_records (int): 无效记录数
        status (str): 数据集状态
        created_at (str): 创建时间
    """
    id: int
    filename: str
    total_records: int
    valid_records: int
    invalid_records: int
    status: str
    created_at: str


class ValidationResult(BaseModel):
    """
    数据验证结果模式
    
    用于返回数据集验证的结果。
    
    属性：
        dataset_id (int): 数据集ID
        total_records (int): 总记录数
        valid_records (int): 有效记录数
        invalid_records (int): 无效记录数
        errors (list[str]): 错误信息列表
        status (str): 验证后的状态
    """
    dataset_id: int
    total_records: int
    valid_records: int
    invalid_records: int
    errors: list[str] = Field(default_factory=list)
    status: str
