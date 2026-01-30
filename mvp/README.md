# 联行号检索模型训练验证系统 (MVP)

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 📋 项目概述

本项目是一个MVP（最小可行产品），旨在验证"使用大模型训练垂直领域小模型"的技术路线可行性。通过联行号智能检索这个具体场景，验证基于大模型的知识蒸馏和微调技术能否在垂直领域达到实用标准。

### 核心功能

- ✅ **数据管理**: 上传、验证、预览联行号数据
- ✅ **训练数据生成**: 使用大模型自动生成多样化问答对
- ✅ **模型训练**: 基于LoRA的参数高效微调
- ✅ **模型评估**: 多维度性能评估和对比分析
- ✅ **智能问答**: 自然语言查询联行号信息
- ✅ **基准对比**: 与Elasticsearch传统检索方案对比

### 技术验证目标

- 验证大模型生成训练数据的质量
- 验证LoRA微调在小模型上的效果
- 验证小模型在垂直领域的准确率（目标≥95%）
- 对比传统检索方案和大模型方案的优劣

## 🚀 快速开始

### 前置要求

- Python 3.9 或更高版本
- 16GB+ RAM（推荐32GB）
- 50GB+ 可用磁盘空间
- 稳定的互联网连接（访问大模型API）
- （可选）NVIDIA GPU with 8GB+ VRAM（用于模型训练）

### 5分钟快速部署

#### 1. 克隆项目

```bash
git clone <repository-url>
cd QWen-Create/mvp
```

#### 2. 创建虚拟环境并安装依赖

```bash
# 创建虚拟环境
python3.9 -m venv .venv

# 激活虚拟环境
# macOS/Linux
source .venv/bin/activate
# Windows
.venv\Scripts\activate

# 升级pip并安装依赖
pip install --upgrade pip
pip install -r requirements.txt
```

#### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
nano .env  # 或使用其他编辑器
```

**必需配置项**:
```bash
# 生成强密钥
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# 配置大模型API密钥（必需）
QWEN_API_KEY=sk-your-api-key-here
```

获取API密钥：访问 [阿里云DashScope](https://dashscope.console.aliyun.com/)

#### 4. 初始化数据库

```bash
python scripts/init_db.py
```

这将创建数据库并初始化默认管理员账号：
- 用户名: `admin`
- 密码: `admin123`

⚠️ **首次登录后请立即修改密码！**

#### 5. 启动服务

**开发模式**（自动重载）:
```bash
./scripts/start.sh --dev
```

**生产模式**:
```bash
./scripts/start.sh
```

#### 6. 验证部署

访问以下URL验证服务是否正常运行：

- 🏥 健康检查: http://localhost:8000/health
- 📚 API文档: http://localhost:8000/docs
- 📖 ReDoc文档: http://localhost:8000/redoc

### 完整使用流程示例

#### 步骤1: 登录获取Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

保存返回的 `access_token` 用于后续请求。

#### 步骤2: 上传联行号数据

准备CSV文件（格式：银行名称,联行号,清算行行号）:
```csv
银行名称,联行号,清算行行号
中国工商银行北京分行,102100000026,102100000000
中国农业银行上海分行,103290000012,103290000000
```

上传数据：
```bash
curl -X POST http://localhost:8000/api/v1/datasets/upload \
  -H "Authorization: Bearer <your-token>" \
  -F "file=@bank_codes.csv"
```

#### 步骤3: 生成训练数据

```bash
curl -X POST http://localhost:8000/api/v1/qa-pairs/generate \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": 1}'
```

这将调用大模型API为每条联行号数据生成多样化的问答对。

#### 步骤4: 启动模型训练

```bash
curl -X POST http://localhost:8000/api/v1/training/start \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": 1,
    "config": {
      "num_epochs": 3,
      "batch_size": 16,
      "learning_rate": 0.0002
    }
  }'
```

#### 步骤5: 查询训练进度

```bash
curl -H "Authorization: Bearer <your-token>" \
  http://localhost:8000/api/v1/training/1
```

#### 步骤6: 评估模型

训练完成后，启动评估：
```bash
curl -X POST http://localhost:8000/api/v1/evaluation/start \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"training_job_id": 1, "include_baseline": true}'
```

#### 步骤7: 使用问答服务

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"question": "中国工商银行北京分行的联行号是什么？"}'
```

