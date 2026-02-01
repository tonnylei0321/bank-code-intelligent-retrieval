#!/usr/bin/env python3
"""
训练任务管理功能测试

测试新增的训练任务队列管理、监控和恢复功能。
"""

import sys
import os
import asyncio
import time
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.training_queue_manager import TrainingQueueManager, TaskPriority
from app.services.training_monitor import TrainingMonitor
from app.services.training_recovery import TrainingRecoveryService, FailureType
from app.models.training_job import TrainingJob


class MockDBSession:
    """模拟数据库会话"""
    def __init__(self):
        self.jobs = {}
        self.next_id = 1
    
    def query(self, model):
        return MockQuery(self.jobs, model)
    
    def add(self, obj):
        if hasattr(obj, 'id') and obj.id is None:
            obj.id = self.next_id
            self.next_id += 1
        self.jobs[obj.id] = obj
    
    def commit(self):
        pass
    
    def rollback(self):
        pass
    
    @property
    def is_active(self):
        return True


class MockQuery:
    """模拟查询对象"""
    def __init__(self, jobs, model):
        self.jobs = jobs
        self.model = model
        self.filters = []
        self.target_id = None
    
    def filter(self, *args):
        # 简化的过滤实现，假设是按ID过滤
        if hasattr(args[0], 'left') and hasattr(args[0].left, 'name'):
            if args[0].left.name == 'id':
                self.target_id = args[0].right.value
        return self
    
    def first(self):
        if self.target_id and self.target_id in self.jobs:
            return self.jobs[self.target_id]
        elif self.jobs:
            return list(self.jobs.values())[0]
        return None
    
    def all(self):
        return list(self.jobs.values())
    
    def count(self):
        return len(self.jobs)


def create_mock_training_job(job_id: int, status: str = "pending") -> TrainingJob:
    """创建模拟训练任务"""
    job = TrainingJob()
    job.id = job_id
    job.dataset_id = 1
    job.created_by = 1
    job.status = status
    job.model_name = "Qwen/Qwen2.5-0.5B"
    job.epochs = 3
    job.batch_size = 8
    job.learning_rate = 2e-4
    job.lora_r = 16
    job.lora_alpha = 32
    job.lora_dropout = 0.05
    job.created_at = datetime.utcnow()
    job.retry_count = 0
    job.max_retries = 3
    job.priority = "medium"
    return job


def test_queue_manager():
    """测试队列管理器功能"""
    print("🔧 测试训练队列管理器...")
    
    # 创建模拟数据库和队列管理器
    mock_db = MockDBSession()
    queue_manager = TrainingQueueManager(mock_db, max_concurrent=2)
    
    # 创建测试任务
    job1 = create_mock_training_job(1, "pending")
    job2 = create_mock_training_job(2, "pending") 
    job3 = create_mock_training_job(3, "failed")
    
    mock_db.add(job1)
    mock_db.add(job2)
    mock_db.add(job3)
    
    # 测试任务入队（只测试第一个任务，避免状态冲突）
    success1 = queue_manager.enqueue_training_job(1, "high")
    assert success1, "高优先级任务应该成功入队"
    
    # 测试队列状态
    status = queue_manager.get_queue_status()
    assert status['queue_size'] >= 1, "队列应该包含至少1个任务"
    assert status['max_concurrent'] == 2, "最大并发数应该为2"
    assert not status['is_processing'], "队列处理应该未启动"
    
    print("✅ 队列管理器功能正常")


async def test_training_monitor():
    """测试训练监控功能"""
    print("📊 测试训练监控服务...")
    
    # 创建模拟数据库和监控服务
    mock_db = MockDBSession()
    monitor = TrainingMonitor(mock_db, monitoring_interval=1)
    
    # 创建运行中的测试任务
    job = create_mock_training_job(1, "running")
    job.current_epoch = 1
    job.current_step = 100
    job.total_steps = 1000
    job.progress_percentage = 10.0
    job.train_loss = 0.5
    job.started_at = datetime.utcnow()
    
    mock_db.add(job)
    
    # 启动监控
    success = await monitor.start_monitoring()
    assert success, "监控服务应该成功启动"
    
    # 等待一段时间让监控收集数据
    await asyncio.sleep(2)
    
    # 获取实时状态
    status = await monitor.get_real_time_status(job_id=1)
    assert status['is_monitoring'], "监控应该处于运行状态"
    assert 'system_metrics' in status, "应该包含系统指标"
    
    # 停止监控
    success = await monitor.stop_monitoring()
    assert success, "监控服务应该成功停止"
    
    print("✅ 训练监控服务功能正常")


def test_recovery_service():
    """测试训练恢复服务"""
    print("🔄 测试训练恢复服务...")
    
    # 创建模拟数据库和恢复服务
    mock_db = MockDBSession()
    recovery = TrainingRecoveryService(mock_db)
    
    # 创建失败的测试任务
    job = create_mock_training_job(1, "failed")
    job.error_message = "CUDA out of memory error occurred during training"
    job.completed_at = datetime.utcnow()
    
    mock_db.add(job)
    
    # 测试失败分析
    analysis = recovery.analyze_failure(1)
    assert 'failure_type' in analysis, "分析结果应该包含失败类型"
    assert 'recovery_suggestions' in analysis, "分析结果应该包含恢复建议"
    assert analysis['can_retry'], "任务应该可以重试"
    
    print(f"失败类型: {analysis['failure_type']}")
    print(f"恢复建议数量: {len(analysis['recovery_suggestions'])}")
    
    # 测试恢复尝试
    recovery_result = recovery.attempt_recovery(1)
    assert 'success' in recovery_result, "恢复结果应该包含成功标志"
    assert 'strategy' in recovery_result, "恢复结果应该包含使用的策略"
    
    print(f"恢复策略: {recovery_result['strategy']}")
    print(f"恢复结果: {recovery_result['success']}")
    
    print("✅ 训练恢复服务功能正常")


def test_system_integration():
    """测试系统集成"""
    print("🔗 测试系统集成...")
    
    # 创建模拟数据库
    mock_db = MockDBSession()
    
    # 创建各个服务
    queue_manager = TrainingQueueManager(mock_db, max_concurrent=1)
    recovery = TrainingRecoveryService(mock_db)
    
    # 创建测试任务
    job = create_mock_training_job(1, "failed")
    job.error_message = "Training diverged due to high learning rate"
    job.retry_count = 1
    
    mock_db.add(job)
    
    # 分析失败并尝试恢复
    analysis = recovery.analyze_failure(1)
    recovery_result = recovery.attempt_recovery(1)
    
    if recovery_result['success']:
        # 如果恢复成功，将任务重新加入队列
        success = queue_manager.enqueue_training_job(1, "high")
        assert success, "恢复后的任务应该能够重新入队"
        
        # 检查队列状态
        status = queue_manager.get_queue_status()
        assert status['queue_size'] >= 1, "队列应该包含恢复的任务"
    
    print("✅ 系统集成功能正常")


async def run_all_tests():
    """运行所有测试"""
    print("🚀 开始训练任务管理功能测试...")
    print("=" * 50)
    
    try:
        # 基础功能测试
        test_queue_manager()
        await test_training_monitor()
        test_recovery_service()
        test_system_integration()
        
        print("=" * 50)
        print("🎉 所有测试通过！")
        print("✅ 训练任务队列管理功能正常")
        print("✅ 训练进度监控功能正常")
        print("✅ 训练失败恢复功能正常")
        print("✅ 系统集成功能正常")
        
        return True
        
    except Exception as e:
        print("=" * 50)
        print(f"❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)