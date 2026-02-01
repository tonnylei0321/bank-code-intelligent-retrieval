# RAG配置参数修改错误修复报告

## 问题描述

用户在RAG管理界面修改参数时遇到错误：`更新RAG配置失败: vector_weight和keyword_weight的和必须等于1.0`

## 问题根因

原有的权重验证逻辑存在缺陷：
1. 前端只发送用户修改的字段（部分配置）
2. 后端验证逻辑要求如果同时存在`vector_weight`和`keyword_weight`，它们的和必须等于1.0
3. 但当用户只修改其中一个权重时，验证逻辑没有自动计算另一个权重

## 修复方案

### 1. 修改权重验证逻辑

在`mvp/app/services/rag_service.py`的`_validate_config`方法中：

**修复前：**
```python
# 混合检索参数验证
if "vector_weight" in config:
    weight = float(config["vector_weight"])
    if not 0.0 <= weight <= 1.0:
        raise ValueError("vector_weight必须在0.0-1.0之间")
    validated["vector_weight"] = weight

if "keyword_weight" in config:
    weight = float(config["keyword_weight"])
    if not 0.0 <= weight <= 1.0:
        raise ValueError("keyword_weight必须在0.0-1.0之间")
    validated["keyword_weight"] = weight

# 确保权重和为1
if "vector_weight" in validated and "keyword_weight" in validated:
    total_weight = validated["vector_weight"] + validated["keyword_weight"]
    if abs(total_weight - 1.0) > 0.01:
        raise ValueError("vector_weight和keyword_weight的和必须等于1.0")
```

**修复后：**
```python
# 混合检索参数验证
vector_weight_provided = "vector_weight" in config
keyword_weight_provided = "keyword_weight" in config

if vector_weight_provided:
    weight = float(config["vector_weight"])
    if not 0.0 <= weight <= 1.0:
        raise ValueError("vector_weight必须在0.0-1.0之间")
    validated["vector_weight"] = weight

if keyword_weight_provided:
    weight = float(config["keyword_weight"])
    if not 0.0 <= weight <= 1.0:
        raise ValueError("keyword_weight必须在0.0-1.0之间")
    validated["keyword_weight"] = weight

# 权重自动计算逻辑
if vector_weight_provided and not keyword_weight_provided:
    # 只提供了vector_weight，自动计算keyword_weight
    validated["keyword_weight"] = 1.0 - validated["vector_weight"]
elif keyword_weight_provided and not vector_weight_provided:
    # 只提供了keyword_weight，自动计算vector_weight
    validated["vector_weight"] = 1.0 - validated["keyword_weight"]
elif vector_weight_provided and keyword_weight_provided:
    # 两个权重都提供了，检查和是否为1.0
    total_weight = validated["vector_weight"] + validated["keyword_weight"]
    if abs(total_weight - 1.0) > 0.01:
        raise ValueError("vector_weight和keyword_weight的和必须等于1.0")
```

### 2. 修复逻辑说明

新的验证逻辑支持三种情况：

1. **只修改vector_weight**：自动计算keyword_weight = 1.0 - vector_weight
2. **只修改keyword_weight**：自动计算vector_weight = 1.0 - keyword_weight  
3. **同时修改两个权重**：验证它们的和是否等于1.0

## 测试验证

创建了完整的测试脚本`mvp/test_rag_config_fix.py`，验证以下场景：

### 测试结果

```
1. 登录获取token...
✅ 登录成功

2. 获取当前RAG配置...
✅ 当前配置获取成功
   vector_weight: 0.6
   keyword_weight: 0.4

3. 测试只修改vector_weight为0.7...
✅ 更新成功
   vector_weight: 0.7
   keyword_weight: 0.30000000000000004
   权重和: 1.0

4. 测试只修改keyword_weight为0.3...
✅ 更新成功
   vector_weight: 0.7
   keyword_weight: 0.3
   权重和: 1.0

5. 测试同时修改两个权重（和不等于1.0，应该失败）...
✅ 正确拒绝了无效的权重组合

6. 测试同时修改两个权重（和等于1.0，应该成功）...
✅ 更新成功
   vector_weight: 0.8
   keyword_weight: 0.2

🎉 所有测试通过！RAG配置修复成功！
```

## 后端日志验证

修复后的后端日志显示权重自动计算正常工作：

```
2026-01-31 21:05:51 | INFO | app.services.rag_service:update_config:180 - RAG配置已更新: {'vector_weight': 0.7, 'keyword_weight': 0.30000000000000004}
2026-01-31 21:05:57 | INFO | app.services.rag_service:update_config:180 - RAG配置已更新: {'keyword_weight': 0.3, 'vector_weight': 0.7}
2026-01-31 21:06:03 | ERROR | app.services.rag_service:update_config:184 - 更新RAG配置失败: vector_weight和keyword_weight的和必须等于1.0
2026-01-31 21:06:09 | INFO | app.services.rag_service:update_config:180 - RAG配置已更新: {'vector_weight': 0.8, 'keyword_weight': 0.2}
```

## 用户体验改进

修复后，用户可以：

1. **单独修改向量权重**：系统自动调整关键词权重，确保和为1.0
2. **单独修改关键词权重**：系统自动调整向量权重，确保和为1.0
3. **同时修改两个权重**：系统验证和是否为1.0，提供明确的错误提示

## 修复文件

- `mvp/app/services/rag_service.py` - 修复权重验证逻辑
- `mvp/test_rag_config_fix.py` - 测试脚本（新增）

## 状态

✅ **修复完成** - RAG参数修改功能已恢复正常，用户可以正常使用RAG管理界面修改配置参数。