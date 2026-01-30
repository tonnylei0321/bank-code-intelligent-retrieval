"""
API Routes - API路由模块

本模块包含所有FastAPI路由端点。

路由列表：
    - auth: 认证API（登录、注册、获取当前用户）
    - datasets: 数据集管理API（上传、验证、查询）
    - training: 训练任务API（创建、查询、停止）
    - evaluation: 评估API（评估模型、生成报告）
    - query: 查询API（问答查询）
    - qa_pairs: 问答对API（生成、查询）
    - logs: 日志API（查询日志）
    - admin: 管理API（用户管理、系统管理）

使用说明：
    所有路由都使用FastAPI的APIRouter进行组织。
    路由按功能模块分组，使用tags进行分类。
    所有路由都需要认证（除了登录端点）。
    管理员专用路由使用@require_admin装饰器。
"""
