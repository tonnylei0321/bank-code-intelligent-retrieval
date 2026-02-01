#!/usr/bin/env python3
"""
智能问答系统初始化脚本

用于初始化Redis、小模型和智能问答服务
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import SessionLocal
from app.core.intelligent_qa_config import intelligent_qa_settings
from app.services.redis_service import RedisService
from app.services.small_model_service import SmallModelService, ModelType
from app.services.intelligent_qa_service import IntelligentQAService
from app.services.rag_service import RAGService
from loguru import logger


async def check_dependencies():
    """检查依赖项"""
    logger.info("检查依赖项...")
    
    missing_deps = []
    
    # 检查Redis依赖
    try:
        import aioredis
        logger.info("✓ aioredis 已安装")
    except ImportError:
        missing_deps.append("aioredis")
    
    # 检查模型依赖
    try:
        import openai
        logger.info("✓ openai 已安装")
    except ImportError:
        missing_deps.append("openai")
    
    try:
        import anthropic
        logger.info("✓ anthropic 已安装")
    except ImportError:
        missing_deps.append("anthropic")
    
    try:
        import transformers
        import torch
        logger.info("✓ transformers 和 torch 已安装")
    except ImportError:
        missing_deps.append("transformers torch")
    
    if missing_deps:
        logger.error(f"缺少依赖项: {', '.join(missing_deps)}")
        logger.error("请运行: pip install " + " ".join(missing_deps))
        return False
    
    logger.info("所有依赖项检查通过")
    return True


async def validate_config():
    """验证配置"""
    logger.info("验证配置...")
    
    validation_result = intelligent_qa_settings.validate_config()
    
    if not validation_result["valid"]:
        logger.error("配置验证失败:")
        for error in validation_result["errors"]:
            logger.error(f"  - {error}")
        return False
    
    if validation_result["warnings"]:
        logger.warning("配置警告:")
        for warning in validation_result["warnings"]:
            logger.warning(f"  - {warning}")
    
    logger.info("配置验证通过")
    return True


async def init_redis_service():
    """初始化Redis服务"""
    logger.info("初始化Redis服务...")
    
    db = SessionLocal()
    try:
        redis_config = intelligent_qa_settings.get_redis_config()
        redis_service = RedisService(db, **redis_config)
        
        # 初始化连接
        if not await redis_service.initialize():
            logger.error("Redis服务初始化失败")
            return None
        
        # 测试连接
        await redis_service.redis_client.ping()
        logger.info("✓ Redis连接测试成功")
        
        # 获取统计信息
        stats = await redis_service.get_redis_stats()
        if "error" not in stats:
            logger.info(f"Redis统计: {stats['total_banks']} 条银行记录")
        
        return redis_service
        
    except Exception as e:
        logger.error(f"Redis服务初始化失败: {e}")
        return None
    finally:
        db.close()


async def init_model_service():
    """初始化模型服务"""
    logger.info("初始化模型服务...")
    
    try:
        model_config = intelligent_qa_settings.get_model_config()
        
        model_service = SmallModelService(
            openai_api_key=model_config.get("openai_api_key"),
            anthropic_api_key=model_config.get("anthropic_api_key"),
            config=model_config
        )
        
        # 获取可用模型
        available_models = model_service.get_available_models()
        logger.info(f"可用模型数量: {len(available_models)}")
        
        for model in available_models:
            logger.info(f"  - {model['name']} ({model['provider']}) - {model['status']}")
        
        # 如果有本地模型配置，尝试初始化
        if model_config.get("local_model_name"):
            logger.info("初始化本地模型...")
            success = await model_service.initialize_local_model()
            if success:
                logger.info("✓ 本地模型初始化成功")
            else:
                logger.warning("本地模型初始化失败，将使用API模型")
        
        return model_service
        
    except Exception as e:
        logger.error(f"模型服务初始化失败: {e}")
        return None


async def init_qa_service(redis_service, model_service):
    """初始化智能问答服务"""
    logger.info("初始化智能问答服务...")
    
    db = SessionLocal()
    try:
        # 初始化RAG服务（可选）
        rag_service = None
        try:
            rag_service = RAGService(db)
            logger.info("✓ RAG服务已加载")
        except Exception as e:
            logger.warning(f"RAG服务加载失败: {e}")
        
        # 创建智能问答服务
        qa_config = intelligent_qa_settings.get_qa_config()
        qa_service = IntelligentQAService(
            db=db,
            redis_service=redis_service,
            model_service=model_service,
            rag_service=rag_service,
            config=qa_config
        )
        
        # 初始化服务
        if not await qa_service.initialize():
            logger.error("智能问答服务初始化失败")
            return None
        
        logger.info("✓ 智能问答服务初始化成功")
        return qa_service
        
    except Exception as e:
        logger.error(f"智能问答服务初始化失败: {e}")
        return None
    finally:
        db.close()


async def test_qa_service(qa_service):
    """测试智能问答服务"""
    logger.info("测试智能问答服务...")
    
    test_questions = [
        "工商银行的联行号是多少？",
        "中国银行北京分行",
        "建设银行西单支行联行号"
    ]
    
    for question in test_questions:
        try:
            logger.info(f"测试问题: {question}")
            result = await qa_service.ask_question(question)
            
            logger.info(f"  答案: {result['answer'][:100]}...")
            logger.info(f"  置信度: {result['confidence']:.2f}")
            logger.info(f"  质量: {result['quality']}")
            logger.info(f"  响应时间: {result['response_time']:.2f}s")
            
        except Exception as e:
            logger.error(f"测试问题失败: {e}")


async def load_bank_data_to_redis(redis_service):
    """加载银行数据到Redis"""
    logger.info("检查Redis数据...")
    
    try:
        stats = await redis_service.get_redis_stats()
        
        if stats.get("total_banks", 0) == 0:
            logger.info("Redis中没有银行数据，开始加载...")
            result = await redis_service.load_bank_data_to_redis()
            
            if result["status"] == "success":
                logger.info(f"✓ 成功加载 {result['loaded_count']} 条银行记录到Redis")
            else:
                logger.error(f"加载银行数据失败: {result.get('error', 'Unknown error')}")
                return False
        else:
            logger.info(f"Redis中已有 {stats['total_banks']} 条银行记录")
        
        return True
        
    except Exception as e:
        logger.error(f"加载银行数据失败: {e}")
        return False


async def main():
    """主函数"""
    logger.info("开始初始化智能问答系统...")
    
    # 1. 检查依赖项
    if not await check_dependencies():
        sys.exit(1)
    
    # 2. 验证配置
    if not await validate_config():
        sys.exit(1)
    
    # 3. 初始化Redis服务
    redis_service = await init_redis_service()
    if not redis_service:
        sys.exit(1)
    
    # 4. 加载银行数据到Redis
    if not await load_bank_data_to_redis(redis_service):
        logger.warning("银行数据加载失败，但继续初始化其他服务")
    
    # 5. 初始化模型服务
    model_service = await init_model_service()
    if not model_service:
        sys.exit(1)
    
    # 6. 初始化智能问答服务
    qa_service = await init_qa_service(redis_service, model_service)
    if not qa_service:
        sys.exit(1)
    
    # 7. 测试服务
    await test_qa_service(qa_service)
    
    # 8. 清理资源
    await redis_service.close()
    
    logger.info("智能问答系统初始化完成！")
    logger.info("您现在可以启动Web服务并使用智能问答功能")


if __name__ == "__main__":
    asyncio.run(main())