### 停止服务

```bash
# 优雅停止
./scripts/stop.sh

# 强制停止
./scripts/stop.sh --force

# 查看状态
./scripts/stop.sh --status
```

## 🛠️ 技术栈

### 后端框架
- **FastAPI**: 现代、高性能的Web框架
- **SQLAlchemy**: ORM数据库工具
- **Pydantic**: 数据验证和设置管理

### 数据库
- **SQLite**: 轻量级关系数据库

### 机器学习
- **PyTorch**: 深度学习框架
- **Transformers**: Hugging Face模型库
- **PEFT**: 参数高效微调（LoRA）
- **Accelerate**: 分布式训练加速

### 检索系统
- **Elasticsearch**: 全文检索引擎（基准对比）

### 测试框架
- **Pytest**: 单元测试框架
- **Hypothesis**: 属性测试框架
- **httpx**: 异步HTTP客户端

### 其他工具
- **python-jose**: JWT认证
- **passlib**: 密码哈希
- **loguru**: 日志管理
- **pandas**: 数据处理

## 📁 项目结构

```
mvp/
├── app/                      # 应用主目录
│   ├── api/                  # API路由
│   │   ├── auth.py          # 认证相关API
│   │   ├── datasets.py      # 数据集管理API
│   │   ├── qa_pairs.py      # 问答对生成API
│   │   ├── training.py      # 模型训练API
│   │   ├── evaluation.py    # 模型评估API
│   │   ├── query.py         # 问答查询API
│   │   ├── logs.py          # 日志查询API
│   │   └── admin.py         # 管理员功能API
│   ├── core/                 # 核心配置
│   │   ├── config.py        # 配置管理
│   │   ├── database.py      # 数据库连接
│   │   ├── security.py      # 安全认证
│   │   ├── exceptions.py    # 异常处理
│   │   ├── logging.py       # 日志配置
│   │   ├── permissions.py   # 权限控制
│   │   ├── rate_limiter.py  # 频率限制
│   │   └── transaction.py   # 事务管理
│   ├── models/               # 数据库模型
│   │   ├── user.py          # 用户模型
│   │   ├── dataset.py       # 数据集模型
│   │   ├── bank_code.py     # 联行号模型
│   │   ├── qa_pair.py       # 问答对模型
│   │   ├── training_job.py  # 训练任务模型
│   │   ├── evaluation.py    # 评估结果模型
│   │   └── query_log.py     # 查询日志模型
│   ├── schemas/              # Pydantic模式
│   │   ├── auth.py          # 认证相关模式
│   │   ├── dataset.py       # 数据集模式
│   │   ├── qa_pair.py       # 问答对模式
│   │   └── bank_code.py     # 联行号模式
│   ├── services/             # 业务逻辑
│   │   ├── data_manager.py  # 数据管理服务
│   │   ├── teacher_model.py # 大模型API客户端
│   │   ├── qa_generator.py  # 问答对生成服务
│   │   ├── model_trainer.py # 模型训练服务
│   │   ├── model_evaluator.py # 模型评估服务
│   │   ├── query_service.py # 问答查询服务
│   │   └── baseline_system.py # 基准检索系统
│   └── main.py               # 应用入口
├── tests/                    # 测试文件
│   ├── test_auth_properties.py
│   ├── test_data_validation_properties.py
│   ├── test_qa_generation_properties.py
│   ├── test_training_properties.py
│   ├── test_evaluation_properties.py
│   ├── test_query_properties.py
│   ├── test_baseline_properties.py
│   ├── test_logging_properties.py
│   └── test_api_properties.py
├── scripts/                  # 脚本文件
│   ├── init_db.py           # 数据库初始化
│   ├── start.sh             # 启动脚本
│   └── stop.sh              # 停止脚本
├── docs/                     # 文档目录
│   ├── API_GUIDE.md         # API使用指南
│   └── DEPLOYMENT.md        # 部署文档
├── data/                     # 数据文件（自动创建）
├── logs/                     # 日志文件（自动创建）
├── models/                   # 模型文件（自动创建）
│   ├── base/                # 基座模型
│   └── finetuned/           # 微调后的模型
├── reports/                  # 评估报告（自动创建）
├── uploads/                  # 上传文件（自动创建）
├── requirements.txt          # Python依赖
├── .env.example             # 环境变量模板
├── .env                     # 环境变量（需创建）
├── pytest.ini               # Pytest配置
└── README.md                # 本文件
```

