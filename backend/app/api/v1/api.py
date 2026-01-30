"""
API v1 路由汇总模块

本模块将所有功能模块的路由汇总到一个主路由器中，
便于在主应用中统一注册。采用模块化设计，每个功能
领域有独立的路由文件。

路由结构：
- /auth: 用户认证（登录、注册、令牌刷新等）
- /users: 用户管理（用户CRUD、个人资料等）
- /data: 数据管理（数据集上传、预览、验证等）
- /training: 训练管理（模型训练、任务监控等）
- /models: 模型管理（模型列表、部署、评估等）
- /qa: 问答服务（问答查询、历史记录等）
- /system: 系统管理（健康检查、配置、日志等）

所有路由都会自动添加/api/v1前缀（在main.py中配置）。
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, datasets, training, models, qa, system

# 创建API v1的主路由器
api_router = APIRouter()

# 认证相关路由
# 包含登录、注册、令牌刷新、密码重置等端点
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])

# 用户管理路由
# 包含用户CRUD、个人资料管理、权限管理等端点
api_router.include_router(users.router, prefix="/users", tags=["用户管理"])

# 数据管理路由
# 包含数据集上传、预览、验证、删除等端点
api_router.include_router(datasets.router, prefix="/data", tags=["数据管理"])

# 训练管理路由
# 包含模型训练、任务监控、训练历史等端点
api_router.include_router(training.router, prefix="/training", tags=["训练管理"])

# 模型管理路由
# 包含模型列表、模型部署、模型评估等端点
api_router.include_router(models.router, prefix="/models", tags=["模型管理"])

# 问答服务路由
# 包含问答查询、查询历史、反馈收集等端点
api_router.include_router(qa.router, prefix="/qa", tags=["问答服务"])

# 系统管理路由
# 包含健康检查、系统配置、日志查询等端点
api_router.include_router(system.router, prefix="/system", tags=["系统管理"])