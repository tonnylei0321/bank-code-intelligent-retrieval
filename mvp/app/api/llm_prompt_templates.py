"""
LLM提示词模板管理API

提供提示词模板的CRUD操作
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.deps import get_current_admin_user, get_db
from app.models.user import User
from app.models.llm_prompt_template import LLMPromptTemplate
from app.core.logging import logger

router = APIRouter(prefix="/api/v1/llm-prompt-templates", tags=["llm-prompt-templates"])


# 默认提示词模板
DEFAULT_TEMPLATES = {
    "exact": """请根据以下银行信息生成一个精确查询的问答对：
银行名称：{bank_name}
联行号：{bank_code}
清算行行号：{clearing_code}

要求：
1. 问题应该是完整的银行名称查询联行号
2. 答案应该直接给出联行号
3. 格式：问题|答案

示例：
中国工商银行北京分行的联行号是什么？|{bank_code}

请生成：""",
    
    "fuzzy": """请根据以下银行信息生成一个模糊查询的问答对：
银行名称：{bank_name}
联行号：{bank_code}
清算行行号：{clearing_code}

要求：
1. 问题应该使用简称或不完整的银行名称
2. 答案应该包含完整的银行名称和联行号
3. 格式：问题|答案

示例：
工行北京分行的联行号|{bank_name}的联行号是{bank_code}

请生成：""",
    
    "reverse": """请根据以下银行信息生成一个反向查询的问答对：
银行名称：{bank_name}
联行号：{bank_code}
清算行行号：{clearing_code}

要求：
1. 问题应该是根据联行号查询银行名称
2. 答案应该给出完整的银行名称
3. 格式：问题|答案

示例：
联行号{bank_code}是哪个银行？|{bank_name}

请生成：""",
    
    "natural": """请根据以下银行信息生成一个自然语言查询的问答对：
银行名称：{bank_name}
联行号：{bank_code}
清算行行号：{clearing_code}

要求：
1. 问题应该是口语化的自然语言表达
2. 答案应该自然地包含银行名称和联行号
3. 格式：问题|答案

示例：
帮我查一下工行北京的联行号|{bank_name}的联行号是{bank_code}

请生成："""
}


@router.get("")
async def list_templates(
    provider: Optional[str] = None,
    prompt_type: Optional[str] = None,
    question_type: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    获取提示词模板列表
    
    Args:
        provider: LLM提供商过滤
        prompt_type: 提示词类型过滤
        question_type: 问题类型过滤
    """
    try:
        query = db.query(LLMPromptTemplate)
        
        if provider:
            query = query.filter(LLMPromptTemplate.provider == provider)
        if prompt_type:
            query = query.filter(LLMPromptTemplate.prompt_type == prompt_type)
        if question_type:
            query = query.filter(LLMPromptTemplate.question_type == question_type)
        
        templates = query.order_by(
            LLMPromptTemplate.provider,
            LLMPromptTemplate.question_type
        ).all()
        
        return [t.to_dict() for t in templates]
    
    except Exception as e:
        logger.error(f"获取提示词模板列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取提示词模板列表失败"
        )


@router.get("/{template_id}")
async def get_template(
    template_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """获取单个提示词模板"""
    try:
        template = db.query(LLMPromptTemplate).filter(
            LLMPromptTemplate.id == template_id
        ).first()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"提示词模板 {template_id} 不存在"
            )
        
        return template.to_dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取提示词模板失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取提示词模板失败"
        )


@router.post("")
async def create_template(
    request: dict,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """创建提示词模板"""
    try:
        template = LLMPromptTemplate(
            provider=request.get("provider"),
            prompt_type=request.get("prompt_type", "sample_generation"),
            question_type=request.get("question_type"),
            template=request.get("template"),
            description=request.get("description"),
            is_default=request.get("is_default", False),
            is_active=request.get("is_active", True)
        )
        
        db.add(template)
        db.commit()
        db.refresh(template)
        
        logger.info(f"用户 {current_user.username} 创建了提示词模板 {template.id}")
        
        return template.to_dict()
    
    except Exception as e:
        db.rollback()
        logger.error(f"创建提示词模板失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建提示词模板失败"
        )


@router.put("/{template_id}")
async def update_template(
    template_id: int,
    request: dict,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """更新提示词模板"""
    try:
        template = db.query(LLMPromptTemplate).filter(
            LLMPromptTemplate.id == template_id
        ).first()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"提示词模板 {template_id} 不存在"
            )
        
        # 更新字段
        if "template" in request:
            template.template = request["template"]
        if "description" in request:
            template.description = request["description"]
        if "is_active" in request:
            template.is_active = request["is_active"]
        
        db.commit()
        db.refresh(template)
        
        logger.info(f"用户 {current_user.username} 更新了提示词模板 {template_id}")
        
        return template.to_dict()
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新提示词模板失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新提示词模板失败"
        )


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """删除提示词模板"""
    try:
        template = db.query(LLMPromptTemplate).filter(
            LLMPromptTemplate.id == template_id
        ).first()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"提示词模板 {template_id} 不存在"
            )
        
        # 不允许删除默认模板
        if template.is_default:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能删除默认模板"
            )
        
        db.delete(template)
        db.commit()
        
        logger.info(f"用户 {current_user.username} 删除了提示词模板 {template_id}")
        
        return {"message": "删除成功"}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除提示词模板失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除提示词模板失败"
        )


@router.post("/init-defaults")
async def init_default_templates(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """初始化默认提示词模板"""
    try:
        providers = ["qwen", "deepseek", "volces"]
        created_count = 0
        
        for provider in providers:
            for question_type, template_text in DEFAULT_TEMPLATES.items():
                # 检查是否已存在
                existing = db.query(LLMPromptTemplate).filter(
                    LLMPromptTemplate.provider == provider,
                    LLMPromptTemplate.prompt_type == "sample_generation",
                    LLMPromptTemplate.question_type == question_type,
                    LLMPromptTemplate.is_default == True
                ).first()
                
                if not existing:
                    template = LLMPromptTemplate(
                        provider=provider,
                        prompt_type="sample_generation",
                        question_type=question_type,
                        template=template_text,
                        description=f"{provider.upper()} - {question_type} 类型的默认提示词",
                        is_default=True,
                        is_active=True
                    )
                    db.add(template)
                    created_count += 1
        
        db.commit()
        
        logger.info(f"初始化了 {created_count} 个默认提示词模板")
        
        return {
            "message": f"成功初始化 {created_count} 个默认提示词模板",
            "created_count": created_count
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"初始化默认提示词模板失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="初始化默认提示词模板失败"
        )


@router.post("/{template_id}/reset")
async def reset_to_default(
    template_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """重置为默认提示词"""
    try:
        template = db.query(LLMPromptTemplate).filter(
            LLMPromptTemplate.id == template_id
        ).first()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"提示词模板 {template_id} 不存在"
            )
        
        # 获取默认模板
        default_template = DEFAULT_TEMPLATES.get(template.question_type)
        if not default_template:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有找到对应的默认模板"
            )
        
        template.template = default_template
        db.commit()
        db.refresh(template)
        
        logger.info(f"用户 {current_user.username} 重置了提示词模板 {template_id}")
        
        return template.to_dict()
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"重置提示词模板失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重置提示词模板失败"
        )
