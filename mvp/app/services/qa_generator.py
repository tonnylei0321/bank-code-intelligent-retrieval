"""
QA Generator Service - 问答对生成服务

本服务负责从银行代码记录生成训练用的问答对数据，使用大模型API生成多种类型的问题。

主要功能：
    - 生成4种类型的问题：精确匹配、模糊匹配、反向查询、自然语言
    - 批量生成问答对并跟踪进度
    - 数据集划分（训练集/验证集/测试集）
    - 错误跟踪和日志记录
    - 生成统计信息查询

使用示例：
    >>> from app.services.qa_generator import QAGenerator
    >>> generator = QAGenerator(db_session)
    >>> 
    >>> # 为数据集生成问答对
    >>> results = generator.generate_for_dataset(
    ...     dataset_id=1,
    ...     question_types=["exact", "fuzzy", "reverse", "natural"]
    ... )
    >>> 
    >>> # 划分数据集
    >>> split_results = generator.split_dataset(
    ...     dataset_id=1,
    ...     train_ratio=0.8,
    ...     val_ratio=0.1,
    ...     test_ratio=0.1
    ... )
    >>> 
    >>> # 查看生成统计
    >>> stats = generator.get_generation_stats(dataset_id=1)

技术细节：
    - 使用TeacherModelAPI调用大模型生成问题
    - 支持进度回调函数实时跟踪生成进度
    - 按问题类型分组确保数据集划分的均匀分布
    - 使用随机种子保证数据划分的可重现性
"""
import random
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from loguru import logger

from app.models.bank_code import BankCode
from app.models.qa_pair import QAPair
from app.models.dataset import Dataset
from app.services.teacher_model import TeacherModelAPI


class QAGenerationError(Exception):
    """
    问答对生成异常基类
    
    用于标识问答对生成过程中的所有错误，包括：
    - 数据集不存在或无效
    - 没有可用的银行代码记录
    - 数据集划分比例错误
    - 数据库操作失败
    """
    pass


