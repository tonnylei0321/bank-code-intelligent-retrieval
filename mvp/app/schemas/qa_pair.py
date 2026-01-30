"""
QA Pair Schemas - 问答对数据的Pydantic模式

本模块定义问答对相关的数据模型。

模式列表：
    - QAPairBase: 基础问答对模式
    - QAPairCreate: 创建问答对请求
    - QAPairResponse: 问答对响应
    - QAPairStats: 问答对统计信息
    - GenerationRequest: 问答对生成请求
    - GenerationResult: 问答对生成结果

使用示例：
    >>> # 生成问答对请求
    >>> request = GenerationRequest(
    ...     dataset_id=1,
    ...     question_types=["exact", "fuzzy", "reverse", "natural"],
    ...     train_ratio=0.8,
    ...     val_ratio=0.1,
    ...     test_ratio=0.1
    ... )
    >>> 
    >>> # 创建问答对
    >>> qa_pair = QAPairCreate(
    ...     dataset_id=1,
    ...     source_record_id=100,
    ...     question="工商银行的联行号是什么？",
    ...     answer="工商银行的联行号是102100099996",
    ...     question_type="exact",
    ...     split_type="train"
    ... )

问题类型说明：
    - exact: 精确匹配问题
    - fuzzy: 模糊匹配问题
    - reverse: 反向查询问题
    - natural: 自然语言问题

数据集划分说明：
    - train: 训练集（用于训练模型）
    - val: 验证集（用于调整超参数）
    - test: 测试集（用于最终评估）
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class QAPairBase(BaseModel):
    """Base QA Pair schema"""
    question: str = Field(..., description="Question text")
    answer: str = Field(..., description="Answer text")
    question_type: str = Field(..., description="Question type: exact, fuzzy, reverse, natural")
    split_type: str = Field(..., description="Split type: train, val, test")


class QAPairCreate(QAPairBase):
    """Schema for creating a QA pair"""
    dataset_id: int = Field(..., description="Dataset ID")
    source_record_id: Optional[int] = Field(None, description="Source bank code record ID")


class QAPairResponse(QAPairBase):
    """Schema for QA pair response"""
    id: int
    dataset_id: int
    source_record_id: Optional[int]
    generated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class QAPairStats(BaseModel):
    """Schema for QA pair statistics"""
    dataset_id: int
    total_pairs: int
    train_pairs: int
    val_pairs: int
    test_pairs: int
    exact_pairs: int
    fuzzy_pairs: int
    reverse_pairs: int
    natural_pairs: int


class GenerationRequest(BaseModel):
    """Schema for QA pair generation request"""
    dataset_id: int = Field(..., description="Dataset ID to generate QA pairs from")
    question_types: list[str] = Field(
        default=["exact", "fuzzy", "reverse", "natural"],
        description="Types of questions to generate"
    )
    train_ratio: float = Field(default=0.8, ge=0.0, le=1.0, description="Training set ratio")
    val_ratio: float = Field(default=0.1, ge=0.0, le=1.0, description="Validation set ratio")
    test_ratio: float = Field(default=0.1, ge=0.0, le=1.0, description="Test set ratio")


class GenerationResult(BaseModel):
    """Schema for QA pair generation result"""
    dataset_id: int
    total_generated: int
    train_count: int
    val_count: int
    test_count: int
    question_type_counts: dict[str, int]
    errors: list[str] = []
