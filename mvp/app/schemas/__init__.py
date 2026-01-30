"""
Pydantic Schemas - 数据验证模式模块

本模块包含所有API请求和响应的Pydantic数据模型。

模式列表：
    - auth: 认证相关模式（登录、注册、Token）
    - bank_code: 银行联行号模式（创建、更新、响应）
    - dataset: 数据集模式（上传、验证、统计）
    - qa_pair: 问答对模式（生成、查询、统计）

Pydantic特点：
    - 自动数据验证：基于类型注解自动验证输入数据
    - 数据序列化：自动转换Python对象为JSON
    - 数据反序列化：自动转换JSON为Python对象
    - 错误提示：提供详细的验证错误信息

使用说明：
    所有模式都继承自BaseModel，使用类型注解定义字段。
    使用Field()函数添加字段约束和描述。
    使用validator装饰器添加自定义验证逻辑。
"""
