"""
BankCode Schemas - 银行联行号数据的Pydantic模式

本模块定义银行联行号相关的数据模型。

模式列表：
    - BankCodeBase: 基础银行联行号模式
    - BankCodeCreate: 创建银行联行号请求
    - BankCodeUpdate: 更新银行联行号请求
    - BankCodeResponse: 银行联行号响应
    - BankCodePreview: 银行联行号预览（简化版）

使用示例：
    >>> # 创建银行联行号
    >>> bank_code = BankCodeCreate(
    ...     bank_name="中国工商银行北京分行",
    ...     bank_code="102100099996",
    ...     clearing_code="102100099996",
    ...     dataset_id=1
    ... )
    >>> 
    >>> # 更新银行联行号
    >>> update = BankCodeUpdate(is_valid=False)

验证规则：
    - bank_name: 1-200个字符
    - bank_code: 必须是12位数字
    - clearing_code: 必须是12位数字
    - 使用自定义validator验证代码格式
"""
from pydantic import BaseModel, Field, validator
from typing import Optional


class BankCodeBase(BaseModel):
    """
    基础银行联行号模式
    
    定义银行联行号的核心字段。
    
    属性：
        bank_name (str): 银行名称，1-200个字符
        bank_code (str): 银行联行号，必须是12位数字
        clearing_code (str): 清算行行号，必须是12位数字
    """
    bank_name: str = Field(..., min_length=1, max_length=200)
    bank_code: str = Field(..., min_length=12, max_length=12)
    clearing_code: str = Field(..., min_length=12, max_length=12)
    
    @validator('bank_code', 'clearing_code')
    def validate_code_format(cls, v):
        """
        验证联行号和清算行行号格式
        
        规则：
            - 必须只包含数字
            - 必须是12位
        
        Args:
            v (str): 待验证的代码
        
        Returns:
            str: 验证通过的代码
        
        Raises:
            ValueError: 如果代码格式不正确
        """
        if not v.isdigit():
            raise ValueError('Code must contain only digits')
        if len(v) != 12:
            raise ValueError('Code must be exactly 12 digits')
        return v


class BankCodeCreate(BankCodeBase):
    """
    创建银行联行号请求模式
    
    用于创建新的银行联行号记录。
    
    属性：
        继承自BankCodeBase的所有字段
        dataset_id (Optional[int]): 所属数据集ID
        is_valid (bool): 记录是否有效，默认为True
    """
    dataset_id: Optional[int] = None
    is_valid: bool = True


class BankCodeUpdate(BaseModel):
    """
    更新银行联行号请求模式
    
    用于更新现有的银行联行号记录。所有字段都是可选的。
    
    属性：
        bank_name (Optional[str]): 新的银行名称
        bank_code (Optional[str]): 新的银行联行号
        clearing_code (Optional[str]): 新的清算行行号
        is_valid (Optional[bool]): 新的有效状态
    """
    bank_name: Optional[str] = None
    bank_code: Optional[str] = None
    clearing_code: Optional[str] = None
    is_valid: Optional[bool] = None


class BankCodeResponse(BankCodeBase):
    """
    银行联行号响应模式
    
    用于返回银行联行号的完整信息。
    
    属性：
        继承自BankCodeBase的所有字段
        id (int): 记录ID
        dataset_id (Optional[int]): 所属数据集ID
        is_valid (bool): 记录是否有效
        created_at (str): 创建时间
    """
    id: int
    dataset_id: Optional[int]
    is_valid: bool
    created_at: str
    
    class Config:
        from_attributes = True


class BankCodePreview(BaseModel):
    """
    银行联行号预览模式
    
    用于返回银行联行号的简化信息（用于预览）。
    
    属性：
        bank_name (str): 银行名称
        bank_code (str): 银行联行号
        clearing_code (str): 清算行行号
    """
    bank_name: str
    bank_code: str
    clearing_code: str
    
    class Config:
        from_attributes = True
