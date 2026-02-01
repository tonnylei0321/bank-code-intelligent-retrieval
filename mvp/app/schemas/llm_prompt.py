"""
LLM提示词相关的Pydantic模式
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class LLMPromptBase(BaseModel):
    """LLM提示词基础模式"""
    llm_name: str = Field(..., description="LLM名称")
    display_name: str = Field(..., description="显示名称")
    prompt_template: str = Field(..., description="提示词模板")
    is_active: bool = Field(True, description="是否启用")
    description: Optional[str] = Field(None, description="描述信息")


class LLMPromptCreate(LLMPromptBase):
    """创建LLM提示词请求"""
    pass


class LLMPromptUpdate(BaseModel):
    """更新LLM提示词请求"""
    display_name: Optional[str] = Field(None, description="显示名称")
    prompt_template: Optional[str] = Field(None, description="提示词模板")
    is_active: Optional[bool] = Field(None, description="是否启用")
    description: Optional[str] = Field(None, description="描述信息")


class LLMPromptResponse(LLMPromptBase):
    """LLM提示词响应"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LLMPromptListResponse(BaseModel):
    """LLM提示词列表响应"""
    success: bool = True
    data: list[LLMPromptResponse]
    total: int