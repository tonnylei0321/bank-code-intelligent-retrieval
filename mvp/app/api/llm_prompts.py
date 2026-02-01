"""
LLM提示词管理API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.deps import get_current_admin_user, get_db
from app.models.user import User
from app.models.llm_prompt import LLMPrompt
from app.schemas.llm_prompt import (
    LLMPromptCreate, 
    LLMPromptUpdate, 
    LLMPromptResponse, 
    LLMPromptListResponse
)
from app.core.logging import logger

router = APIRouter(prefix="/api/v1/llm-prompts", tags=["llm-prompts"])


# 默认提示词模板
DEFAULT_PROMPTS = {
    "qwen": {
        "display_name": "阿里通义千问",
        "description": "阿里巴巴开发的大语言模型，擅长中文理解和生成",
        "prompt_template": """你是一个银行业务专家。请为以下银行生成{num_samples}种不同的自然语言查询方式。

银行信息：
- 完整名称：{bank_name}
- 联行号：{bank_code}

要求：
1. 生成{num_samples}种用户可能的问法
2. 包括：完整名称、简称、口语化表达、地区+银行名、不完整描述等
3. 模拟真实用户的查询习惯（简短、自然、口语化）
4. 每种问法要自然、简洁，不要太长

请直接返回JSON格式（不要有其他文字）：
{{
    "questions": [
        "问法1",
        "问法2",
        "问法3",
        ...
    ]
}}

示例：
对于"中国工商银行股份有限公司北京市分行"，可能的问法包括：
- "工商银行北京分行"
- "北京工行"
- "ICBC北京"
- "工行北京市分行联行号"
- "北京的工商银行"
等等。"""
    },
    "deepseek": {
        "display_name": "DeepSeek",
        "description": "DeepSeek开发的大语言模型，具有强大的推理能力",
        "prompt_template": """作为银行查询专家，请为指定银行生成多样化的用户查询表达方式。

目标银行：
名称：{bank_name}
联行号：{bank_code}

任务：生成{num_samples}种不同的查询方式

生成规则：
1. 覆盖多种表达习惯：正式名称、简称、地区简化、口语化等
2. 考虑用户实际使用场景：快速查询、模糊记忆、地区偏好等
3. 保持自然流畅，避免过于复杂的表述
4. 长度适中，符合实际查询习惯

输出格式（纯JSON，无其他内容）：
{{
    "questions": [
        "查询方式1",
        "查询方式2",
        "查询方式3",
        ...
    ]
}}

参考示例：
银行"中国建设银行股份有限公司上海市分行"的可能查询：
- "建设银行上海分行"
- "上海建行"
- "CCB上海"
- "建行上海市分行"
- "上海的建设银行"
等。"""
    },
    "chatglm": {
        "display_name": "智谱ChatGLM",
        "description": "智谱AI开发的对话语言模型，适合中文对话场景",
        "prompt_template": """请帮我为银行查询系统生成训练数据。

银行详情：
- 银行全称：{bank_name}
- 银行联行号：{bank_code}

请生成{num_samples}种用户可能的查询表达，要求：

✅ 多样性：包含正式名称、简称、地区+银行、口语化表达
✅ 真实性：模拟用户真实查询习惯，自然简洁
✅ 实用性：涵盖常见查询场景和表达方式
✅ 准确性：确保指向同一家银行

返回格式（仅JSON，无额外说明）：
{{
    "questions": [
        "表达方式1",
        "表达方式2",
        "表达方式3",
        ...
    ]
}}

举例说明：
对于"中国农业银行股份有限公司深圳分行"：
- "农业银行深圳分行" 
- "深圳农行"
- "ABC深圳"
- "农行深圳分行联行号"
- "深圳的农业银行"
等表达方式。"""
    }
}


@router.get("", response_model=LLMPromptListResponse)
async def list_llm_prompts(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    获取所有LLM提示词配置
    """
    try:
        prompts = db.query(LLMPrompt).order_by(LLMPrompt.llm_name).all()
        
        return LLMPromptListResponse(
            success=True,
            data=[LLMPromptResponse.from_orm(prompt) for prompt in prompts],
            total=len(prompts)
        )
    except Exception as e:
        logger.error(f"获取LLM提示词列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取提示词列表失败"
        )


