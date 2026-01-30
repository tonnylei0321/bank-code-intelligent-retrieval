# 🔧 RAG调试和超时修复

## 🔍 发现的问题

### 1. 超时问题 ⚠️
- **查询耗时**: 19.9秒
- **前端超时**: 30秒 → 已增加到60秒
- **状态**: ✅ 已修复

### 2. RAG系统未工作 🔴
- **现象**: 日志中没有RAG相关信息
- **原因**: RAG检索逻辑可能有问题
- **状态**: 🔧 正在调试

### 3. 模型幻觉仍存在 🔴
- **问题**: 中国农业银行股份有限公司厦门大同支行
- **模型返回**: 103885472017 (错误)
- **正确答案**: 103393037005
- **状态**: 🔧 需要RAG修复

## ✅ 已完成的修复

### 1. 增加前端超时时间
**文件**: `frontend/src/services/api.ts`
```typescript
// 修复前
timeout: 30000,  // 30秒

// 修复后  
timeout: 60000,  // 60秒
```

### 2. 增强RAG调试日志
**文件**: `mvp/app/services/query_service.py`

#### 增强的query()方法
```python
logger.info(f"RAG enabled: {use_rag}")
if use_rag:
    retrieved_banks = self.retrieve_relevant_banks(question, top_k=5)
    if retrieved_banks:
        # ... 构建上下文
        logger.info(f"RAG: Retrieved {len(retrieved_banks)} relevant banks")
        logger.info(f"RAG Context: {context[:200]}...")
    else:
        logger.warning("RAG: No relevant banks found")
else:
    logger.info("RAG: Disabled by request")
```

#### 增强的retrieve_relevant_banks()方法
```python
logger.info(f"RAG: Starting retrieval for question: {question[:50]}...")
keywords = re.findall(r'[\u4e00-\u9fff]+', question)
logger.info(f"RAG: Extracted keywords: {keywords}")

for keyword in keywords:
    if len(keyword) >= 2:
        logger.info(f"RAG: Searching for keyword: {keyword}")
        records = self.db.query(BankCode).filter(
            BankCode.bank_name.contains(keyword)
        ).limit(top_k).all()
        logger.info(f"RAG: Found {len(records)} records for keyword '{keyword}'")
```

## 🧪 测试计划

### 1. 验证RAG是否被调用
**测试问题**: "中国农业银行股份有限公司厦门大同支行"

**期望日志**:
```
INFO - RAG enabled: True
INFO - RAG: Starting retrieval for question: 中国农业银行股份有限公司厦门大同支行...
INFO - RAG: Extracted keywords: ['中国', '农业', '银行', '股份', '有限', '公司', '厦门', '大同', '支行']
INFO - RAG: Searching for keyword: 中国
INFO - RAG: Found X records for keyword '中国'
INFO - RAG: Searching for keyword: 农业
INFO - RAG: Found X records for keyword '农业'
...
INFO - RAG: Retrieved X relevant banks
INFO - RAG Context: 中国农业银行股份有限公司厦门大同支行: 103393037005...
```

### 2. 验证数据库中的正确数据
```sql
SELECT bank_name, bank_code FROM bank_codes 
WHERE bank_name LIKE '%中国农业银行%厦门%大同%';
```

**期望结果**:
```
中国农业银行股份有限公司厦门大同支行|103393037005
```

### 3. 验证模型生成
**期望**: 基于RAG上下文，模型应该生成正确的联行号103393037005

## 🔧 可能的问题和解决方案

### 问题1: RAG检索不到数据
**可能原因**:
- 关键词提取不准确
- 数据库查询条件太严格
- 银行名称格式不匹配

**解决方案**:
```python
# 更灵活的搜索策略
for keyword in ['中国农业银行', '厦门', '大同']:
    records = self.db.query(BankCode).filter(
        BankCode.bank_name.contains(keyword)
    ).all()
```

### 问题2: 上下文格式不正确
**可能原因**:
- 提示格式与训练时不匹配
- 上下文信息太多或太少

**解决方案**:
```python
# 优化提示格式
if context:
    prompt = f"参考信息：\n{context}\n\n问题：{question}\n答案："
else:
    prompt = f"问题：{question}\n答案："
```

### 问题3: 正则表达式提取失败
**当前问题**: 模型生成了103885472017，但正则没有提取到

**检查**: 
```python
code_pattern = r'\b\d{12}\b'  # 匹配12位数字
```

**可能原因**: 103885472017确实是12位，应该能匹配到

## 📊 性能优化

### 1. 查询速度优化
- **当前**: 19.9秒
- **目标**: <10秒
- **方案**: 
  - 缓存模型加载
  - 优化RAG检索
  - 减少生成长度

### 2. RAG检索优化
- **当前**: 简单关键词匹配
- **升级**: 
  - 使用向量相似度
  - 添加同义词扩展
  - 优化搜索策略

## 🎯 下一步行动

### 立即执行
1. **重启后端服务** ✅
2. **测试RAG调试日志**
3. **验证数据库查询**
4. **检查提取逻辑**

### 如果RAG仍不工作
1. **检查前端请求**: 确认use_rag=true被发送
2. **检查API参数**: 确认参数正确传递
3. **检查数据库连接**: 确认查询能正常执行
4. **简化测试**: 使用最简单的查询测试

### 如果RAG工作但结果错误
1. **优化检索策略**: 更精确的关键词匹配
2. **改进上下文格式**: 与训练格式保持一致
3. **调整生成参数**: 降低temperature，提高确定性

## 📝 监控命令

### 实时查看RAG日志
```bash
tail -f mvp/logs/app_2026-01-21.log | grep -E "RAG|Retrieved|Context|Extracted"
```

### 测试数据库查询
```bash
sqlite3 mvp/data/bank_code.db "
SELECT bank_name, bank_code 
FROM bank_codes 
WHERE bank_name LIKE '%农业银行%' 
  AND bank_name LIKE '%厦门%' 
  AND bank_name LIKE '%大同%'
"
```

---

**修复时间**: 2026-01-21 18:25
**状态**: 🔧 调试中，后端已重启
**下一步**: 测试RAG是否正常工作