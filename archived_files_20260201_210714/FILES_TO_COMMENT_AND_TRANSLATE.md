# 详细文件清单：需要添加中文注释和翻译的文件

## 📝 Python代码文件 - 需要添加中文注释

### MVP项目 (mvp/app) - 43个文件

#### 核心模块 (mvp/app/core)
1. `mvp/app/core/__init__.py` - 模块初始化
2. `mvp/app/core/config.py` - 配置管理（环境变量、应用设置）
3. `mvp/app/core/database.py` - 数据库连接和初始化
4. `mvp/app/core/security.py` - 安全认证（密码哈希、JWT token）⚠️ 已有部分注释
5. `mvp/app/core/exceptions.py` - 异常处理（自定义异常类）
6. `mvp/app/core/logging.py` - 日志配置（日志级别、格式）
7. `mvp/app/core/permissions.py` - 权限控制（角色权限检查）
8. `mvp/app/core/rate_limiter.py` - 频率限制（API限流）
9. `mvp/app/core/transaction.py` - 事务管理（数据库事务）
10. `mvp/app/core/deps.py` - 依赖注入（FastAPI依赖）

#### 数据模型 (mvp/app/models)
11. `mvp/app/models/__init__.py` - 模块初始化
12. `mvp/app/models/user.py` - 用户模型（用户表定义）
13. `mvp/app/models/dataset.py` - 数据集模型（数据集表定义）
14. `mvp/app/models/bank_code.py` - 联行号模型（联行号表定义）
15. `mvp/app/models/qa_pair.py` - 问答对模型（问答对表定义）
16. `mvp/app/models/training_job.py` - 训练任务模型（训练任务表定义）
17. `mvp/app/models/evaluation.py` - 评估结果模型（评估结果表定义）
18. `mvp/app/models/query_log.py` - 查询日志模型（查询日志表定义）

#### API路由 (mvp/app/api)
19. `mvp/app/api/__init__.py` - 模块初始化
20. `mvp/app/api/auth.py` - 认证API（登录、注册、token刷新）
21. `mvp/app/api/datasets.py` - 数据集管理API（上传、验证、预览）
22. `mvp/app/api/qa_pairs.py` - 问答对生成API（生成、查询、删除）
23. `mvp/app/api/training.py` - 模型训练API（启动、查询、停止）
24. `mvp/app/api/evaluation.py` - 模型评估API（启动、查询、报告）
25. `mvp/app/api/query.py` - 问答查询API（单个查询、批量查询）
26. `mvp/app/api/logs.py` - 日志查询API（查询应用日志）
27. `mvp/app/api/admin.py` - 管理员功能API（用户管理、系统配置）

#### 业务服务 (mvp/app/services)
28. `mvp/app/services/__init__.py` - 模块初始化
29. `mvp/app/services/data_manager.py` - 数据管理服务（数据上传、验证、预处理）
30. `mvp/app/services/teacher_model.py` - 大模型API客户端（调用通义千问API）
31. `mvp/app/services/qa_generator.py` - 问答对生成服务（生成训练数据）⚠️ 已有部分注释
32. `mvp/app/services/model_trainer.py` - 模型训练服务（LoRA微调）
33. `mvp/app/services/model_evaluator.py` - 模型评估服务（性能评估）
34. `mvp/app/services/query_service.py` - 问答查询服务（问答推理）
35. `mvp/app/services/baseline_system.py` - 基准检索系统（Elasticsearch对比）

#### 数据验证 (mvp/app/schemas)
36. `mvp/app/schemas/__init__.py` - 模块初始化
37. `mvp/app/schemas/auth.py` - 认证数据模式（登录、注册请求/响应）
38. `mvp/app/schemas/dataset.py` - 数据集数据模式（数据集请求/响应）
39. `mvp/app/schemas/qa_pair.py` - 问答对数据模式（问答对请求/响应）
40. `mvp/app/schemas/bank_code.py` - 联行号数据模式（联行号请求/响应）

