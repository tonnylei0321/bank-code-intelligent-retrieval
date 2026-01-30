"""
Business Logic Services - 业务逻辑服务模块

本模块包含所有业务逻辑服务，负责处理应用的核心功能。

服务列表：
    - data_manager: 数据管理服务（数据上传、验证、预览）
    - teacher_model: 大模型API客户端（调用通义千问生成问答对）
    - qa_generator: 问答对生成服务（批量生成训练数据）
    - model_trainer: 模型训练服务（LoRA微调）
    - model_evaluator: 模型评估服务（性能评估和对比）
    - query_service: 查询推理服务（实时推理）
    - baseline_system: 基准系统服务（Elasticsearch检索）

服务架构：
    1. 数据层：data_manager负责数据的导入和管理
    2. 生成层：teacher_model和qa_generator负责生成训练数据
    3. 训练层：model_trainer负责模型训练
    4. 评估层：model_evaluator负责模型评估
    5. 推理层：query_service和baseline_system负责实时查询

使用说明：
    所有服务都需要数据库会话（Session）作为初始化参数。
    服务之间通过数据库进行数据交换，保证数据一致性。
"""