class QAGenerator:
    """
    问答对生成器服务 - 用于创建模型训练数据
    
    本类负责从银行代码数据生成高质量的问答对，支持多种问题类型和数据集管理功能。
    
    核心功能：
        1. 问题生成：支持4种问题类型
           - exact: 精确匹配问题（如：工商银行的代码是什么？）
           - fuzzy: 模糊匹配问题（如：工行的代码是多少？）
           - reverse: 反向查询问题（如：102100099996是哪个银行？）
           - natural: 自然语言问题（如：我想查询工商银行的联行号）
        
        2. 批量生成：支持大规模数据生成
           - 自动遍历数据集中的所有有效记录
           - 为每条记录生成指定类型的问题
           - 实时跟踪生成进度
           - 记录失败的记录和原因
        
        3. 数据集划分：智能划分训练/验证/测试集
           - 按问题类型分组确保均匀分布
           - 支持自定义划分比例
           - 使用随机种子保证可重现性
        
        4. 统计分析：提供详细的生成统计信息
           - 按问题类型统计
           - 按数据集划分统计
           - 生成成功率和失败原因
    
    属性：
        db (Session): 数据库会话对象
        teacher_api (TeacherModelAPI): 大模型API客户端，用于生成问题
    
    使用流程：
        1. 创建QAGenerator实例
        2. 调用generate_for_dataset()生成问答对
        3. 调用split_dataset()划分数据集
        4. 调用get_generation_stats()查看统计信息
    """
    
    def __init__(
        self,
        db: Session,
        teacher_api: Optional[TeacherModelAPI] = None
    ):
        """
        初始化问答对生成器
        
        Args:
            db (Session): SQLAlchemy数据库会话对象，用于访问数据库
            teacher_api (Optional[TeacherModelAPI]): 大模型API客户端
                如果为None，将创建默认的TeacherModelAPI实例
        
        说明：
            - 数据库会话用于读取银行代码记录和保存生成的问答对
            - 大模型API用于调用AI模型生成问题文本
            - 初始化时会记录日志便于追踪
        """
        self.db = db
        self.teacher_api = teacher_api or TeacherModelAPI()
        
        logger.info("QAGenerator initialized")
    
    def generate_for_dataset(
        self,
        dataset_id: int,
        question_types: Optional[List[str]] = None,
        progress_callback: Optional[callable] = None,
        max_records: Optional[int] = None,  # 新增：限制处理的记录数
        batch_size: int = 100  # 新增：批量提交大小
    ) -> Dict[str, Any]:
        """
        为数据集中的所有记录生成问答对
        
        本方法会遍历指定数据集中的所有有效银行代码记录，为每条记录生成指定类型的问题。
        生成过程支持进度跟踪和错误记录。
        
        Args:
            dataset_id (int): 数据集ID，必须是已存在的有效数据集
            question_types (Optional[List[str]]): 要生成的问题类型列表
                可选值：["exact", "fuzzy", "reverse", "natural"]
                默认为None，表示生成所有4种类型
            progress_callback (Optional[callable]): 进度回调函数
                函数签名：callback(current: int, total: int, record_id: int)
                - current: 当前处理的记录索引（从1开始）
                - total: 总记录数
                - record_id: 当前记录的ID
        
        Returns:
            Dict[str, Any]: 生成结果字典，包含以下字段：
                - dataset_id: 数据集ID
                - total_records: 处理的记录总数
                - question_types: 生成的问题类型列表
                - total_attempts: 总尝试次数
                - successful: 成功生成的问答对数量
                - failed: 失败的生成次数
                - qa_pairs_created: 实际创建的问答对数量
                - failed_records: 失败记录列表，每项包含record_id、bank_name和failures
                - start_time: 开始时间（ISO格式）
                - end_time: 结束时间（ISO格式）
        
        Raises:
            QAGenerationError: 在以下情况抛出异常：
                - 数据集不存在
                - 数据集中没有有效的银行代码记录
                - 数据库提交失败
        
        处理流程：
            1. 验证数据集是否存在
            2. 加载所有有效的银行代码记录（is_valid=1）
            3. 对每条记录生成指定类型的问题
            4. 将生成的问答对保存到数据库
            5. 记录失败的记录和原因
            6. 返回详细的统计信息
        
        注意事项：
            - 生成的问答对初始split_type为"train"，需要后续调用split_dataset()重新划分
            - 失败的生成不会中断整个流程，会继续处理其他记录
            - 所有问答对在方法结束时统一提交到数据库
        """
        # 验证数据集是否存在
        dataset = self.db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise QAGenerationError(f"Dataset {dataset_id} not found")
        
        # 获取所有有效的银行代码记录（is_valid=1表示数据有效）
        query = self.db.query(BankCode).filter(
            BankCode.dataset_id == dataset_id,
            BankCode.is_valid == 1
        )
        
        # 如果指定了max_records，限制记录数量
        if max_records:
            query = query.limit(max_records)
            logger.info(f"限制处理记录数: {max_records}")
        
        bank_records = query.all()
        
        if not bank_records:
            raise QAGenerationError(f"No valid bank code records found in dataset {dataset_id}")
        
        # 设置默认问题类型（如果未指定则生成所有4种类型）
        if question_types is None:
            question_types = ["exact", "fuzzy", "reverse", "natural"]
        
        logger.info(
            f"Starting QA generation for dataset {dataset_id} - "
            f"Records: {len(bank_records)}, Types: {question_types}"
        )
        
        # 初始化结果字典，用于跟踪生成过程的统计信息
        results = {
            "dataset_id": dataset_id,
            "total_records": len(bank_records),
            "question_types": question_types,
            "total_attempts": 0,  # 总尝试次数
            "successful": 0,  # 成功次数
            "failed": 0,  # 失败次数
            "qa_pairs_created": 0,  # 实际创建的问答对数量
            "failed_records": [],  # 失败记录列表
            "start_time": datetime.utcnow().isoformat(),
            "end_time": None
        }
        
        start_time = datetime.utcnow()
        
        # 批量提交计数器
        batch_counter = 0
        
        # 遍历每条银行代码记录，生成问答对
        for idx, record in enumerate(bank_records, 1):
            # 调用进度回调函数（如果提供）
            if progress_callback:
                progress_callback(idx, len(bank_records), record.id)
            
            record_failures = []  # 记录当前记录的失败情况
            
            # 为当前记录生成每种类型的问题
            for question_type in question_types:
                results["total_attempts"] += 1
                
                try:
                    # 使用大模型API生成问答对
                    qa_result = self.teacher_api.generate_qa_pair(record, question_type)
                    
                    if qa_result:
                        question, answer = qa_result
                        
                        # 创建问答对记录（split_type稍后在split_dataset中分配）
                        qa_pair = QAPair(
                            dataset_id=dataset_id,
                            source_record_id=record.id,
                            question=question,
                            answer=answer,
                            question_type=question_type,
                            split_type="train",  # 默认为训练集，后续会重新划分
                            generated_at=datetime.utcnow()
                        )
                        
                        self.db.add(qa_pair)
                        results["successful"] += 1
                        batch_counter += 1
                        
                        # 批量提交：每batch_size条记录提交一次
                        if batch_counter >= batch_size:
                            try:
                                self.db.commit()
                                logger.info(f"批量提交 {batch_counter} 条问答对到数据库")
                                batch_counter = 0
                            except Exception as commit_error:
                                self.db.rollback()
                                logger.error(f"批量提交失败: {commit_error}")
                                raise QAGenerationError(f"Database commit failed: {commit_error}")
                        
                        logger.debug(
                            f"QA pair created - Record: {record.id}, Type: {question_type}"
                        )
                    else:
                        # 大模型生成失败
                        results["failed"] += 1
                        record_failures.append({
                            "question_type": question_type,
                            "reason": "Teacher model generation failed"
                        })
                        
                        logger.warning(
                            f"QA pair generation failed - Record: {record.id}, Type: {question_type}"
                        )
                
                except Exception as e:
                    # 捕获异常并记录
                    results["failed"] += 1
                    record_failures.append({
                        "question_type": question_type,
                        "reason": str(e)
                    })
                    
                    logger.error(
                        f"Error generating QA pair - Record: {record.id}, "
                        f"Type: {question_type}: {e}"
                    )
            
            # 如果当前记录有失败的生成，记录到失败列表
            if record_failures:
                results["failed_records"].append({
                    "record_id": record.id,
                    "bank_name": record.bank_name,
                    "failures": record_failures
                })
        
        # 提交剩余的问答对到数据库
        try:
            if batch_counter > 0:
                self.db.commit()
                logger.info(f"最终提交 {batch_counter} 条问答对到数据库")
            
            # 统计实际创建的问答对数量
            qa_count = self.db.query(QAPair).filter(
                QAPair.dataset_id == dataset_id
            ).count()
            results["qa_pairs_created"] = qa_count
            
            logger.info(f"QA pairs committed to database - Count: {qa_count}")
        
        except Exception as e:
            # 提交失败时回滚事务
            self.db.rollback()
            logger.error(f"Failed to commit QA pairs: {e}")
            raise QAGenerationError(f"Database commit failed: {e}")
        
        # 计算总耗时
        end_time = datetime.utcnow()
        results["end_time"] = end_time.isoformat()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(
            f"QA generation completed for dataset {dataset_id} - "
            f"Total: {results['total_attempts']}, "
            f"Successful: {results['successful']}, "
            f"Failed: {results['failed']}, "
            f"Duration: {duration:.2f}s"
        )
        
        return results
    
    def split_dataset(
        self,
        dataset_id: int,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        random_seed: Optional[int] = 42
    ) -> Dict[str, Any]:
        """
        将问答对划分为训练集/验证集/测试集
        
        本方法按照指定比例将数据集中的问答对划分为三个子集，用于模型训练、验证和测试。
        划分过程按问题类型分组进行，确保每种类型的问题在各个子集中均匀分布。
        
        Args:
            dataset_id (int): 数据集ID
            train_ratio (float): 训练集比例，默认0.8（80%）
            val_ratio (float): 验证集比例，默认0.1（10%）
            test_ratio (float): 测试集比例，默认0.1（10%）
            random_seed (Optional[int]): 随机种子，用于保证划分的可重现性
                默认为42，设置为None则使用随机划分
        
        Returns:
            Dict[str, Any]: 划分结果字典，包含以下字段：
                - dataset_id: 数据集ID
                - total_qa_pairs: 总问答对数量
                - train_count: 训练集数量
                - val_count: 验证集数量
                - test_count: 测试集数量
                - train_ratio: 实际训练集比例
                - val_ratio: 实际验证集比例
                - test_ratio: 实际测试集比例
                - question_types: 问题类型列表
                - random_seed: 使用的随机种子
        
        Raises:
            QAGenerationError: 在以下情况抛出异常：
                - 三个比例之和不等于1.0
                - 数据集中没有问答对
                - 数据库提交失败
        
        划分策略：
            1. 按问题类型分组：确保每种类型的问题均匀分布
            2. 随机打乱：使用随机种子打乱每组问题
            3. 按比例划分：根据指定比例切分每组问题
            4. 更新数据库：将split_type字段更新为train/val/test
        
        注意事项：
            - 实际比例可能与指定比例略有偏差（由于整数除法）
            - 使用相同的随机种子可以重现相同的划分结果
            - 划分会覆盖之前的split_type设置
        """
        # 验证比例之和是否为1.0（允许0.001的误差）
        total_ratio = train_ratio + val_ratio + test_ratio
        if abs(total_ratio - 1.0) > 0.001:
            raise QAGenerationError(
                f"Split ratios must sum to 1.0, got {total_ratio}"
            )
        
        # 获取数据集中的所有问答对
        qa_pairs = self.db.query(QAPair).filter(
            QAPair.dataset_id == dataset_id
        ).all()
        
        if not qa_pairs:
            raise QAGenerationError(f"No QA pairs found for dataset {dataset_id}")
        
        logger.info(
            f"Splitting dataset {dataset_id} - "
            f"Total QA pairs: {len(qa_pairs)}, "
            f"Ratios: train={train_ratio}, val={val_ratio}, test={test_ratio}"
        )
        
        # 按问题类型分组，确保每种类型的问题在各个子集中均匀分布
        qa_by_type = {}
        for qa in qa_pairs:
            if qa.question_type not in qa_by_type:
                qa_by_type[qa.question_type] = []
            qa_by_type[qa.question_type].append(qa)
        
        # 设置随机种子以保证可重现性
        if random_seed is not None:
            random.seed(random_seed)
        
        # 分别划分每种问题类型
        train_count = 0
        val_count = 0
        test_count = 0
        
        for question_type, type_qa_pairs in qa_by_type.items():
            # 随机打乱问答对顺序
            random.shuffle(type_qa_pairs)
            
            # 计算划分索引位置
            total = len(type_qa_pairs)
            train_end = int(total * train_ratio)
            val_end = train_end + int(total * val_ratio)
            
            # 分配split_type标签
            for i, qa in enumerate(type_qa_pairs):
                if i < train_end:
                    qa.split_type = "train"
                    train_count += 1
                elif i < val_end:
                    qa.split_type = "val"
                    val_count += 1
                else:
                    qa.split_type = "test"
                    test_count += 1
            
            logger.debug(
                f"Split {question_type} - "
                f"train: {train_end}, val: {val_end - train_end}, test: {total - val_end}"
            )
        
        # 提交数据集划分结果到数据库
        try:
            self.db.commit()
            logger.info(f"Dataset split committed to database")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to commit dataset split: {e}")
            raise QAGenerationError(f"Database commit failed: {e}")
        
        # 计算实际比例（可能与指定比例略有偏差）
        total_qa = len(qa_pairs)
        actual_train_ratio = train_count / total_qa
        actual_val_ratio = val_count / total_qa
        actual_test_ratio = test_count / total_qa
        
        results = {
            "dataset_id": dataset_id,
            "total_qa_pairs": total_qa,
            "train_count": train_count,
            "val_count": val_count,
            "test_count": test_count,
            "train_ratio": actual_train_ratio,
            "val_ratio": actual_val_ratio,
            "test_ratio": actual_test_ratio,
            "question_types": list(qa_by_type.keys()),
            "random_seed": random_seed
        }
        
        logger.info(
            f"Dataset split completed - "
            f"Train: {train_count} ({actual_train_ratio:.2%}), "
            f"Val: {val_count} ({actual_val_ratio:.2%}), "
            f"Test: {test_count} ({actual_test_ratio:.2%})"
        )
        
        return results
    
    def get_generation_stats(self, dataset_id: int) -> Dict[str, Any]:
        """
        获取数据集的问答对生成统计信息
        
        本方法提供数据集中问答对的详细统计，包括总数、按问题类型分布、按数据集划分分布等。
        
        Args:
            dataset_id (int): 数据集ID
        
        Returns:
            Dict[str, Any]: 统计信息字典，包含以下字段：
                - dataset_id: 数据集ID
                - total_qa_pairs: 总问答对数量
                - by_question_type: 按问题类型统计的字典
                    - exact: 精确匹配问题数量
                    - fuzzy: 模糊匹配问题数量
                    - reverse: 反向查询问题数量
                    - natural: 自然语言问题数量
                - by_split_type: 按数据集划分统计的字典
                    - train: 训练集数量
                    - val: 验证集数量
                    - test: 测试集数量
        
        使用场景：
            - 查看数据集生成进度
            - 验证数据集划分是否均衡
            - 生成数据集报告
        """
        # 统计总问答对数量
        total_qa = self.db.query(QAPair).filter(
            QAPair.dataset_id == dataset_id
        ).count()
        
        if total_qa == 0:
            return {
                "dataset_id": dataset_id,
                "total_qa_pairs": 0,
                "by_question_type": {},
                "by_split_type": {}
            }
        
        # 按问题类型统计
        by_question_type = {}
        for q_type in ["exact", "fuzzy", "reverse", "natural"]:
            count = self.db.query(QAPair).filter(
                QAPair.dataset_id == dataset_id,
                QAPair.question_type == q_type
            ).count()
            by_question_type[q_type] = count
        
        # 按数据集划分统计
        by_split_type = {}
        for s_type in ["train", "val", "test"]:
            count = self.db.query(QAPair).filter(
                QAPair.dataset_id == dataset_id,
                QAPair.split_type == s_type
            ).count()
            by_split_type[s_type] = count
        
        return {
            "dataset_id": dataset_id,
            "total_qa_pairs": total_qa,
            "by_question_type": by_question_type,
            "by_split_type": by_split_type
        }
