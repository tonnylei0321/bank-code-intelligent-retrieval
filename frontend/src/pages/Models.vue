<template>
  <div class="models-container">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-button type="default" @click="$router.push('/dashboard')" class="back-button">
              <el-icon><ArrowLeft /></el-icon>
              返回首页
            </el-button>
            <span>模型管理</span>
          </div>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            创建模型
          </el-button>
        </div>
      </template>
      
      <el-row :gutter="20" style="margin-bottom: 16px;">
        <el-col :xs="24" :sm="12" :md="8">
          <el-input
            v-model="searchQuery"
            placeholder="搜索模型名称"
            clearable
            @keyup.enter="handleSearch"
          >
            <template #append>
              <el-button @click="handleSearch">
                <el-icon><Search /></el-icon>
              </el-button>
            </template>
          </el-input>
        </el-col>
        <el-col :xs="24" :sm="12" :md="8">
          <el-select v-model="modelTypeFilter" placeholder="选择模型类型" clearable>
            <el-option label="全部" value="" />
            <el-option label="银行检索" value="bank_retrieval" />
            <el-option label="BIC检索" value="bic_retrieval" />
            <el-option label="清算路由" value="settlement_route" />
          </el-select>
        </el-col>
        <el-col :xs="24" :sm="12" :md="8">
          <el-select v-model="modelStatusFilter" placeholder="选择状态" clearable>
            <el-option label="全部" value="" />
            <el-option label="活跃" value="active" />
            <el-option label="草稿" value="draft" />
            <el-option label="训练中" value="training" />
            <el-option label="停用" value="inactive" />
          </el-select>
        </el-col>
      </el-row>
      
      <!-- 卡片列表 -->
      <div class="card-list" v-loading="loading">
        <el-row :gutter="20">
          <el-col 
            v-for="item in models" 
            :key="item.model_id" 
            :xs="24" 
            :sm="12" 
            :md="8" 
            :lg="6"
            :xl="4"
            class="card-item"
          >
            <el-card 
              shadow="hover" 
              class="model-card"
            >
              <div class="card-content">
                <!-- 卡片头部 -->
                <div class="card-header-section">
                  <h3 class="model-name">{{ item.model_name }}</h3>
                  <el-tag 
                    :type="getStatusTagType(item.status)" 
                    size="small"
                    class="status-tag"
                  >
                    {{ modelStatusMap[item.status] || item.status }}
                  </el-tag>
                </div>
                
                <!-- 数据信息 -->
                <div class="model-info">
                  <div class="info-item">
                    <span class="info-label">类型：</span>
                    <el-tag 
                      :type="getTypeTagType(item.model_type)" 
                      size="small"
                      class="type-tag"
                    >
                      {{ modelTypeMap[item.model_type] || item.model_type }}
                    </el-tag>
                  </div>
                  <div class="info-item">
                    <span class="info-label">基础模型：</span>
                    <span class="info-value">{{ item.base_model }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">版本数量：</span>
                    <span class="info-value">{{ item.version_count }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">创建时间：</span>
                    <span class="info-value date">{{ item.created_at }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">更新时间：</span>
                    <span class="info-value date">{{ item.updated_at }}</span>
                  </div>
                </div>
                
                <!-- 操作按钮 -->
                <div class="card-actions">
                  <el-button type="primary" size="small" @click.stop="handleView(item)" class="action-btn view-btn">
                    查看
                  </el-button>
                  <el-button type="success" size="small" @click.stop="handleTrain(item)" class="action-btn train-btn">
                    训练
                  </el-button>
                  <el-button type="warning" size="small" @click.stop="handlePublish(item)" class="action-btn publish-btn">
                    发布
                  </el-button>
                  <el-button type="danger" size="small" @click.stop="handleDelete(item)" class="action-btn delete-btn">
                    删除
                  </el-button>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
      
      <div class="pagination-container">
        <el-pagination
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
          :current-page="currentPage"
          :page-sizes="[10, 20, 50, 100]"
          :page-size="pageSize"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
        />
      </div>
    </el-card>
    
    <!-- 创建模型对话框 -->
    <el-dialog
      v-model="dialogVisible"
      title="创建新模型"
      width="600px"
      @close="resetForm"
    >
      <el-form
        ref="modelFormRef"
        :model="modelForm"
        :rules="formRules"
        label-width="120px"
        style="margin-top: 20px;"
      >
        <el-form-item label="模型名称" prop="model_name">
          <el-input
            v-model="modelForm.model_name"
            placeholder="请输入模型名称"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>
        
        <el-form-item label="模型类型" prop="model_type">
          <el-select
            v-model="modelForm.model_type"
            placeholder="请选择模型类型"
            style="width: 100%;"
          >
            <el-option label="银行检索" value="bank_retrieval" />
            <el-option label="BIC检索" value="bic_retrieval" />
            <el-option label="清算路由" value="settlement_route" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="基础模型" prop="base_model">
          <el-select
            v-model="modelForm.base_model"
            placeholder="请选择基础模型"
            style="width: 100%;"
          >
            <el-option label="Qwen3-0.6B" value="Qwen3-0.6B" />
            <el-option label="Qwen3-1.5B" value="Qwen3-1.5B" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="模型描述" prop="description">
          <el-input
            v-model="modelForm.description"
            placeholder="请输入模型描述"
            type="textarea"
            rows="4"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmit">确定</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Plus, Search, ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import * as modelApi from '../api/models'
import type { ModelInfo, ModelRegisterRequest } from '../api/models'

const searchQuery = ref('')
const modelTypeFilter = ref('')
const modelStatusFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const loading = ref(false)

// 对话框状态
const dialogVisible = ref(false)
const modelFormRef = ref<FormInstance | null>(null)

// 创建模型表单
const modelForm = ref<ModelRegisterRequest>({
  model_name: '',
  model_type: '',
  base_model: '',
  description: ''
})

// 表单验证规则
const formRules = ref({
  model_name: [
    { required: true, message: '请输入模型名称', trigger: 'blur' },
    { min: 1, max: 100, message: '模型名称长度在 1 到 100 个字符', trigger: 'blur' }
  ],
  model_type: [
    { required: true, message: '请选择模型类型', trigger: 'change' }
  ],
  base_model: [
    { required: true, message: '请选择基础模型', trigger: 'change' }
  ],
  description: [
    { max: 500, message: '模型描述长度不能超过 500 个字符', trigger: 'blur' }
  ]
})

// 更新数据模型，使用后端返回的字段结构
const models = ref<ModelInfo[]>([])

// 模型类型映射
const modelTypeMap: Record<string, string> = {
  'bank_retrieval': '银行检索',
  'bic_retrieval': 'BIC检索',
  'settlement_route': '清算路由'
}

// 模型状态映射
const modelStatusMap: Record<string, string> = {
  'active': '活跃',
  'draft': '草稿',
  'training': '训练中',
  'inactive': '停用'
}

const getTypeTagType = (type: string) => {
  switch (type) {
    case 'bank_retrieval':
      return 'success'
    case 'bic_retrieval':
      return 'warning'
    case 'settlement_route':
      return 'info'
    default:
      return 'default'
  }
}

const getStatusTagType = (status: string) => {
  switch (status) {
    case 'active':
      return 'success'
    case 'draft':
      return 'info'
    case 'training':
      return 'warning'
    case 'inactive':
      return 'danger'
    default:
      return 'default'
  }
}

// 获取模型列表
const fetchModels = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      model_type: modelTypeFilter.value || undefined,
      status: modelStatusFilter.value || undefined,
      search: searchQuery.value || undefined
    }
    const data = await modelApi.getModels(params)
    models.value = data
    total.value = data.length // 实际项目中应该从API响应中获取total
    ElMessage.success('获取模型列表成功')
  } catch (error) {
    ElMessage.error('获取模型列表失败')
    console.error('获取模型列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 搜索功能
const handleSearch = () => {
  currentPage.value = 1
  fetchModels()
}

// 查看模型详情
const handleView = async (row: ModelInfo) => {
  try {
    const modelDetail = await modelApi.getModelDetail(row.model_id)
    // 这里可以跳转到模型详情页或显示详情对话框
    ElMessage.success(`查看模型: ${row.model_name}`)
    console.log('模型详情:', modelDetail)
  } catch (error) {
    ElMessage.error('获取模型详情失败')
    console.error('获取模型详情失败:', error)
  }
}

// 训练模型
const handleTrain = async (row: ModelInfo) => {
  try {
    ElMessage.success(`开始训练模型: ${row.model_name}`)
    // 调用实际的训练模型API
    const trainingConfig = {
      training_config: {
        epochs: 10,
        batch_size: 32,
        learning_rate: 0.001
      },
      // 可以根据实际情况提供数据集ID或代码仓库信息
      dataset_id: 1,
      gitee_repo_url: "https://gitee.com/example/model-repo.git",
      gitee_branch: "main"
    }
    const response = await modelApi.trainModel(row.model_id, trainingConfig)
    ElMessage.success(response.message)
    // 显示任务ID，方便用户跟踪
    ElMessage.info(`训练任务ID: ${response.task_id}`)
    // 延迟一段时间后刷新模型列表，因为训练是异步的
    setTimeout(() => {
      fetchModels() // 重新获取模型列表，更新状态
    }, 3000)
  } catch (error) {
    ElMessage.error('训练模型失败')
    console.error('训练模型失败:', error)
  }
}

// 发布模型
const handlePublish = async (row: ModelInfo) => {
  try {
    // 获取最新版本
    const versions = await modelApi.getModelVersions(row.model_id)
    if (versions.versions.length > 0) {
      const latestVersion = versions.versions[0] // 假设第一个是最新版本
      // 调用部署模型API
      await modelApi.deployModel(row.model_id, {
        version_id: latestVersion.version_id
      })
      ElMessage.success(`模型 "${row.model_name}" 发布成功`)
      fetchModels() // 重新获取模型列表，更新状态
    } else {
      ElMessage.warning('该模型没有可用版本，请先训练模型')
    }
  } catch (error) {
    ElMessage.error('发布模型失败')
    console.error('发布模型失败:', error)
  }
}

// 删除模型
const handleDelete = async (row: ModelInfo) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除模型 "${row.model_name}" 吗？此操作不可恢复。`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await modelApi.deleteModel(row.model_id)
    ElMessage.success('模型删除成功')
    // 重新获取模型列表
    fetchModels()
  } catch (error: any) {
    if (error === 'cancel') {
      return
    }
    ElMessage.error('模型删除失败')
    console.error('删除模型失败:', error)
  }
}

// 创建模型
const handleAdd = () => {
  dialogVisible.value = true
}

// 重置表单
const resetForm = () => {
  if (modelFormRef.value) {
    modelFormRef.value.resetFields()
  }
  modelForm.value = {
    model_name: '',
    model_type: '',
    base_model: '',
    description: ''
  }
}

// 提交表单
const handleSubmit = async () => {
  if (!modelFormRef.value) return
  
  try {
    await modelFormRef.value.validate()
    
    const response = await modelApi.registerModel(modelForm.value)
    ElMessage.success('模型创建成功！')
    
    // 关闭对话框
    dialogVisible.value = false
    
    // 重新获取模型列表
    fetchModels()
    
    // 重置表单
    resetForm()
    
    console.log('创建模型成功:', response)
  } catch (error: any) {
    if (error === false) {
      // 表单验证失败
      return
    }
    ElMessage.error('创建模型失败，请稍后重试')
    console.error('创建模型失败:', error)
  }
}

// 分页大小变化
const handleSizeChange = (size: number) => {
  pageSize.value = size
  fetchModels()
}

// 页码变化
const handleCurrentChange = (page: number) => {
  currentPage.value = page
  fetchModels()
}

// 组件挂载时获取模型列表
onMounted(() => {
  fetchModels()
})
</script>

<style scoped>
.models-container {
  padding: 20px;
  min-height: 100vh;
  background-color: #f5f7fa;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.back-button {
  margin-right: 12px;
}

/* 卡片列表样式 */
.card-list {
  margin-bottom: 24px;
}

.card-item {
  margin-bottom: 20px;
}

.model-card {
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid #e5e7eb;
  height: 100%;
}

.model-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  border-color: #3b82f6;
}

.card-content {
  padding: 16px;
}

.card-header-section {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.model-name {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.status-tag {
  margin-top: 4px;
}

/* 数据信息样式 */
.model-info {
  margin-bottom: 20px;
}

.info-item {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  font-size: 14px;
}

.info-label {
  color: #6b7280;
  margin-right: 8px;
  min-width: 80px;
}

.info-value {
  color: #374151;
  font-weight: 500;
}

.info-value.date {
  color: #6b7280;
  font-size: 13px;
}

.type-tag {
  margin: 0;
}

/* 操作按钮样式 */
.card-actions {
  display: flex;
  gap: 8px;
  justify-content: space-between;
}

.action-btn {
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 500;
  flex: 1;
  text-align: center;
}

.view-btn {
  background-color: #3b82f6;
  border-color: #3b82f6;
}

.view-btn:hover {
  background-color: #2563eb;
  border-color: #2563eb;
}

.train-btn {
  background-color: #10b981;
  border-color: #10b981;
}

.train-btn:hover {
  background-color: #059669;
  border-color: #059669;
}

.publish-btn {
  background-color: #f59e0b;
  border-color: #f59e0b;
}

.publish-btn:hover {
  background-color: #d97706;
  border-color: #d97706;
}

.delete-btn {
  background-color: #ef4444;
  border-color: #ef4444;
}

.delete-btn:hover {
  background-color: #dc2626;
  border-color: #dc2626;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 24px;
  padding: 16px;
  background-color: #f9fafb;
  border-radius: 8px;
  border-top: 1px solid #e5e7eb;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .models-container {
    padding: 12px;
  }
  
  .card-actions {
    flex-direction: column;
  }
  
  .action-btn {
    width: 100%;
  }
}
</style>