## 🧪 开发指南

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_auth_properties.py

# 运行属性测试（使用Hypothesis）
pytest tests/test_*_properties.py

# 查看测试覆盖率
pytest --cov=app --cov-report=html

# 生成覆盖率报告
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### 代码规范

本项目遵循以下代码规范：

- ✅ 遵循 PEP 8 代码规范
- ✅ 使用类型注解（Type Hints）
- ✅ 编写详细的文档字符串（Docstrings）
- ✅ 保持函数简洁（单一职责原则）
- ✅ 使用有意义的变量名
- ✅ 编写单元测试和属性测试

### 属性测试说明

本项目使用 **Hypothesis** 进行属性测试，验证系统在各种输入下的正确性：

```python
from hypothesis import given, strategies as st

@given(
    valid_records=st.lists(st.tuples(st.text(), st.text(), st.text())),
    invalid_records=st.lists(st.text())
)
def test_data_validation_completeness(valid_records, invalid_records):
    """
    Feature: bank-code-retrieval, Property 1: 数据验证完整性
    验证：总记录数 = 有效记录数 + 错误记录数
    """
    # 测试逻辑
    pass
```

每个属性测试运行至少100次迭代，确保系统在各种边界情况下都能正确工作。

### 日志查看

```bash
# 查看应用日志
tail -f logs/app_$(date +%Y-%m-%d).log

# 查看错误日志
tail -f logs/error_$(date +%Y-%m-%d).log

# 搜索特定关键词
grep "ERROR" logs/app_*.log
```

### 数据库管理

```bash
# 查看数据库
sqlite3 data/bank_code.db

# 导出数据
sqlite3 data/bank_code.db .dump > backup.sql

# 导入数据
sqlite3 data/bank_code.db < backup.sql
```

## 📚 文档

### 项目文档
- 📋 [需求文档](../.kiro/specs/bank-code-retrieval/requirements.md) - 详细的功能需求和验收标准
- 🎨 [设计文档](../.kiro/specs/bank-code-retrieval/design.md) - 系统架构和设计决策
- ✅ [任务列表](../.kiro/specs/bank-code-retrieval/tasks.md) - 开发任务和进度跟踪

### 使用文档
- 📖 [API使用指南](docs/API_GUIDE.md) - 完整的API接口文档和使用示例
- 🚀 [部署文档](docs/DEPLOYMENT.md) - 详细的部署步骤和配置说明

### 在线文档
- 📚 Swagger UI: http://localhost:8000/docs
- 📖 ReDoc: http://localhost:8000/redoc

## ❓ 常见问题 (FAQ)

### Q1: 如何获取大模型API密钥？

访问 [阿里云DashScope](https://dashscope.console.aliyun.com/) 注册并创建API密钥。

### Q2: 训练需要多长时间？

使用15万条数据训练通常需要6-8小时（取决于硬件配置）。可以使用小数据集（1000条）快速测试，约需30分钟。

### Q3: 没有GPU可以训练吗？

可以，但训练速度会较慢。建议使用小数据集进行测试。

### Q4: 如何修改管理员密码？

首次登录后，使用 `PUT /api/v1/admin/users/{user_id}` 接口修改密码。

### Q5: 如何查看训练进度？

使用 `GET /api/v1/training/{job_id}` 接口查询训练状态和进度。

### Q6: 支持哪些数据格式？

目前支持CSV格式，必须包含三列：银行名称、联行号、清算行行号。

### Q7: 如何停止正在运行的训练任务？

使用 `POST /api/v1/training/{job_id}/stop` 接口停止训练任务。

### Q8: 评估报告在哪里？

评估报告保存在 `reports/` 目录，也可以通过 `GET /api/v1/evaluation/{eval_id}/report` 接口获取。

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出建议！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 👥 联系方式

- 项目维护者: 系统开发团队
- 技术支持: 请提交 Issue

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的Web框架
- [Hugging Face](https://huggingface.co/) - 模型和工具库
- [Hypothesis](https://hypothesis.readthedocs.io/) - 属性测试框架
- [阿里云通义千问](https://dashscope.aliyun.com/) - 大模型API服务

---

**版本**: v1.0.0  
**更新日期**: 2026-01-11  
**状态**: MVP阶段
