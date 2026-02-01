"""
智能问答服务 - 整合小模型和Redis的增强问答系统

本服务实现了完整的智能问答流程：
1. 使用小模型进行问题分析和意图识别
2. 基于Redis进行快速数据检索
3. 结合上下文生成准确答案
4. 保存问答历史和用户偏好

主要功能：
    - 智能问题理解和分类
    - 多策略数据检索（Redis + RAG）
    - 上下文感知的答案生成
    - 问答历史管理
    - 用户偏好学习

技术架构：
    - 问题分析：小模型（GPT/Claude/本地模型）
    - 数据检索：Redis缓存 + 向量数据库
    - 答案生成：小模型 + 模板
    - 历史存储：数据库 + Redis缓存

使用示例：
    >>> qa_service = IntelligentQAService(db, redis_service, model_service)
    >>> await qa_service.initialize()
    >>> 
    >>> # 智能问答
    >>> result = await qa_service.ask_question("工商银行西单支行联行号", user_id=1)
    >>> 
    >>> # 获取历史记录
    >>> history = await qa_service.get_user_history(user_id=1)
"""

import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy.orm import Session
from loguru import logger

from app.services.redis_service import RedisService
from app.services.small_model_service import SmallModelService, ModelType, QuestionType
from app.services.rag_service import RAGService
from app.models.qa_pair import QAPair
from app.models.user import User


class RetrievalStrategy(Enum):
    """检索策略"""
    REDIS_ONLY = "redis_only"           # 仅使用Redis
    RAG_ONLY = "rag_only"              # 仅使用RAG
    HYBRID = "hybrid"                   # 混合检索
    INTELLIGENT = "intelligent"        # 智能选择


class AnswerQuality(Enum):
    """答案质量评级"""
    EXCELLENT = "excellent"    # 优秀
    GOOD = "good"             # 良好  
    FAIR = "fair"             # 一般
    POOR = "poor"             # 较差