#### 其他文件
41. `mvp/app/__init__.py` - 模块初始化
42. `mvp/app/main.py` - 应用入口（FastAPI应用配置）⚠️ 已有部分注释

### Backend项目 (backend/app) - 33个文件

#### 核心模块 (backend/app/core)
43. `backend/app/core/config.py` - 配置管理
44. `backend/app/core/database.py` - 数据库连接
45. `backend/app/core/security.py` - 安全认证
46. `backend/app/core/exceptions.py` - 异常处理

#### 数据模型 (backend/app/models)
47. `backend/app/models/__init__.py` - 模块初始化
48. `backend/app/models/user.py` - 用户模型
49. `backend/app/models/dataset.py` - 数据集模型
50. `backend/app/models/model.py` - 模型模型
51. `backend/app/models/qa.py` - 问答模型
52. `backend/app/models/system.py` - 系统模型
53. `backend/app/models/training.py` - 训练模型

#### API路由 (backend/app/api)
54. `backend/app/api/__init__.py` - 模块初始化
55. `backend/app/api/deps.py` - 依赖注入
56. `backend/app/api/v1/__init__.py` - 模块初始化
57. `backend/app/api/v1/api.py` - API路由聚合
58. `backend/app/api/v1/endpoints/` - 各种API端点（多个文件）

#### 数据验证 (backend/app/schemas)
59. `backend/app/schemas/__init__.py` - 模块初始化
60. `backend/app/schemas/auth.py` - 认证数据模式
61. `backend/app/schemas/user.py` - 用户数据模式
62. `backend/app/schemas/common.py` - 通用数据模式

#### 工具函数 (backend/app/utils)
63. `backend/app/utils/__init__.py` - 模块初始化
64. `backend/app/utils/file_utils.py` - 文件处理工具

#### 数据库初始化 (backend/app/db)
65. `backend/app/db/__init__.py` - 模块初始化
66. `backend/app/db/init_db.py` - 数据库初始化脚本

#### 其他文件
67. `backend/app/__init__.py` - 模块初始化
68. `backend/app/main.py` - 应用入口

---

## 🎨 TypeScript/JavaScript代码文件 - 需要添加中文注释

### Frontend项目 (frontend/src)

#### 页面组件 (frontend/src/pages)
1. `frontend/src/pages/Dashboard.tsx` - 仪表板页面（React版本）
2. `frontend/src/pages/Dashboard.vue` - 仪表板页面（Vue版本）
3. `frontend/src/pages/DataImport.vue` - 数据导入页面
4. `frontend/src/pages/DataList.vue` - 数据列表页面
5. `frontend/src/pages/DataManagement.tsx` - 数据管理页面
6. `frontend/src/pages/Login.vue` - 登录页面
7. `frontend/src/pages/LoginPage.tsx` - 登录页面（React版本）
8. `frontend/src/pages/ModelManagement.tsx` - 模型管理页面
9. `frontend/src/pages/Models.vue` - 模型页面
10. `frontend/src/pages/Monitor.vue` - 监控页面
11. `frontend/src/pages/QAInterface.tsx` - 问答界面
12. `frontend/src/pages/SystemSettings.tsx` - 系统设置页面
13. `frontend/src/pages/Tasks.vue` - 任务页面
14. `frontend/src/pages/TrainingManagement.tsx` - 训练管理页面
15. `frontend/src/pages/UserManagement.tsx` - 用户管理页面

#### 组件 (frontend/src/components)
16. `frontend/src/components/Layout.vue` - 布局组件
17. `frontend/src/components/Layout/DashboardLayout.tsx` - 仪表板布局

#### 服务 (frontend/src/services)
18. `frontend/src/services/api.ts` - API服务（HTTP请求、拦截器）⚠️ 已有部分注释

