# 智能问答系统使用指南

## 概述

智能问答系统是一个基于小模型和Redis的增强问答解决方案，提供快速、准确的银行信息查询服务。

## 系统架构

```
用户问题 → 小模型分析 → 多策略检索 → 答案生成 → 历史存储
                ↓
        [Redis缓存] + [RAG向量库]
```

### 核心组件

1. **小模型服务** - 问题理解和答案生成
2. **Redis服务** - 快速数据缓存和检索
3. **智能问答服务** - 整合多种技术的问答流程
4. **RAG服务** - 向量检索（可选）

## 功能特性

### 1. 多模型支持

- **OpenAI GPT系列**: GPT-3.5-turbo, GPT-4
- **Anthropic Claude系列**: Claude-3-haiku, Claude-3-sonnet
- **本地模型**: 支持Hugging Face模型

### 2. 智能检索策略

- **Redis检索**: 快速精确匹配
- **RAG检索**: 语义相似度检索
- **混合检索**: 结合多种策略
- **智能选择**: 根据问题类型自动选择最佳策略

### 3. 问答历史管理

- 自动保存问答记录
- 用户历史查询
- 热门问题统计
- 质量评估和学习

## 安装和配置

### 1. 安装依赖

```bash
cd mvp
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.intelligent_qa.example .env
# 编辑 .env 文件，配置Redis和模型参数
```

### 3. 初始化系统

```bash
python scripts/init_intelligent_qa.py
```

### 4. 启动服务

```bash
python app/main.py
```

## API接口

### 智能问答

```http
POST /api/intelligent-qa/ask
Content-Type: application/json
Authorization: Bearer <token>

{
  "question": "工商银行西单支行的联行号是多少？",
  "model_type": "gpt-3.5-turbo",
  "retrieval_strategy": "intelligent"
}
```

### 获取可用模型

```http
GET /api/intelligent-qa/models
Authorization: Bearer <token>
```

### 获取问答历史

```http
GET /api/intelligent-qa/history?limit=20
Authorization: Bearer <token>
```

### Redis数据管理

```http
# 加载银行数据到Redis
POST /api/redis/load-data?force_reload=false
Authorization: Bearer <token>

# 搜索银行信息
GET /api/redis/search?query=工商银行&search_type=name&limit=10
Authorization: Bearer <token>

# 获取Redis统计信息
GET /api/redis/stats
Authorization: Bearer <token>
```

## 前端界面

### 1. 智能问答页面

- 路径: `/intelligent-qa`
- 功能: 智能问答对话、模型选择、历史记录

### 2. Redis管理页面

- 路径: `/redis` (管理员)
- 功能: 数据加载、搜索测试、统计信息

## 配置说明

### Redis配置

```env
# Redis连接
REDIS_URL=redis://localhost:6379/0
REDIS_CONNECTION_TIMEOUT=10
REDIS_MAX_CONNECTIONS=20

# 数据管理
REDIS_KEY_PREFIX=bank_code:
REDIS_BATCH_SIZE=1000
```

### 模型配置

```env
# API密钥（至少配置一个）
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# 本地模型
LOCAL_MODEL_NAME=microsoft/DialoGPT-medium
MODEL_DEVICE=auto

# 生成参数
MODEL_DEFAULT_TEMPERATURE=0.1
MODEL_DEFAULT_MAX_TOKENS=512
```

### 问答服务配置

```env
# 检索策略
QA_DEFAULT_RETRIEVAL_STRATEGY=intelligent
QA_MAX_CONTEXT_RESULTS=5

# 质量控制
QA_ANSWER_CONFIDENCE_THRESHOLD=0.7
QA_QUALITY_THRESHOLD=0.8

# 历史记录
QA_ENABLE_HISTORY=true
QA_HISTORY_LIMIT=100
```

## 使用示例

### 1. 基本问答

```python
from app.services.intelligent_qa_service import IntelligentQAService

# 初始化服务
qa_service = IntelligentQAService(db, redis_service, model_service)
await qa_service.initialize()

# 提问
result = await qa_service.ask_question(
    "中国工商银行西单支行的联行号是多少？",
    user_id=1
)

print(f"答案: {result['answer']}")
print(f"置信度: {result['confidence']}")
print(f"匹配银行: {result['matched_banks']}")
```