class IntelligentQAService:
    """
    智能问答服务 - 整合多种技术的问答系统
    
    本类实现了完整的智能问答流程，包括：
    1. 问题理解和意图识别
    2. 多策略数据检索
    3. 上下文感知答案生成
    4. 问答历史管理
    5. 用户偏好学习
    
    属性：
        db: 数据库会话
        redis_service: Redis服务
        model_service: 小模型服务
        rag_service: RAG服务
        config: 服务配置
    """
    
    def __init__(
        self,
        db: Session,
        redis_service: RedisService,
        model_service: SmallModelService,
        rag_service: Optional[RAGService] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化智能问答服务
        
        Args:
            db: 数据库会话
            redis_service: Redis服务实例
            model_service: 小模型服务实例
            rag_service: RAG服务实例（可选）
            config: 服务配置
        """
        self.db = db
        self.redis_service = redis_service
        self.model_service = model_service
        self.rag_service = rag_service
        
        # 默认配置
        self.config = {
            "default_retrieval_strategy": RetrievalStrategy.INTELLIGENT,
            "max_context_results": 5,
            "redis_search_limit": 10,
            "rag_search_limit": 5,
            "answer_confidence_threshold": 0.7,
            "enable_history": True,
            "history_limit": 100,
            "enable_learning": True,
            "cache_answers": True,
            "cache_ttl": 3600,
            "fallback_to_rag": True,
            "quality_threshold": 0.8
        }
        
        if config:
            self.config.update(config)
        
        # 统计信息
        self.stats = {
            "total_questions": 0,
            "successful_answers": 0,
            "failed_answers": 0,
            "redis_retrievals": 0,
            "rag_retrievals": 0,
            "hybrid_retrievals": 0,
            "average_response_time": 0.0,
            "quality_distribution": {
                "excellent": 0,
                "good": 0,
                "fair": 0,
                "poor": 0
            }
        }
    
    async def initialize(self) -> bool:
        """
        初始化智能问答服务
        
        Returns:
            是否成功初始化
        """
        try:
            logger.info("Initializing Intelligent QA Service...")
            
            # 初始化Redis服务
            if not await self.redis_service.initialize():
                logger.error("Failed to initialize Redis service")
                return False
            
            # 测试Redis连接
            await self.redis_service.redis_client.ping()
            
            # 检查模型服务
            available_models = self.model_service.get_available_models()
            if not available_models:
                logger.warning("No models available in model service")
            
            logger.info(f"Intelligent QA Service initialized with {len(available_models)} available models")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Intelligent QA Service: {e}")
            return False
    
    async def ask_question(
        self,
        question: str,
        user_id: Optional[int] = None,
        retrieval_strategy: Optional[RetrievalStrategy] = None,
        model_type: Optional[ModelType] = None
    ) -> Dict[str, Any]:
        """
        智能问答主入口
        
        Args:
            question: 用户问题
            user_id: 用户ID（可选）
            retrieval_strategy: 检索策略（可选）
            model_type: 模型类型（可选）
        
        Returns:
            问答结果字典
        """
        try:
            start_time = datetime.now()
            logger.info(f"Processing question: {question[:50]}...")
            
            # 设置模型（如果指定）
            if model_type and model_type != self.model_service.current_model:
                self.model_service.set_model(model_type)
            
            # 第一步：问题分析
            logger.info("Step 1: Analyzing question...")
            analysis = await self.model_service.analyze_question(question)
            
            # 第二步：选择检索策略
            strategy = retrieval_strategy or self._choose_retrieval_strategy(analysis)
            logger.info(f"Step 2: Using retrieval strategy: {strategy.value}")
            
            # 第三步：数据检索
            logger.info("Step 3: Retrieving relevant data...")
            context = await self._retrieve_context(question, analysis, strategy)
            
            # 第四步：答案生成
            logger.info("Step 4: Generating answer...")
            answer_result = await self.model_service.generate_answer(question, context, analysis)
            
            # 第五步：质量评估
            quality = self._assess_answer_quality(answer_result, context)
            
            # 第六步：保存历史记录
            if self.config["enable_history"] and user_id:
                await self._save_qa_history(user_id, question, answer_result, analysis, quality)
            
            # 构建最终结果
            result = {
                "question": question,
                "answer": answer_result["answer"],
                "confidence": answer_result.get("confidence", 0.0),
                "matched_banks": answer_result.get("matched_banks", []),
                "suggestions": answer_result.get("suggestions", []),
                "analysis": analysis,
                "retrieval_strategy": strategy.value,
                "context_count": len(context),
                "quality": quality.value,
                "model_used": answer_result.get("model_used"),
                "response_time": (datetime.now() - start_time).total_seconds(),
                "timestamp": datetime.now().isoformat()
            }
            
            # 更新统计信息
            self._update_stats(start_time, True, strategy, quality)
            
            logger.info(f"Question processed successfully in {result['response_time']:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process question: {e}")
            self._update_stats(start_time, False, strategy, AnswerQuality.POOR)
            
            return {
                "question": question,
                "answer": "抱歉，处理您的问题时出现了错误。请稍后重试或联系技术支持。",
                "confidence": 0.0,
                "matched_banks": [],
                "suggestions": ["请检查问题格式", "尝试使用更具体的描述"],
                "analysis": None,
                "retrieval_strategy": "error",
                "context_count": 0,
                "quality": AnswerQuality.POOR.value,
                "model_used": "error",
                "response_time": (datetime.now() - start_time).total_seconds(),
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def _choose_retrieval_strategy(self, analysis: Dict[str, Any]) -> RetrievalStrategy:
        """
        根据问题分析选择最佳检索策略
        
        Args:
            analysis: 问题分析结果
        
        Returns:
            选择的检索策略
        """
        question_type = analysis.get("question_type", "general_query")
        confidence = analysis.get("confidence", 0.0)
        
        # 高置信度的精确查询优先使用Redis
        if confidence > 0.8 and question_type in ["bank_code_query", "bank_name_query"]:
            return RetrievalStrategy.REDIS_ONLY
        
        # 支行查询使用混合检索
        elif question_type == "branch_query":
            return RetrievalStrategy.HYBRID
        
        # 不明确查询使用RAG
        elif question_type == "unclear_query" or confidence < 0.5:
            return RetrievalStrategy.RAG_ONLY
        
        # 默认使用智能策略
        else:
            return RetrievalStrategy.INTELLIGENT
    
    async def _retrieve_context(
        self,
        question: str,
        analysis: Dict[str, Any],
        strategy: RetrievalStrategy
    ) -> List[Dict[str, Any]]:
        """
        根据策略检索上下文信息
        
        Args:
            question: 用户问题
            analysis: 问题分析结果
            strategy: 检索策略
        
        Returns:
            检索到的上下文信息列表
        """
        context = []
        
        try:
            if strategy == RetrievalStrategy.REDIS_ONLY:
                context = await self._redis_retrieve(question, analysis)
                self.stats["redis_retrievals"] += 1
            
            elif strategy == RetrievalStrategy.RAG_ONLY:
                context = await self._rag_retrieve(question, analysis)
                self.stats["rag_retrievals"] += 1
            
            elif strategy == RetrievalStrategy.HYBRID:
                redis_results = await self._redis_retrieve(question, analysis)
                rag_results = await self._rag_retrieve(question, analysis)
                context = self._merge_results(redis_results, rag_results)
                self.stats["hybrid_retrievals"] += 1
            
            elif strategy == RetrievalStrategy.INTELLIGENT:
                # 智能策略：先尝试Redis，如果结果不足则补充RAG
                context = await self._redis_retrieve(question, analysis)
                
                if len(context) < self.config["max_context_results"] and self.rag_service:
                    rag_results = await self._rag_retrieve(question, analysis)
                    context = self._merge_results(context, rag_results)
                
                self.stats["hybrid_retrievals"] += 1
            
            logger.info(f"Retrieved {len(context)} context items using {strategy.value}")
            return context[:self.config["max_context_results"]]
            
        except Exception as e:
            logger.error(f"Context retrieval failed: {e}")
            return []
    
    async def _redis_retrieve(
        self,
        question: str,
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """使用Redis检索"""
        try:
            # 根据分析结果选择搜索类型
            question_type = analysis.get("question_type", "general_query")
            
            if question_type == "bank_code_query" and analysis.get("bank_code"):
                # 精确联行号查询
                result = await self.redis_service.get_bank_by_code(analysis["bank_code"])
                return [result] if result else []
            
            elif analysis.get("bank_name"):
                # 银行名称查询
                return await self.redis_service.search_banks(
                    analysis["bank_name"],
                    search_type="name",
                    limit=self.config["redis_search_limit"]
                )
            
            else:
                # 通用关键词查询
                keywords = analysis.get("keywords", [])
                if keywords:
                    return await self.redis_service.search_banks(
                        keywords[0],
                        search_type="keyword",
                        limit=self.config["redis_search_limit"]
                    )
                else:
                    return await self.redis_service.search_banks(
                        question,
                        search_type="auto",
                        limit=self.config["redis_search_limit"]
                    )
            
        except Exception as e:
            logger.error(f"Redis retrieval failed: {e}")
            return []
    
    async def _rag_retrieve(
        self,
        question: str,
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """使用RAG检索"""
        try:
            if not self.rag_service:
                logger.warning("RAG service not available")
                return []
            
            results = await self.rag_service.retrieve_relevant_banks(
                question,
                top_k=self.config["rag_search_limit"]
            )
            
            # 转换RAG结果格式以匹配Redis结果
            converted_results = []
            for result in results:
                converted_results.append({
                    "bank_name": result.get("bank_name"),
                    "bank_code": result.get("bank_code"),
                    "clearing_code": result.get("clearing_code", ""),
                    "match_score": result.get("final_score", 0.0),
                    "search_type": "rag",
                    "similarity_score": result.get("similarity_score", 0.0)
                })
            
            return converted_results
            
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            return []
    
    def _merge_results(
        self,
        redis_results: List[Dict[str, Any]],
        rag_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        合并Redis和RAG检索结果
        
        Args:
            redis_results: Redis检索结果
            rag_results: RAG检索结果
        
        Returns:
            合并后的结果列表
        """
        merged = []
        seen_codes = set()
        
        # 优先添加Redis结果（通常更准确）
        for result in redis_results:
            bank_code = result.get("bank_code")
            if bank_code and bank_code not in seen_codes:
                result["source"] = "redis"
                merged.append(result)
                seen_codes.add(bank_code)
        
        # 添加RAG结果（去重）
        for result in rag_results:
            bank_code = result.get("bank_code")
            if bank_code and bank_code not in seen_codes:
                result["source"] = "rag"
                merged.append(result)
                seen_codes.add(bank_code)
        
        # 按匹配分数排序
        merged.sort(key=lambda x: x.get("match_score", 0.0), reverse=True)
        
        return merged
    
    def _assess_answer_quality(
        self,
        answer_result: Dict[str, Any],
        context: List[Dict[str, Any]]
    ) -> AnswerQuality:
        """
        评估答案质量
        
        Args:
            answer_result: 答案结果
            context: 检索上下文
        
        Returns:
            答案质量等级
        """
        confidence = answer_result.get("confidence", 0.0)
        matched_banks = answer_result.get("matched_banks", [])
        
        # 基于置信度和匹配结果评估质量
        if confidence >= 0.9 and len(matched_banks) > 0:
            return AnswerQuality.EXCELLENT
        elif confidence >= 0.7 and len(matched_banks) > 0:
            return AnswerQuality.GOOD
        elif confidence >= 0.5 or len(context) > 0:
            return AnswerQuality.FAIR
        else:
            return AnswerQuality.POOR
    
    async def _save_qa_history(
        self,
        user_id: int,
        question: str,
        answer_result: Dict[str, Any],
        analysis: Dict[str, Any],
        quality: AnswerQuality
    ):
        """保存问答历史记录"""
        try:
            from app.models.user_qa_history import UserQAHistory
            
            qa_record = UserQAHistory(
                user_id=user_id,
                question=question,
                answer=answer_result["answer"],
                retrieval_strategy=analysis.get("retrieval_method", "unknown"),
                model_type=answer_result.get("model_used", "unknown"),
                confidence_score=answer_result.get("confidence", 0.0),
                response_time=int(answer_result.get("response_time", 0) * 1000),  # 转换为毫秒
                context_count=len(answer_result.get("matched_banks", []))
            )
            
            self.db.add(qa_record)
            self.db.commit()
            
            logger.info(f"Saved QA history for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to save QA history: {e}")
            self.db.rollback()
    
    async def get_user_history(
        self,
        user_id: int,
        limit: int = 20,
        question_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取用户问答历史
        
        Args:
            user_id: 用户ID
            limit: 返回记录数量限制
            question_type: 问题类型过滤（可选）
        
        Returns:
            历史记录列表
        """
        try:
            from app.models.user_qa_history import UserQAHistory
            
            query = self.db.query(UserQAHistory).filter(UserQAHistory.user_id == user_id)
            
            records = query.order_by(UserQAHistory.created_at.desc()).limit(limit).all()
            
            history = []
            for record in records:
                history.append({
                    "id": record.id,
                    "question": record.question,
                    "answer": record.answer,
                    "confidence_score": record.confidence_score,
                    "retrieval_strategy": record.retrieval_strategy,
                    "model_type": record.model_type,
                    "response_time": record.response_time,
                    "context_count": record.context_count,
                    "created_at": record.created_at.isoformat() if record.created_at else None
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get user history: {e}")
            return []
    
    async def get_popular_questions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取热门问题"""
        try:
            # 这里可以实现基于问题频率的统计
            # 简化版本：返回最近的问题
            recent_questions = self.db.query(QAPair)\
                .order_by(QAPair.created_at.desc())\
                .limit(limit * 2)\
                .all()
            
            # 统计问题频率
            question_counts = {}
            for qa in recent_questions:
                question = qa.question.lower().strip()
                question_counts[question] = question_counts.get(question, 0) + 1
            
            # 排序并返回
            popular = sorted(question_counts.items(), key=lambda x: x[1], reverse=True)
            
            return [
                {"question": q, "count": c} 
                for q, c in popular[:limit]
            ]
            
        except Exception as e:
            logger.error(f"Failed to get popular questions: {e}")
            return []
    
    def _update_stats(
        self,
        start_time: datetime,
        success: bool,
        strategy: RetrievalStrategy,
        quality: AnswerQuality
    ):
        """更新统计信息"""
        self.stats["total_questions"] += 1
        
        if success:
            self.stats["successful_answers"] += 1
        else:
            self.stats["failed_answers"] += 1
        
        # 更新质量分布
        self.stats["quality_distribution"][quality.value] += 1
        
        # 更新平均响应时间
        response_time = (datetime.now() - start_time).total_seconds()
        if self.stats["total_questions"] == 1:
            self.stats["average_response_time"] = response_time
        else:
            self.stats["average_response_time"] = (
                self.stats["average_response_time"] * (self.stats["total_questions"] - 1) + response_time
            ) / self.stats["total_questions"]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        return {
            **self.stats,
            "config": self.config,
            "redis_service_stats": self.redis_service.stats if hasattr(self.redis_service, 'stats') else {},
            "model_service_stats": self.model_service.get_stats()
        }