#### Redux状态管理 (frontend/src/store)
19. `frontend/src/store/index.ts` - Redux store配置
20. `frontend/src/store/slices/authSlice.ts` - 认证状态切片
21. `frontend/src/store/slices/dataSlice.ts` - 数据状态切片
22. `frontend/src/store/slices/modelSlice.ts` - 模型状态切片
23. `frontend/src/store/slices/qaSlice.ts` - 问答状态切片
24. `frontend/src/store/slices/trainingSlice.ts` - 训练状态切片

#### 自定义Hooks (frontend/src/hooks)
25. `frontend/src/hooks/redux.ts` - Redux hooks

#### 其他文件
26. `frontend/src/App.tsx` - 应用主组件（路由配置）⚠️ 已有部分注释
27. `frontend/src/App.vue` - 应用主组件（Vue版本）
28. `frontend/src/main.ts` - 应用入口
29. `frontend/src/index.tsx` - 应用入口（React版本）

---

## 📚 Markdown文档文件 - 需要翻译成中文

### 高优先级（直接影响用户使用）

1. **mvp/docs/API_GUIDE.md**
   - 当前语言：英文
   - 内容：API端点说明、请求/响应格式、认证方式、错误处理、使用示例
   - 预计工作量：2-3小时
   - 用户群体：开发者、集成商

2. **mvp/docs/DEPLOYMENT.md**
   - 当前语言：英文
   - 内容：部署前置条件、环境配置、数据库初始化、服务启动、监控和日志
   - 预计工作量：1-2小时
   - 用户群体：运维人员、系统管理员

3. **mvp/USER_ACCEPTANCE_TEST_GUIDE.md**
   - 当前语言：英文
   - 内容：测试场景、测试步骤、预期结果、故障排查
   - 预计工作量：2-3小时
   - 用户群体：测试人员、用户

### 中优先级（项目管理和参考）

4. **mvp/CHECKPOINT_13_REPORT.md**
   - 当前语言：英文
   - 内容：功能验证报告、模块导入验证、API端点验证、测试基础设施验证
   - 预计工作量：2-3小时
   - 用户群体：项目经理、技术负责人

5. **mvp/FINAL_CHECKPOINT_REPORT.md**
   - 当前语言：英文
   - 内容：最终系统验证、完成情况总结、建议
   - 预计工作量：2-3小时
   - 用户群体：项目经理、技术负责人

6. **mvp/TASK_15_COMPLETION_SUMMARY.md**
   - 当前语言：中英混合
   - 内容：任务完成情况、验证脚本、测试指南
   - 预计工作量：1-2小时
   - 用户群体：项目团队

### 低优先级（历史记录）

7. **mvp/CHECKPOINT_7_SUMMARY.md**
   - 当前语言：英文
   - 预计工作量：1小时

8. **mvp/TASK_9_SUMMARY.md**
   - 当前语言：英文
   - 预计工作量：1小时

9. **mvp/TASK_10_SUMMARY.md**
   - 当前语言：英文
   - 预计工作量：1小时

### 其他文档（需要检查）

10. **README.md** (项目根目录)
    - 当前语言：需要检查
    - 预计工作量：取决于内容

11. **QUICKSTART.md**
    - 当前语言：需要检查
    - 预计工作量：取决于内容

12. **.kiro/specs/bank-code-retrieval/tasks.md**
    - 当前语言：中文
    - 状态：已有中文，无需翻译

---

## 🗑️ 临时文件和无用文件 - 可以删除

### 测试数据库文件 (6个)
1. `mvp/test_admin.db` - 测试数据库
2. `mvp/test_data_upload.db` - 测试数据库
3. `mvp/test_models.db` - 测试数据库
4. `mvp/test_preview_properties.db` - 测试数据库
5. `mvp/test_validation_properties.db` - 测试数据库
6. `mvp/final_checkpoint_results.json` - 检查点结果文件