### 2. 模型切换

```python
from app.services.small_model_service import ModelType

# 切换到GPT-4
model_service.set_model(ModelType.OPENAI_GPT4)

# 使用特定模型提问
result = await qa_service.ask_question(
    question="建设银行总行联行号",
    model_type=ModelType.OPENAI_GPT4
)
```

### 3. Redis数据管理

```python
from app.services.redis_service import RedisService

# 初始化Redis服务
redis_service = RedisService(db)
await redis_service.initialize()

# 加载银行数据
result = await redis_service.load_bank_data_to_redis()

# 搜索银行
banks = await redis_service.search_banks("工商银行", "name", 10)
```

## 性能优化

### 1. Redis优化

- 使用连接池减少连接开销
- 批量操作提高数据加载速度
- 合理设置TTL避免内存溢出

### 2. 模型优化

- 选择合适的模型平衡速度和质量
- 使用本地模型减少API调用成本
- 启用缓存避免重复计算

### 3. 检索优化

- 智能策略选择最佳检索方法
- 混合检索提高召回率和准确率
- 上下文限制控制响应时间

## 监控和维护

### 1. 健康检查

```http
GET /api/intelligent-qa/health
GET /api/redis/health
```

### 2. 统计信息

```http
GET /api/intelligent-qa/stats
GET /api/redis/stats
```

### 3. 日志监控

- 应用日志: `logs/app_*.log`
- 错误日志: `logs/error_*.log`
- Redis日志: Redis服务器日志

## 故障排除

### 常见问题

1. **Redis连接失败**
   - 检查Redis服务是否启动
   - 验证连接URL和端口
   - 检查防火墙设置

2. **模型API调用失败**
   - 验证API密钥是否正确
   - 检查网络连接
   - 确认API配额是否充足

3. **本地模型加载失败**
   - 检查模型名称是否正确
   - 确认磁盘空间是否充足
   - 验证CUDA环境（如果使用GPU）

4. **问答质量不佳**
   - 调整模型参数（temperature, max_tokens）
   - 优化检索策略
   - 增加训练数据

### 调试模式

```bash
# 启用详细日志
export LOG_LEVEL=DEBUG

# 运行初始化脚本查看详细信息
python scripts/init_intelligent_qa.py
```

## 扩展开发

### 1. 添加新模型

```python
# 在 SmallModelService 中添加新模型支持
class ModelType(Enum):
    CUSTOM_MODEL = "custom-model"

# 实现模型调用方法
async def _call_custom_model(self, prompt: str) -> str:
    # 自定义模型调用逻辑
    pass
```

### 2. 自定义检索策略

```python
# 在 IntelligentQAService 中添加新策略
class RetrievalStrategy(Enum):
    CUSTOM_STRATEGY = "custom_strategy"

# 实现检索方法
async def _custom_retrieve(self, question: str, analysis: Dict) -> List[Dict]:
    # 自定义检索逻辑
    pass
```

### 3. 扩展问答功能

```python
# 添加新的问答处理逻辑
async def enhanced_ask_question(self, question: str, **kwargs):
    # 预处理
    processed_question = self.preprocess_question(question)
    
    # 调用基础问答
    result = await self.ask_question(processed_question, **kwargs)
    
    # 后处理
    enhanced_result = self.postprocess_answer(result)
    
    return enhanced_result
```

## 最佳实践

1. **配置管理**: 使用环境变量管理敏感配置
2. **错误处理**: 实现完善的异常处理和降级策略
3. **性能监控**: 定期检查响应时间和资源使用
4. **数据备份**: 定期备份Redis数据和问答历史
5. **安全考虑**: 实施访问控制和API限流
6. **版本管理**: 记录模型版本和配置变更

## 支持和反馈

如有问题或建议，请通过以下方式联系：

- 创建GitHub Issue
- 发送邮件至技术支持
- 查看项目文档和FAQ

---

更新时间: 2026-02-01
版本: 1.0.0