"""
银行数据加载服务

功能：
- 从UNL文件加载银行联行号数据
- 支持定时自动更新
- 增量更新，避免重复数据
"""

import os
from datetime import datetime
from typing import List, Dict, Tuple
from pathlib import Path
from sqlalchemy.orm import Session
from loguru import logger

from app.models.bank_code import BankCode
from app.models.dataset import Dataset


class BankDataLoader:
    """银行数据加载器"""
    
    def __init__(self, db: Session):
        self.db = db
        self.data_dir = Path("data")
        self.unl_file = self.data_dir / "T_BANK_LINE_NO_ICBC_ALL.unl"
    
    def load_from_unl_file(self, file_path: str = None) -> Dict[str, any]:
        """
        从UNL文件加载银行数据
        
        文件格式：
        - 分隔符：竖线（|）
        - 第1列：联行号（bank_code）
        - 第2列：银行名称（bank_name）
        - 第3列：清算号（clearing_code）
        
        Args:
            file_path: UNL文件路径，默认使用data/T_BANK_LINE_NO_ICBC_ALL.unl
        
        Returns:
            加载结果统计
        """
        if file_path is None:
            file_path = str(self.unl_file)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"UNL文件不存在: {file_path}")
        
        logger.info(f"开始加载UNL文件: {file_path}")
        
        # 创建或获取数据集
        dataset = self._get_or_create_dataset(file_path)
        
        # 读取文件
        total_lines = 0
        valid_lines = 0
        skipped_lines = 0
        new_records = 0
        updated_records = 0
        error_lines = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    total_lines += 1
                    
                    # 跳过空行
                    if not line.strip():
                        skipped_lines += 1
                        continue
                    
                    try:
                        # 解析行数据
                        parts = line.strip().split('|')
                        
                        if len(parts) < 3:
                            logger.warning(f"行 {line_num}: 字段不足，跳过")
                            skipped_lines += 1
                            continue
                        
                        bank_code = parts[0].strip()
                        bank_name = parts[1].strip()
                        clearing_code = parts[2].strip()
                        
                        # 验证必填字段
                        if not bank_code or not bank_name:
                            logger.warning(f"行 {line_num}: 联行号或银行名称为空，跳过")
                            skipped_lines += 1
                            continue
                        
                        valid_lines += 1
                        
                        # 检查是否已存在
                        existing = self.db.query(BankCode).filter(
                            BankCode.bank_code == bank_code
                        ).first()
                        
                        if existing:
                            # 更新现有记录
                            if existing.bank_name != bank_name or existing.clearing_code != clearing_code:
                                existing.bank_name = bank_name
                                existing.clearing_code = clearing_code
                                existing.dataset_id = dataset.id
                                updated_records += 1
                        else:
                            # 创建新记录
                            new_record = BankCode(
                                dataset_id=dataset.id,
                                bank_code=bank_code,
                                bank_name=bank_name,
                                clearing_code=clearing_code,
                                is_valid=True
                            )
                            self.db.add(new_record)
                            new_records += 1
                        
                        # 每1000条提交一次
                        if (new_records + updated_records) % 1000 == 0:
                            self.db.commit()
                            logger.info(f"已处理 {new_records + updated_records} 条记录...")
                    
                    except Exception as e:
                        logger.error(f"行 {line_num} 处理失败: {e}")
                        error_lines += 1
                        continue
            
            # 最终提交
            self.db.commit()
            
            # 更新数据集统计
            dataset.total_records = new_records + updated_records
            dataset.valid_records = new_records + updated_records
            dataset.invalid_records = error_lines
            dataset.status = "validated"
            self.db.commit()
            
            result = {
                "success": True,
                "dataset_id": dataset.id,
                "total_lines": total_lines,
                "valid_lines": valid_lines,
                "new_records": new_records,
                "updated_records": updated_records,
                "skipped_lines": skipped_lines,
                "error_lines": error_lines,
                "file_path": file_path,
                "loaded_at": datetime.now().isoformat()
            }
            
            logger.info(
                f"UNL文件加载完成 - "
                f"总行数: {total_lines}, "
                f"有效行: {valid_lines}, "
                f"新增: {new_records}, "
                f"更新: {updated_records}, "
                f"跳过: {skipped_lines}, "
                f"错误: {error_lines}"
            )
            
            return result
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"加载UNL文件失败: {e}")
            raise
    
    def _get_or_create_dataset(self, file_path: str) -> Dataset:
        """获取或创建数据集记录"""
        file_name = os.path.basename(file_path)
        
        # 查找现有数据集
        dataset = self.db.query(Dataset).filter(
            Dataset.filename == file_name
        ).first()
        
        if dataset:
            # 更新现有数据集
            dataset.status = "processing"
            dataset.updated_at = datetime.now().isoformat()
        else:
            # 创建新数据集
            dataset = Dataset(
                filename=file_name,
                file_path=file_path,
                file_size=os.path.getsize(file_path),
                total_records=0,
                valid_records=0,
                invalid_records=0,
                status="processing",
                uploaded_by=None  # 系统自动加载
            )
            self.db.add(dataset)
        
        self.db.commit()
        return dataset
    
    def check_and_load_if_exists(self) -> Dict[str, any]:
        """
        检查UNL文件是否存在，如果存在则加载
        
        Returns:
            加载结果或None
        """
        if self.unl_file.exists():
            logger.info(f"发现UNL文件: {self.unl_file}")
            return self.load_from_unl_file()
        else:
            logger.info(f"UNL文件不存在: {self.unl_file}")
            return {
                "success": False,
                "message": "UNL文件不存在",
                "file_path": str(self.unl_file)
            }
    
    def get_load_statistics(self) -> Dict[str, any]:
        """获取数据加载统计信息"""
        try:
            total_records = self.db.query(BankCode).count()
            
            # 按数据集统计
            datasets = self.db.query(Dataset).all()
            dataset_stats = []
            for ds in datasets:
                dataset_stats.append({
                    "id": ds.id,
                    "filename": ds.filename,
                    "total_records": ds.total_records,
                    "valid_records": ds.valid_records,
                    "status": ds.status,
                    "created_at": ds.created_at
                })
            
            return {
                "total_records": total_records,
                "datasets": dataset_stats,
                "last_check": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {
                "error": str(e)
            }
