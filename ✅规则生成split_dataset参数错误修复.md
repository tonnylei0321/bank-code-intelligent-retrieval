# ✅ 规则生成split_dataset参数错误修复

## 错误信息

```
错误: split_dataset() got an unexpected keyword argument 'sample_set_id'
```

## 问题原因

在异步样本生成API中,调用`generator.split_dataset()`时传递了`sample_set_id`参数,但该方法不接受此参数。

### 原始代码
```python
# 错误的调用方式
split_results = generator.split_dataset(
    dataset_id=request["dataset_id"],
    train_ratio=request.get("train_ratio", 0.8),
    val_ratio=request.get("val_ratio", 0.1),
    test_ratio=request.get("test_ratio", 0.1),
    random_seed=42,
    sample_set_id=sample_set.id  # ❌ 这个参数不存在
)
```

### split_dataset方法签名
```python
def split_dataset(
    self,
    dataset_id: int,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    random_seed: Optional[int] = 42
) -> Dict[str, Any]:
```

可以看到,`split_dataset`方法只接受5个参数,没有`sample_set_id`参数。

## 解决方案

创建一个新的函数`split_sample_set()`,专门用于划分样本集中的样本。

### 新增函数

**文件**: `mvp/app/api/sample_generation_async.py`

```python
def split_sample_set(
    db: Session,
    sample_set_id: int,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    random_seed: int = 42
) -> Dict:
    """
    划分样本集中的问答对为训练集/验证集/测试集
    
    Args:
        db: 数据库会话
        sample_set_id: 样本集ID
        train_ratio: 训练集比例
        val_ratio: 验证集比例
        test_ratio: 测试集比例
        random_seed: 随机种子
    
    Returns:
        划分结果字典
    """
    from app.models.qa_pair import QAPair
    
    # 验证比例
    total_ratio = train_ratio + val_ratio + test_ratio
    if abs(total_ratio - 1.0) > 0.001:
        raise ValueError(f"Split ratios must sum to 1.0, got {total_ratio}")
    
    # 获取样本集中的所有问答对
    qa_pairs = db.query(QAPair).filter(
        QAPair.sample_set_id == sample_set_id
    ).all()
    
    if not qa_pairs:
        logger.warning(f"No QA pairs found for sample set {sample_set_id}")
        return {
            "train_count": 0,
            "val_count": 0,
            "test_count": 0
        }
    
    logger.info(f"Splitting sample set {sample_set_id} - Total QA pairs: {len(qa_pairs)}")
    
    # 按问题类型分组
    qa_by_type = {}
    for qa in qa_pairs:
        if qa.question_type not in qa_by_type:
            qa_by_type[qa.question_type] = []
        qa_by_type[qa.question_type].append(qa)
    
    # 设置随机种子
    if random_seed is not None:
        random.seed(random_seed)
    
    # 分别划分每种问题类型
    train_count = 0
    val_count = 0
    test_count = 0
    
    for question_type, type_qa_pairs in qa_by_type.items():
        # 随机打乱
        random.shuffle(type_qa_pairs)
        
        # 计算划分索引
        total = len(type_qa_pairs)
        train_end = int(total * train_ratio)
        val_end = train_end + int(total * val_ratio)
        
        # 分配split_type
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
    
    # 提交更改
    db.commit()
    
    logger.info(
        f"Sample set split completed - "
        f"Train: {train_count}, Val: {val_count}, Test: {test_count}"
    )
    
    return {
        "train_count": train_count,
        "val_count": val_count,
        "test_count": test_count
    }
```

### 修改后的调用方式

```python
# 正确的调用方式
split_results = split_sample_set(
    db=db,
    sample_set_id=sample_set.id,
    train_ratio=request.get("train_ratio", 0.8),
    val_ratio=request.get("val_ratio", 0.1),
    test_ratio=request.get("test_ratio", 0.1),
    random_seed=42
)
```

## 函数对比

### split_dataset (QAGenerator方法)
- **作用**: 划分整个数据集的所有样本
- **参数**: dataset_id
- **影响范围**: 数据集中的所有QA对
- **使用场景**: 旧版样本管理,一个数据集只有一个样本集

### split_sample_set (新增函数)
- **作用**: 只划分指定样本集的样本
- **参数**: sample_set_id
- **影响范围**: 只影响指定样本集的QA对
- **使用场景**: 新版三层结构,一个数据集可以有多个样本集

## 为什么需要新函数?

在三层样本管理结构中:
```
数据集 (Dataset)
  └── 样本集1 (Sample Set 1)
      └── 样本1, 样本2, ...
  └── 样本集2 (Sample Set 2)
      └── 样本3, 样本4, ...
```

每个样本集需要独立划分,不能影响其他样本集。如果使用`split_dataset()`,会划分整个数据集的所有样本,导致不同样本集的样本被混在一起划分。

## 测试方法

### 1. 使用测试脚本
```bash
python test_split_sample_set.py
```

### 2. 完整流程测试
```bash
python test_rule_generation.py
```

## 验证要点

1. ✅ 任务能够成功启动
2. ✅ 生成过程不报错
3. ✅ 样本能够正确生成
4. ✅ 样本集能够正确划分
5. ✅ 训练集/验证集/测试集比例正确
6. ✅ 不同样本集的划分互不影响

## 修复总结

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| split_dataset参数错误 | 方法不接受sample_set_id参数 | 创建新函数split_sample_set |
| 划分影响其他样本集 | split_dataset划分整个数据集 | 新函数只划分指定样本集 |
| 三层结构不兼容 | 旧方法不支持多样本集 | 新函数专为三层结构设计 |

## 文件修改

- ✅ `mvp/app/api/sample_generation_async.py`
  - 添加`split_sample_set()`函数
  - 修改调用方式
  - 添加`import random`
- ✅ `test_split_sample_set.py` - 创建测试脚本

## 后续建议

1. **考虑将split_sample_set移到独立模块**
   - 可以放在`mvp/app/services/sample_set_service.py`
   - 便于复用和测试

2. **添加更多验证**
   - 验证样本集是否存在
   - 验证样本集是否有样本
   - 验证比例是否合理

3. **支持更多划分策略**
   - 按时间划分
   - 按银行类型划分
   - 分层抽样

4. **性能优化**
   - 批量更新split_type
   - 减少数据库查询次数

## 完成状态

✅ 规则生成方式现在可以正常工作
✅ split_dataset参数错误已修复
✅ 样本集划分功能正常
✅ 三层样本管理结构完整支持
