# 银行代码智能检索系统 (Bank Code Intelligent Retrieval System)

基于大模型的银行代码智能检索和训练数据生成平台

## 🚀 项目特性

- **智能检索**: 使用自然语言查询银行代码信息
- **RAG增强**: 结合检索增强生成技术提高准确性
- **智能生成**: 自动生成多样化的训练数据
- **模型训练**: 支持自定义小模型训练和优化
- **Web界面**: 现代化的React前端管理界面
- **API接口**: 完整的RESTful API

## 🏗️ 技术架构

### 后端 (MVP)
- **框架**: FastAPI + Python 3.9+
- **数据库**: SQLite
- **AI模型**: Qwen2.5-1.5B-Instruct
- **向量数据库**: FAISS
- **设备支持**: CPU, CUDA, MPS (Apple Silicon)

### 前端
- **框架**: React 18 + TypeScript
- **UI库**: Ant Design
- **状态管理**: React Hooks
- **构建工具**: Create React App

## 📦 快速开始

### 环境要求

- Python 3.9+
- Node.js 16+
- 8GB+ RAM (推荐16GB)
- Apple Silicon Mac (MPS支持) 或 NVIDIA GPU (可选)

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/tonnylei0321/bank-code-intelligent-retrieval.git
cd bank-code-intelligent-retrieval
```

2. **后端设置**
```bash
cd mvp
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **前端设置**
```bash
cd frontend
npm install
```

4. **启动服务**

后端:
```bash
cd mvp
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

前端:
```bash
cd frontend
npm start
```

5. **访问应用**
- 前端界面: http://localhost:3000
- API文档: http://localhost:8000/docs

### 默认账号
- 用户: `testuser` / `test123`
- 管理员: `admin` / `admin123`

## 📖 功能指南

### 1. 数据管理
- 上传银行数据文件 (.unl格式)
- 智能生成训练样本
- 数据验证和预处理

### 2. 模型训练
- 选择训练数据集
- 配置训练参数
- 监控训练进度

### 3. 智能查询
- 自然语言查询银行信息
- RAG增强的准确回答
- 查询历史记录

## 🔧 配置说明

### 内存优化 (Apple Silicon)
```bash
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.8
```

### 模型配置
- 默认模型: `Qwen/Qwen2.5-1.5B-Instruct`
- 支持本地模型和Hugging Face模型
- 自动设备检测 (MPS/CUDA/CPU)

## 📁 项目结构

```
bank-code-intelligent-retrieval/
├── README.md
├── .gitignore
├── docs/                    # 文档
├── frontend/               # React前端
│   ├── src/
│   ├── public/
│   └── package.json
├── mvp/                    # Python后端
│   ├── app/
│   │   ├── api/           # API路由
│   │   ├── models/        # 数据模型
│   │   └── services/      # 业务逻辑
│   ├── requirements.txt
│   └── README.md
└── scripts/               # 部署脚本
```

## 🚀 部署

### 生产环境
- 使用Nginx反向代理
- 配置HTTPS证书
- 设置环境变量
- 配置日志轮转

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [Qwen](https://github.com/QwenLM/Qwen) - 大语言模型
- [FastAPI](https://fastapi.tiangolo.com/) - 后端框架
- [React](https://reactjs.org/) - 前端框架
- [Ant Design](https://ant.design/) - UI组件库

## 📞 联系方式

如有问题或建议，请创建 [Issue](https://github.com/tonnylei0321/bank-code-intelligent-retrieval/issues)