@router.get("/{llm_name}", response_model=LLMPromptResponse)
async def get_llm_prompt(
    llm_name: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    获取指定LLM的提示词配置
    """
    try:
        prompt = db.query(LLMPrompt).filter(LLMPrompt.llm_name == llm_name).first()
        
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"LLM '{llm_name}' 的提示词配置不存在"
            )
        
        return LLMPromptResponse.from_orm(prompt)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取LLM提示词失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取提示词失败"
        )


@router.post("", response_model=LLMPromptResponse, status_code=status.HTTP_201_CREATED)
async def create_llm_prompt(
    prompt_data: LLMPromptCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    创建新的LLM提示词配置
    """
    try:
        # 检查是否已存在
        existing = db.query(LLMPrompt).filter(LLMPrompt.llm_name == prompt_data.llm_name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"LLM '{prompt_data.llm_name}' 的提示词配置已存在"
            )
        
        # 创建新配置
        prompt = LLMPrompt(**prompt_data.dict())
        db.add(prompt)
        db.commit()
        db.refresh(prompt)
        
        logger.info(f"管理员 {current_user.username} 创建了LLM提示词配置: {prompt_data.llm_name}")
        
        return LLMPromptResponse.from_orm(prompt)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建LLM提示词失败: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建提示词失败"
        )


@router.put("/{llm_name}", response_model=LLMPromptResponse)
async def update_llm_prompt(
    llm_name: str,
    prompt_data: LLMPromptUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    更新LLM提示词配置
    """
    try:
        prompt = db.query(LLMPrompt).filter(LLMPrompt.llm_name == llm_name).first()
        
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"LLM '{llm_name}' 的提示词配置不存在"
            )
        
        # 更新字段
        update_data = prompt_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(prompt, field, value)
        
        db.commit()
        db.refresh(prompt)
        
        logger.info(f"管理员 {current_user.username} 更新了LLM提示词配置: {llm_name}")
        
        return LLMPromptResponse.from_orm(prompt)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新LLM提示词失败: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新提示词失败"
        )


@router.delete("/{llm_name}")
async def delete_llm_prompt(
    llm_name: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    删除LLM提示词配置
    """
    try:
        prompt = db.query(LLMPrompt).filter(LLMPrompt.llm_name == llm_name).first()
        
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"LLM '{llm_name}' 的提示词配置不存在"
            )
        
        db.delete(prompt)
        db.commit()
        
        logger.info(f"管理员 {current_user.username} 删除了LLM提示词配置: {llm_name}")
        
        return {"success": True, "message": "提示词配置已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除LLM提示词失败: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除提示词失败"
        )


@router.post("/init-defaults")
async def init_default_prompts(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    初始化默认提示词配置
    """
    try:
        created_count = 0
        
        for llm_name, config in DEFAULT_PROMPTS.items():
            # 检查是否已存在
            existing = db.query(LLMPrompt).filter(LLMPrompt.llm_name == llm_name).first()
            if existing:
                continue
            
            # 创建默认配置
            prompt = LLMPrompt(
                llm_name=llm_name,
                display_name=config["display_name"],
                prompt_template=config["prompt_template"],
                description=config["description"],
                is_active=True
            )
            db.add(prompt)
            created_count += 1
        
        db.commit()
        
        logger.info(f"管理员 {current_user.username} 初始化了 {created_count} 个默认提示词配置")
        
        return {
            "success": True,
            "message": f"成功初始化 {created_count} 个默认提示词配置",
            "created_count": created_count
        }
    except Exception as e:
        logger.error(f"初始化默认提示词失败: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="初始化默认提示词失败"
        )