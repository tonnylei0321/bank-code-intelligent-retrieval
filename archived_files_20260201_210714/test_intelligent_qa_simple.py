#!/usr/bin/env python3
"""
智能问答系统简单测试脚本

用于快速测试Redis和小模型功能
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.database import SessionLocal
from app.services.redis_service import RedisService
from app.services.small_model_service import SmallModelService, ModelType
from loguru import logger


async def test_redis_service():
    """测试Redis服务"""
    logger.info("测试Redis服务...")
    
    db = SessionLocal()
    try:
        # 创建Redis服务
        redis_service = RedisService(db)
        
        # 初始化连接
        if not await redis_service.initialize():
            logger.error("Redis初始化失败")
            return False
        
        # 测试连接
        await redis_service.redis_client.ping()
        logger.info("✓ Redis连接成功")
        
        # 获取统计信息
        stats = await redis_service.get_redis_stats()
        logger.info(f"Redis统计: {stats}")
        
        # 测试搜索（如果有数据）
        if stats.get("total_banks", 0) > 0:
            results = await redis_service.search_banks("工商银行", "keyword", 3)
            logger.info(f"搜索结果: {len(results)} 条")
            for result in results[:2]:
                logger.info(f"  - {result.get('bank_name', 'N/A')}")
        
        await redis_service.close()
        return True
        
    except Exception as e:
        logger.error(f"Redis测试失败: {e}")
        return False
    finally:
        db.close()


async def test_model_service():
    """测试模型服务"""
    logger.info("测试模型服务...")
    
    try:
        # 创建模型服务（不需要API密钥进行基本测试）
        model_service = SmallModelService()
        
        # 获取可用模型
        models = model_service.get_available_models()
        logger.info(f"可用模型: {len(models)} 个")
        
        for model in models:
            logger.info(f"  - {model['name']} ({model['provider']}) - {model['status']}")
        
        # 测试问题分析（使用备用方法）
        test_question = "工商银行西单支行联行号"
        analysis = await model_service.analyze_question(test_question)
        
        logger.info(f"问题分析结果:")
        logger.info(f"  - 问题类型: {analysis.get('question_type', 'N/A')}")
        logger.info(f"  - 意图: {analysis.get('intent', 'N/A')}")
        logger.info(f"  - 置信度: {analysis.get('confidence', 0)}")
        logger.info(f"  - 关键词: {analysis.get('keywords', [])}")
        
        return True
        
    except Exception as e:
        logger.error(f"模型服务测试失败: {e}")
        return False


async def test_integration():
    """集成测试"""
    logger.info("进行集成测试...")
    
    db = SessionLocal()
    try:
        # 初始化服务
        redis_service = RedisService(db)
        model_service = SmallModelService()
        
        if not await redis_service.initialize():
            logger.error("Redis初始化失败")
            return False
        
        # 测试问题分析 + Redis搜索
        test_question = "中国工商银行"
        
        # 1. 分析问题
        analysis = await model_service.analyze_question(test_question)
        logger.info(f"问题分析: {analysis.get('question_type', 'N/A')}")
        
        # 2. 基于分析结果搜索
        search_query = analysis.get('bank_name') or analysis.get('keywords', [test_question])[0]
        results = await redis_service.search_banks(search_query, "auto", 3)
        
        logger.info(f"搜索到 {len(results)} 条结果:")
        for result in results:
            logger.info(f"  - {result.get('bank_name', 'N/A')} ({result.get('bank_code', 'N/A')})")
        
        await redis_service.close()
        return True
        
    except Exception as e:
        logger.error(f"集成测试失败: {e}")
        return False
    finally:
        db.close()


async def main():
    """主函数"""
    logger.info("开始智能问答系统简单测试...")
    
    success_count = 0
    total_tests = 3
    
    # 测试Redis服务
    if await test_redis_service():
        success_count += 1
        logger.info("✓ Redis服务测试通过")
    else:
        logger.error("✗ Redis服务测试失败")
    
    print("-" * 50)
    
    # 测试模型服务
    if await test_model_service():
        success_count += 1
        logger.info("✓ 模型服务测试通过")
    else:
        logger.error("✗ 模型服务测试失败")
    
    print("-" * 50)
    
    # 集成测试
    if await test_integration():
        success_count += 1
        logger.info("✓ 集成测试通过")
    else:
        logger.error("✗ 集成测试失败")
    
    print("=" * 50)
    logger.info(f"测试完成: {success_count}/{total_tests} 通过")
    
    if success_count == total_tests:
        logger.info("🎉 所有测试通过！智能问答系统基本功能正常")
    else:
        logger.warning(f"⚠️  有 {total_tests - success_count} 个测试失败，请检查配置")


if __name__ == "__main__":
    asyncio.run(main())