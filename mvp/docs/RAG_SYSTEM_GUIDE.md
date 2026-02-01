# RAG系统升级指南

## 概述

本系统已从基于关键词的简单检索升级为基于向量数据库的RAG（检索增强生成）系统，提供更智能的语义检索能力。

## 技术架构

### 核心组件

1. **向量数据库**: ChromaDB
   - 轻量级、高性能的向量数据库
   - 支持持久化存储
   - 内置相似度搜索

2. **嵌入模型**: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
   - 多语言支持，特别适合中文
   - 轻量级模型，推理速度快
   - 384维向量表示

3. **检索策略**: 语义相似度检索
   - 基于向量相似度的语义搜索
   - 支持相似度阈值过滤
   - 可扩展的混合检索（向量+关键词）

### 系统流程

```
用户问题 → 向量化 → 向量数据库检索 → 相似度排序 → 返回结果
```

## 安装和配置

### 1. 安装依赖

```bash
cd mvp
python install_rag_dependencies.py
```

### 2. 重启服务

```bash
./cleanup_and_restart.sh
```

### 3. 初始化向量数据库

通过管理界面或API初始化：

**管理界面**:
- 访问 `http://localhost:3000/rag`
- 点击"初始化向量数据库"

**API调用**:
```bash
curl -X POST "http://localhost:8000/api/v1/rag/initialize" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

## API接口

### 管理接口

#### 初始化向量数据库
```http
POST /api/v1/rag/initialize?force_rebuild=false
Authorization: Bearer {admin_token}
```

#### 更新向量数据库
```http
POST /api/v1/rag/update
Authorization: Bearer {admin_token}
```

#### 获取系统状态
```http
GET /api/v1/rag/stats
Authorization: Bearer {token}
```

### 检索接口

#### 语义检索
```http
POST /api/v1/rag/search
Content-Type: application/json
Authorization: Bearer {token}

{
  "question": "工商银行北京分行",
  "top_k": 5,
  "similarity_threshold": 0.7
}
```

#### 混合检索
```http
POST /api/v1/rag/hybrid-search
Content-Type: application/json
Authorization: Bearer {token}

{
  "question": "工商银行北京分行",
  "top_k": 5,
  "vector_weight": 0.7,
  "keyword_weight": 0.3
}
```

## 使用指南

### 管理员操作

1. **首次使用**
   - 初始化向量数据库
   - 检查同步状态
   - 测试检索功能

2. **日常维护**
   - 定期更新向量数据库（当银行数据有变化时）
   - 监控系统状态
   - 根据需要调整相似度阈值

3. **故障排除**
   - 如果检索结果不准确，可以重建向量数据库
   - 检查日志文件排查问题
   - 验证嵌入模型是否正常加载

### 开发者集成

#### 在查询服务中使用RAG

```python
from app.services.rag_service import RAGService

# 初始化RAG服务
rag_service = RAGService(db_session)

# 检索相关银行
results = await rag_service.retrieve_relevant_banks(
    question="工商银行北京分行",
    top_k=5,
    similarity_threshold=0.7
)

# 混合检索
hybrid_results = await rag_service.hybrid_retrieve(
    question="工商银行北京分行",
    top_k=5,
    vector_weight=0.7,
    keyword_weight=0.3
)
```

#### 自定义嵌入模型

```python
# 使用不同的嵌入模型
rag_service = RAGService(
    db=db_session,
    embedding_model_name="sentence-transformers/distiluse-base-multilingual-cased"
)
```

## 性能优化

### 检索性能

1. **相似度阈值调优**
   - 默认阈值: 0.7
   - 提高阈值: 更精确但可能遗漏相关结果
   - 降低阈值: 更全面但可能包含不相关结果

2. **批量处理**
   - 向量化过程支持批量处理
   - 默认批次大小: 100条记录

3. **缓存策略**
   - 查询结果缓存（1小时TTL）
   - 向量缓存在内存中

### 存储优化

1. **向量数据库大小**
   - 每条记录约1.5KB（384维向量 + 元数据）
   - 10万条记录约150MB存储空间

2. **定期清理**
   - 删除无效的银行记录对应的向量
   - 压缩向量数据库文件

## 监控和日志

### 关键指标

1. **系统状态**
   - 向量数据库记录数
   - 源数据库记录数
   - 同步状态

2. **检索性能**
   - 平均检索时间
   - 相似度分布
   - 缓存命中率

### 日志位置

- 应用日志: `mvp/logs/app_*.log`
- 错误日志: `mvp/logs/error_*.log`
- 后端日志: `mvp/backend.log`

### 关键日志信息

```
RAG: Starting semantic retrieval for question: 工商银行北京分行
RAG: Found 5 potential matches
RAG: Final Result 1: 中国工商银行股份有限公司北京分行 -> 102100099996 (Score: 0.923)
```

## 故障排除

### 常见问题

1. **向量数据库初始化失败**
   ```
   错误: Failed to initialize vector database
   解决: 检查磁盘空间，确保data/vector_db目录可写
   ```

2. **嵌入模型加载失败**
   ```
   错误: Failed to load embedding model
   解决: 检查网络连接，模型会自动从HuggingFace下载
   ```

3. **检索结果为空**
   ```
   原因: 向量数据库未初始化或数据为空
   解决: 执行初始化操作
   ```

4. **检索结果不准确**
   ```
   原因: 相似度阈值设置不当
   解决: 调整similarity_threshold参数
   ```

### 调试步骤

1. **检查系统状态**
   ```bash
   curl -H "Authorization: Bearer TOKEN" http://localhost:8000/api/v1/rag/stats
   ```

2. **测试检索功能**
   ```bash
   curl -X POST -H "Content-Type: application/json" \
        -H "Authorization: Bearer TOKEN" \
        -d '{"question":"工商银行","top_k":3}' \
        http://localhost:8000/api/v1/rag/search
   ```

3. **查看日志**
   ```bash
   tail -f mvp/logs/app_$(date +%Y-%m-%d).log | grep RAG
   ```

## 升级和迁移

### 从关键词检索升级

系统会自动降级到关键词检索如果向量检索失败，确保向后兼容性。

### 数据迁移

现有的银行数据会自动向量化，无需手动迁移。

### 版本兼容性

- ChromaDB: 0.4.18+
- sentence-transformers: 2.2.2+
- Python: 3.9+

## 最佳实践

1. **定期更新**
   - 银行数据更新后及时同步向量数据库
   - 建议设置自动更新任务

2. **性能监控**
   - 监控检索响应时间
   - 跟踪相似度分数分布

3. **质量保证**
   - 定期测试检索准确性
   - 收集用户反馈优化阈值

4. **备份策略**
   - 定期备份向量数据库
   - 保留配置文件副本

## 技术支持

如遇到问题，请：

1. 查看本文档的故障排除部分
2. 检查系统日志
3. 在管理界面查看RAG系统状态
4. 联系技术支持团队

---

*最后更新: 2026-01-31*