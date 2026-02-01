"""
数据管理服务模块

提供数据文件上传、验证和预览功能，包括：
1. CSV文件上传和保存
2. 数据格式验证和解析
3. 联行号数据验证
4. 数据统计和预览
5. Elasticsearch索引集成

特性：
- 原子文件操作（文件和数据库一致性）
- 事务安全的数据验证
- 详细的错误记录
- 自动索引到Elasticsearch
"""
import csv
import os
from typing import List, Tuple, Optional
from pathlib import Path
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.models.bank_code import BankCode
from app.core.logging import logger
from app.core.config import settings
from app.core.transaction import atomic_file_operation, transaction_scope


class DataManager:
    """
    数据管理器类
    
    负责处理联行号数据的上传、验证和管理。
    确保文件操作和数据库操作的一致性。
    
    Attributes:
        db: 数据库会话
        baseline_system: 基准检索系统（Elasticsearch）
    """
    
    def __init__(self, db: Session, baseline_system=None):
        """
        初始化数据管理器
        
        Args:
            db: SQLAlchemy数据库会话
            baseline_system: 基准检索系统实例（可选）
        """
        self.db = db
        self.baseline_system = baseline_system
    
    async def upload_file(self, file: UploadFile, user_id: int) -> Dataset:
        """
        上传并保存数据文件，使用原子操作确保一致性
        
        执行流程：
        1. 验证文件格式（仅支持CSV）
        2. 创建上传目录
        3. 生成唯一文件名
        4. 使用原子操作保存文件和创建数据库记录
        5. 如果任何步骤失败，自动回滚
        
        Args:
            file: 上传的文件对象
            user_id: 上传用户的ID
            
        Returns:
            创建的Dataset对象
            
        Raises:
            ValueError: 文件格式无效或上传失败
        """
        # 验证文件扩展名
        if not file.filename.endswith(('.csv', '.unl')):
            raise ValueError("仅支持CSV和UNL文件格式")
        
        # 创建上传目录（如果不存在）
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成唯一文件名（使用时间戳）
        timestamp = Path(file.filename).stem
        file_path = upload_dir / f"{timestamp}_{file.filename}"
        
        # 读取文件内容
        content = await file.read()
        file_size = len(content)
        
        # 使用原子文件操作确保一致性
        try:
            with atomic_file_operation(str(file_path), self.db) as (path, session):
                # 保存文件到磁盘
                with open(path, 'wb') as f:
                    f.write(content)
                
                logger.info(f"文件已保存: {path} ({file_size} 字节)")
                
                # 创建数据集记录
                dataset = Dataset(
                    filename=file.filename,
                    file_path=str(file_path),
                    file_size=file_size,
                    total_records=0,
                    valid_records=0,
                    invalid_records=0,
                    status='uploaded',
                    uploaded_by=user_id
                )
                
                session.add(dataset)
                # 如果没有异常，事务会自动提交
            
            # 刷新以获取生成的ID
            self.db.refresh(dataset)
            logger.info(f"数据集已创建: ID={dataset.id}, 文件名={dataset.filename}")
            
            return dataset
        
        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            raise ValueError(f"文件上传失败: {str(e)}")
    
    def validate_data(self, dataset_id: int) -> Tuple[int, int, int, List[str]]:
        """
        验证和解析上传文件中的数据，使用事务确保安全
        
        验证规则：
        1. 每行必须有3列：银行名称、联行号、清算行行号
        2. 银行名称不能为空
        3. 联行号必须是12位数字
        4. 清算行行号必须是12位数字
        
        执行流程：
        1. 读取CSV文件
        2. 自动检测CSV格式和是否有表头
        3. 逐行验证数据
        4. 将有效记录保存到数据库
        5. 记录无效记录的错误信息
        6. 更新数据集统计信息
        7. 可选：索引到Elasticsearch
        
        Args:
            dataset_id: 数据集ID
            
        Returns:
            四元组 (总记录数, 有效记录数, 无效记录数, 错误列表)
            
        Raises:
            ValueError: 数据集不存在或文件不存在
        """
        # 获取数据集
        dataset = self.db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"数据集 {dataset_id} 不存在")
        
        if not os.path.exists(dataset.file_path):
            raise ValueError(f"文件不存在: {dataset.file_path}")
        
        logger.info(f"开始验证数据集 {dataset_id}: {dataset.filename}")
        
        # 如果数据集已经验证过，先清空旧的记录
        if dataset.status == 'validated':
            logger.info(f"数据集 {dataset_id} 已验证过，清空旧记录")
            self.db.query(BankCode).filter(BankCode.dataset_id == dataset_id).delete()
            self.db.commit()
        
        total_records = 0
        valid_records = 0
        invalid_records = 0
        errors = []
        
        # 维护已插入的联行号集合，用于检测同一批次中的重复
        inserted_bank_codes = set()
        
        # 使用事务作用域进行数据库操作
        try:
            with transaction_scope(self.db) as session:
                with open(dataset.file_path, 'r', encoding='utf-8') as f:
                    # 根据文件扩展名确定分隔符
                    file_extension = dataset.file_path.lower().split('.')[-1]
                    if file_extension == 'unl':
                        # UNL文件使用竖线分隔符
                        delimiter = '|'
                        logger.info(f"检测到UNL文件，使用竖线分隔符")
                    else:
                        # CSV文件，尝试检测分隔符
                        sample = f.read(1024)
                        f.seek(0)
                        
                        # 使用csv.Sniffer检测CSV格式
                        try:
                            dialect = csv.Sniffer().sniff(sample)
                            delimiter = dialect.delimiter
                            has_header = csv.Sniffer().has_header(sample)
                        except:
                            delimiter = ','
                            has_header = False
                        
                        logger.info(f"检测到CSV文件，使用分隔符: '{delimiter}'")
                    
                    # 对于UNL文件，通常没有表头
                    if file_extension == 'unl':
                        has_header = False
                    
                    reader = csv.reader(f, delimiter=delimiter)
                    
                    # 读取第一行，判断是否为表头
                    first_row = next(reader, None)
                    if not first_row:
                        raise ValueError("文件为空")
                    
                    # 检测列顺序
                    # 可能的列名：bank_name, bank_code, clearing_code
                    # 或中文：银行名称, 联行号, 清算行号
                    col_mapping = {}
                    
                    if has_header:
                        # 有表头，根据表头确定列顺序
                        for idx, col_name in enumerate(first_row):
                            col_lower = col_name.strip().lower()
                            if col_lower in ['bank_name', '银行名称', 'bankname']:
                                col_mapping['bank_name'] = idx
                            elif col_lower in ['bank_code', '联行号', 'bankcode']:
                                col_mapping['bank_code'] = idx
                            elif col_lower in ['clearing_code', '清算行号', 'clearingcode', '清算行行号']:
                                col_mapping['clearing_code'] = idx
                        
                        # 如果没有识别到列，使用默认顺序
                        if not col_mapping:
                            logger.warning("无法识别表头，使用默认列顺序")
                            col_mapping = {'bank_name': 0, 'bank_code': 1, 'clearing_code': 2}
                    else:
                        # 没有表头，尝试根据第一行数据判断列顺序
                        # 如果第一列是12位数字，可能是联行号在前
                        if len(first_row) >= 3:
                            first_col = first_row[0].strip()
                            if len(first_col) == 12 and first_col.isdigit():
                                # 第一列是数字，可能是：联行号, 银行名称, 清算行号
                                logger.info("检测到第一列为12位数字，使用列顺序：联行号, 银行名称, 清算行号")
                                col_mapping = {'bank_code': 0, 'bank_name': 1, 'clearing_code': 2}
                            else:
                                # 第一列不是数字，使用默认顺序：银行名称, 联行号, 清算行号
                                logger.info("使用默认列顺序：银行名称, 联行号, 清算行号")
                                col_mapping = {'bank_name': 0, 'bank_code': 1, 'clearing_code': 2}
                        else:
                            col_mapping = {'bank_name': 0, 'bank_code': 1, 'clearing_code': 2}
                        
                        # 如果没有表头，第一行是数据，需要处理
                        if not has_header:
                            row = first_row
                            row_num = 1
                            total_records += 1
                            
                            # 验证行格式（必须有3列）
                            if len(row) < 3:
                                invalid_records += 1
                                errors.append(f"第{row_num}行: 期望3列，实际{len(row)}列")
                            else:
                                bank_name = row[col_mapping['bank_name']].strip()
                                bank_code = row[col_mapping['bank_code']].strip()
                                clearing_code = row[col_mapping['clearing_code']].strip()
                                
                                # 验证字段内容
                                if not bank_name:
                                    invalid_records += 1
                                    errors.append(f"第{row_num}行: 银行名称为空")
                                elif not bank_code or len(bank_code) != 12 or not bank_code.isdigit():
                                    invalid_records += 1
                                    errors.append(f"第{row_num}行: 联行号'{bank_code}'无效（必须是12位数字）")
                                elif not clearing_code or len(clearing_code) != 12 or not clearing_code.isdigit():
                                    invalid_records += 1
                                    errors.append(f"第{row_num}行: 清算行行号'{clearing_code}'无效（必须是12位数字）")
                                else:
                                    # 创建联行号记录
                                    try:
                                        bank_code_record = BankCode(
                                            dataset_id=dataset_id,
                                            bank_name=bank_name,
                                            bank_code=bank_code,
                                            clearing_code=clearing_code,
                                            is_valid=1
                                        )
                                        session.add(bank_code_record)
                                        inserted_bank_codes.add(bank_code)  # 记录已插入的联行号
                                        valid_records += 1
                                    except Exception as e:
                                        invalid_records += 1
                                        errors.append(f"第{row_num}行: 数据库错误 - {str(e)}")
                                        logger.error(f"添加联行号记录失败: {e}")
                    
                    logger.info(f"列映射: {col_mapping}")
                    
                    for row_num, row in enumerate(reader, start=2 if has_header else 2):
                        total_records += 1
                        
                        # 验证行格式（必须有3列）
                        if len(row) < 3:
                            invalid_records += 1
                            errors.append(f"第{row_num}行: 期望3列，实际{len(row)}列")
                            continue
                        
                        bank_name = row[col_mapping['bank_name']].strip()
                        bank_code = row[col_mapping['bank_code']].strip()
                        clearing_code = row[col_mapping['clearing_code']].strip()
                        
                        # 验证字段内容
                        if not bank_name:
                            invalid_records += 1
                            errors.append(f"第{row_num}行: 银行名称为空")
                            continue
                        
                        if not bank_code or len(bank_code) != 12 or not bank_code.isdigit():
                            invalid_records += 1
                            errors.append(f"第{row_num}行: 联行号'{bank_code}'无效（必须是12位数字）")
                            continue
                        
                        if not clearing_code or len(clearing_code) != 12 or not clearing_code.isdigit():
                            invalid_records += 1
                            errors.append(f"第{row_num}行: 清算行行号'{clearing_code}'无效（必须是12位数字）")
                            continue
                        
                        # 检查是否已存在相同的联行号（在同一数据集中）
                        # 1. 检查数据库中已有的记录
                        existing = session.query(BankCode).filter(
                            BankCode.dataset_id == dataset_id,
                            BankCode.bank_code == bank_code
                        ).first()
                        
                        # 2. 检查当前批次中已插入的记录
                        if existing or bank_code in inserted_bank_codes:
                            # 跳过重复记录
                            invalid_records += 1
                            errors.append(f"第{row_num}行: 联行号'{bank_code}'重复（已存在）")
                            logger.warning(f"跳过重复联行号: {bank_code}")
                            continue
                        
                        # 创建联行号记录
                        try:
                            bank_code_record = BankCode(
                                dataset_id=dataset_id,
                                bank_name=bank_name,
                                bank_code=bank_code,
                                clearing_code=clearing_code,
                                is_valid=1
                            )
                            session.add(bank_code_record)
                            inserted_bank_codes.add(bank_code)  # 记录已插入的联行号
                            valid_records += 1
                        except Exception as e:
                            invalid_records += 1
                            errors.append(f"第{row_num}行: 数据库错误 - {str(e)}")
                            logger.error(f"添加联行号记录失败: {e}")
                
                # 更新数据集统计信息
                dataset.total_records = total_records
                dataset.valid_records = valid_records
                dataset.invalid_records = invalid_records
                dataset.status = 'validated'
                
                # 事务在这里自动提交
            
            logger.info(f"验证完成: {valid_records}/{total_records} 条有效记录")
            
            # 如果基准系统可用且有有效记录，则索引到Elasticsearch
            if self.baseline_system and self.baseline_system.is_available() and valid_records > 0:
                try:
                    logger.info(f"正在将 {valid_records} 条记录索引到Elasticsearch...")
                    bank_codes = self.db.query(BankCode)\
                        .filter(BankCode.dataset_id == dataset_id)\
                        .all()
                    
                    index_result = self.baseline_system.index_bank_codes(bank_codes)
                    
                    if index_result.get("success"):
                        # 在单独的事务中更新状态
                        with transaction_scope(self.db):
                            dataset.status = 'indexed'
                        logger.info(f"成功索引 {index_result.get('indexed')} 条记录到Elasticsearch")
                    else:
                        logger.warning(f"Elasticsearch索引失败: {index_result.get('error')}")
                        
                except Exception as e:
                    logger.error(f"Elasticsearch索引错误: {e}")
                    # 索引失败不影响验证结果
            
        except Exception as e:
            logger.error(f"数据集验证错误: {e}")
            raise ValueError(f"数据集验证错误: {str(e)}")
        
        return total_records, valid_records, invalid_records, errors
    
    def get_dataset_stats(self, dataset_id: int) -> Dataset:
        """
        获取数据集统计信息
        
        Args:
            dataset_id: 数据集ID
            
        Returns:
            Dataset对象，包含统计信息
            
        Raises:
            ValueError: 数据集不存在
        """
        dataset = self.db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"数据集 {dataset_id} 不存在")
        
        return dataset
    
    def preview_data(self, dataset_id: int, limit: int = 100) -> List[BankCode]:
        """
        预览数据集中的数据
        
        返回数据集中的前N条记录，用于数据预览。
        
        Args:
            dataset_id: 数据集ID
            limit: 返回的最大记录数，默认100
            
        Returns:
            BankCode记录列表
            
        Raises:
            ValueError: 数据集不存在
        """
        dataset = self.db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"数据集 {dataset_id} 不存在")
        
        records = self.db.query(BankCode)\
            .filter(BankCode.dataset_id == dataset_id)\
            .limit(limit)\
            .all()
        
        return records