### 日志文件 (7个)
7. `mvp/logs/app_2026-01-08.log` - 应用日志
8. `mvp/logs/app_2026-01-09.log` - 应用日志
9. `mvp/logs/app_2026-01-10.log` - 应用日志
10. `mvp/logs/error_2026-01-08.log` - 错误日志
11. `mvp/logs/error_2026-01-09.log` - 错误日志
12. `mvp/logs/error_2026-01-10.log` - 错误日志
13. `mvp/final_checkpoint_output.log` - 检查点输出日志

### 测试脚本和文件 (2个)
14. `mvp/test_auth_manual.py` - 手动测试脚本
15. `mvp/uploads/test_data_test_data.csv` - 测试上传文件

### 缓存目录 (2个)
16. `mvp/.hypothesis/` - Hypothesis测试缓存目录
17. `mvp/.pytest_cache/` - Pytest缓存目录

---

## ✅ 需要保留的文件

### 配置文件
- `mvp/.env` - 环境变量（生产配置）
- `mvp/.env.example` - 环境变量模板
- `mvp/.gitignore` - Git忽略文件
- `mvp/pytest.ini` - Pytest配置
- `mvp/requirements.txt` - Python依赖列表
- `backend/requirements.txt` - 后端依赖列表
- `frontend/package.json` - 前端依赖列表

### 数据文件
- `mvp/data/bank_code.db` - 生产数据库（重要！）

### 脚本文件
- `mvp/scripts/init_db.py` - 数据库初始化脚本
- `mvp/scripts/start.sh` - 启动脚本
- `mvp/scripts/stop.sh` - 停止脚本
- `mvp/run_checkpoint_tests.sh` - 测试脚本

### 验证脚本
- `mvp/checkpoint_13_verification.py` - 检查点13验证脚本
- `mvp/final_checkpoint_verification.py` - 最终检查点验证脚本

### 文档文件
- `mvp/README.md` - 项目README（已有中文）
- `mvp/docs/API_GUIDE.md` - API指南（需翻译）
- `mvp/docs/DEPLOYMENT.md` - 部署文档（需翻译）
- 所有其他.md文档文件

---

## 📊 统计总结

### 代码文件
- **Python文件**: 76个（mvp: 43, backend: 33）
- **TypeScript/JavaScript文件**: 29个（frontend）
- **总计**: 105个代码文件需要添加中文注释

### 文档文件
- **Markdown文件**: 12个
- **需要翻译**: 9个
- **已有中文**: 3个

### 临时文件
- **可删除文件**: 15个
- **可删除目录**: 2个
- **预计释放空间**: 50-100MB

### 工作量估计
- **代码注释**: 40-50小时
- **文档翻译**: 15-20小时
- **文件清理**: 1-2小时
- **总计**: 56-72小时（约1.5-2周）

---

## 🎯 建议的实施顺序

### 第1阶段：核心业务逻辑注释（第1-2天）
1. mvp/app/services/ - 业务服务（8个文件）
2. mvp/app/core/ - 核心模块（10个文件）

### 第2阶段：数据模型和API注释（第3-4天）
1. mvp/app/models/ - 数据模型（8个文件）
2. mvp/app/api/ - API路由（10个文件）
3. mvp/app/schemas/ - 数据验证（5个文件）

### 第3阶段：后端代码注释（第5天）
1. backend/app/ - 所有后端代码（33个文件）

### 第4阶段：前端代码注释（第6-7天）
1. frontend/src/services/ - API服务（1个文件）
2. frontend/src/store/ - 状态管理（6个文件）
3. frontend/src/pages/ - 页面组件（15个文件）
4. frontend/src/components/ - 组件（2个文件）

### 第5阶段：文档翻译（第8-10天）
1. 高优先级文档（3个）
2. 中优先级文档（3个）
3. 低优先级文档（3个）

### 第6阶段：文件清理和验证（第11-12天）
1. 删除临时文件
2. 清理缓存目录
3. 验证所有更改

---

**最后更新**: 2026-01-11
