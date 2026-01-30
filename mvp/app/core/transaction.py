"""
数据库事务管理工具模块

提供数据库事务管理的高级工具，包括：
1. 事务上下文管理器（自动提交/回滚）
2. 原子文件操作（文件和数据库一致性）
3. 模型一致性验证
4. 事务原子性保证
5. 复杂多步骤操作的事务管理器

用于确保数据库操作的ACID特性，特别是在涉及文件操作时。
"""
from contextlib import contextmanager
from typing import Optional, Callable
from sqlalchemy.orm import Session
from pathlib import Path
import os

from app.core.logging import logger
from app.core.exceptions import APIException


@contextmanager
def transaction_scope(db: Session, rollback_on_error: bool = True):
    """
    数据库事务上下文管理器，支持自动提交和回滚
    
    提供简洁的事务管理方式，自动处理提交和回滚：
    - 正常执行完成时自动提交
    - 发生异常时自动回滚
    - 确保事务的原子性
    
    使用示例:
        with transaction_scope(db) as session:
            # 执行数据库操作
            session.add(new_record)
            session.query(Model).filter(...).update(...)
            # 成功时自动提交
            # 异常时自动回滚
    
    Args:
        db: 数据库会话对象
        rollback_on_error: 发生错误时是否回滚，默认True
    
    Yields:
        数据库会话对象
    
    Raises:
        Exception: 回滚后重新抛出原始异常
    """
    try:
        yield db
        db.commit()  # 提交事务
        logger.debug("事务提交成功")
    except Exception as e:
        if rollback_on_error:
            db.rollback()  # 回滚事务
            logger.warning(f"事务因错误回滚: {e}")
        raise  # 重新抛出异常


@contextmanager
def atomic_file_operation(
    file_path: str,
    db: Session,
    cleanup_on_error: bool = True
):
    """
    原子文件操作上下文管理器，确保文件和数据库的一致性
    
    在涉及文件和数据库操作时，确保两者的一致性：
    - 如果数据库提交失败，删除已创建的文件
    - 如果文件操作失败，回滚数据库事务
    - 保证"要么全部成功，要么全部失败"
    
    使用场景：
    - 上传文件并记录到数据库
    - 保存模型文件并更新训练记录
    - 导出数据并记录导出历史
    
    使用示例:
        with atomic_file_operation(file_path, db) as (path, session):
            # 写入文件
            with open(path, 'w') as f:
                f.write(data)
            
            # 更新数据库
            record = Model(file_path=path)
            session.add(record)
            # 文件和数据库一起提交
    
    Args:
        file_path: 文件路径
        db: 数据库会话
        cleanup_on_error: 发生错误时是否删除文件，默认True
    
    Yields:
        元组 (文件路径, 数据库会话)
    
    Raises:
        Exception: 清理后重新抛出原始异常
    """
    file_created = False
    file_path_obj = Path(file_path)
    
    try:
        # Check if file will be created
        if not file_path_obj.exists():
            file_created = True
        
        yield file_path, db
        
        # Commit database transaction
        db.commit()
        logger.debug(f"Atomic operation completed: {file_path}")
        
    except Exception as e:
        # Rollback database
        db.rollback()
        logger.warning(f"Atomic operation failed, rolling back: {e}")
        
        # Cleanup file if it was created during this operation
        if cleanup_on_error and file_created and file_path_obj.exists():
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up file after failed operation: {file_path}")
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup file {file_path}: {cleanup_error}")
        
        raise


def verify_model_consistency(db: Session, model_path: str, record_id: int, model_class) -> bool:
    """
    Verify consistency between model file and database record
    验证模型文件和数据库记录的一致性
    
    Args:
        db: Database session
        model_path: Path to model file
        record_id: Database record ID
        model_class: SQLAlchemy model class
    
    Returns:
        True if consistent, False otherwise
    """
    try:
        # Check if file exists
        file_exists = Path(model_path).exists()
        
        # Check if database record exists and has correct path
        record = db.query(model_class).filter(model_class.id == record_id).first()
        
        if not record:
            logger.warning(f"Database record {record_id} not found")
            return False
        
        # Check if record has model_path attribute
        if not hasattr(record, 'model_path'):
            logger.warning(f"Record {record_id} does not have model_path attribute")
            return False
        
        record_path = record.model_path
        
        # Both should exist or both should not exist
        if file_exists and record_path:
            # Normalize paths for comparison
            file_path_normalized = str(Path(model_path).resolve())
            record_path_normalized = str(Path(record_path).resolve())
            
            if file_path_normalized == record_path_normalized:
                logger.debug(f"Model consistency verified for record {record_id}")
                return True
            else:
                logger.warning(
                    f"Path mismatch for record {record_id}: "
                    f"file={file_path_normalized}, db={record_path_normalized}"
                )
                return False
        elif not file_exists and not record_path:
            logger.debug(f"No model file for record {record_id} (consistent)")
            return True
        else:
            logger.warning(
                f"Inconsistency for record {record_id}: "
                f"file_exists={file_exists}, record_path={record_path}"
            )
            return False
    
    except Exception as e:
        logger.error(f"Error verifying model consistency: {e}")
        return False


def ensure_transaction_atomicity(
    db: Session,
    operation: Callable,
    error_message: str = "Operation failed"
) -> any:
    """
    Execute operation with transaction atomicity guarantee
    执行操作并保证事务原子性
    
    Args:
        db: Database session
        operation: Callable to execute
        error_message: Error message prefix
    
    Returns:
        Result of operation
    
    Raises:
        APIException: If operation fails
    """
    try:
        result = operation()
        db.commit()
        return result
    except Exception as e:
        db.rollback()
        logger.error(f"{error_message}: {e}")
        raise APIException(
            error_code="TRANSACTION_FAILED",
            error_message=f"{error_message}: {str(e)}",
            status_code=500
        )


class TransactionManager:
    """
    Transaction manager for complex multi-step operations
    复杂多步骤操作的事务管理器
    """
    
    def __init__(self, db: Session):
        """
        Initialize transaction manager
        
        Args:
            db: Database session
        """
        self.db = db
        self.operations = []
        self.rollback_actions = []
    
    def add_operation(
        self,
        operation: Callable,
        rollback_action: Optional[Callable] = None,
        description: str = ""
    ):
        """
        Add operation to transaction
        
        Args:
            operation: Operation to execute
            rollback_action: Action to execute on rollback
            description: Operation description
        """
        self.operations.append({
            "operation": operation,
            "rollback_action": rollback_action,
            "description": description
        })
    
    def execute(self) -> any:
        """
        Execute all operations in transaction
        
        Returns:
            Result of last operation
        
        Raises:
            Exception: If any operation fails
        """
        executed_count = 0
        result = None
        
        try:
            for i, op_info in enumerate(self.operations):
                operation = op_info["operation"]
                description = op_info["description"]
                
                logger.debug(f"Executing operation {i+1}/{len(self.operations)}: {description}")
                result = operation()
                executed_count += 1
            
            # Commit transaction
            self.db.commit()
            logger.info(f"Transaction completed successfully: {executed_count} operations")
            return result
        
        except Exception as e:
            # Rollback database
            self.db.rollback()
            logger.error(f"Transaction failed at operation {executed_count+1}: {e}")
            
            # Execute rollback actions in reverse order
            for i in range(executed_count - 1, -1, -1):
                rollback_action = self.operations[i]["rollback_action"]
                if rollback_action:
                    try:
                        logger.debug(f"Executing rollback action {i+1}")
                        rollback_action()
                    except Exception as rollback_error:
                        logger.error(f"Rollback action {i+1} failed: {rollback_error}")
            
            raise
