<template>
  <div class="data-list-container">
    <el-card shadow="hover" class="main-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-button type="default" @click="$router.push('/dashboard')" class="back-button">
              <el-icon><ArrowLeft /></el-icon>
              返回首页
            </el-button>
            <h2 class="page-title">数据列表</h2>
          </div>
          <el-button type="primary" @click="handleAdd" class="add-button">
            <el-icon><Plus /></el-icon>
            新增数据
          </el-button>
        </div>
      </template>
      
      <!-- 搜索和筛选区域 -->
      <div class="filter-section">
        <el-row :gutter="24">
          <el-col :xs="24" :sm="24" :md="12" :lg="8">
            <el-input
              v-model="searchQuery"
              placeholder="搜索数据名称"
              clearable
              @keyup.enter="handleSearch"
              class="search-input"
            >
              <template #prepend>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6" :lg="4">
            <el-select v-model="dataType" placeholder="数据类型" clearable class="filter-select">
              <el-option label="全部" value="" />
              <el-option label="结构化数据" value="structured" />
              <el-option label="非结构化数据" value="unstructured" />
              <el-option label="半结构化数据" value="semi-structured" />
            </el-select>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6" :lg="4">
            <el-select v-model="status" placeholder="状态" clearable class="filter-select">
              <el-option label="全部" value="" />
              <el-option label="已发布" value="published" />
              <el-option label="草稿" value="draft" />
              <el-option label="审核中" value="pending" />
            </el-select>
          </el-col>
          <el-col :xs="24" :sm="24" :md="12" :lg="8" class="action-buttons">
            <el-button @click="handleSearch" class="search-button">
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
            <el-button @click="resetFilters" class="reset-button">
              <el-icon><RefreshRight /></el-icon>
              重置
            </el-button>
          </el-col>
        </el-row>
      </div>
      
      <!-- 卡片列表 -->
      <div class="card-list">
        <el-row :gutter="20">
          <el-col 
            v-for="item in dataList" 
            :key="item.file_id" 
            :xs="24" 
            :sm="12" 
            :md="8" 
            :lg="6"
            :xl="4"
            class="card-item"
          >
          <el-card 
            shadow="hover" 
            class="data-card"
            @click="handleView(item)"
          >
            <div class="card-content">
              <!-- 卡片头部 -->
              <div class="card-header-section">
                <h3 class="data-name">{{ item.file_name }}</h3>
                <el-tag 
                  :type="getStatusTagType(item.status)" 
                  size="small"
                  class="status-tag"
                >
                  {{ item.status === 'published' ? '已发布' : item.status === 'draft' ? '草稿' : item.status === 'pending' ? '审核中' : item.status }}
                </el-tag>
              </div>
              
              <!-- 数据信息 -->
              <div class="data-info">
                <div class="info-item">
                  <span class="info-label">大小：</span>
                  <span class="info-value">{{ formatFileSize(item.file_size) }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">记录数：</span>
                  <span class="info-value">{{ item.record_count.toLocaleString() }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">上传时间：</span>
                  <span class="info-value date">{{ item.upload_time }}</span>
                </div>
                <div class="info-item" v-if="item.parsed_records">
                  <span class="info-label">解析记录：</span>
                  <span class="info-value">{{ item.parsed_records.toLocaleString() }}</span>
                </div>
              </div>
              
              <!-- 操作按钮 -->
              <div class="card-actions">
                <el-button type="primary" size="small" @click.stop="handleView(item)" class="action-btn view-btn">
                  <el-icon><View /></el-icon>
                  查看
                </el-button>
                <el-button type="success" size="small" @click.stop="handleEdit(item)" class="action-btn edit-btn">
                  <el-icon><EditPen /></el-icon>
                  编辑
                </el-button>
                <el-button type="danger" size="small" @click.stop="handleDelete(item)" class="action-btn delete-btn">
                  <el-icon><Delete /></el-icon>
                  删除
                </el-button>
              </div>
            </div>
          </el-card>
        </el-col>
        </el-row>
      </div>
      
      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
          :current-page="currentPage"
          :page-sizes="[12, 24, 36, 48]"
          :page-size="pageSize"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          class="modern-pagination"
        />
      </div>
    </el-card>
  </div>
  
  <!-- 查看数据对话框 -->
  <el-dialog
    v-model="viewDialogVisible"
    title="数据详情"
    width="70%"
    :before-close="() => { viewDialogVisible.value = false }"
  >
    <el-card v-if="currentFile" shadow="never" class="detail-card">
      <div class="detail-content">
        <div class="detail-row">
          <div class="detail-label">文件名称：</div>
          <div class="detail-value">{{ currentFile.file_name }}</div>
        </div>
        <div class="detail-row">
          <div class="detail-label">文件大小：</div>
          <div class="detail-value">{{ formatFileSize(currentFile.file_size) }}</div>
        </div>
        <div class="detail-row">
          <div class="detail-label">记录数：</div>
          <div class="detail-value">{{ currentFile.record_count.toLocaleString() }}</div>
        </div>
        <div class="detail-row" v-if="currentFile.parsed_records">
          <div class="detail-label">解析记录：</div>
          <div class="detail-value">{{ currentFile.parsed_records.toLocaleString() }}</div>
        </div>
        <div class="detail-row">
          <div class="detail-label">状态：</div>
          <div class="detail-value">
            <el-tag :type="getStatusTagType(currentFile.status)">
              {{ currentFile.status === 'published' ? '已发布' : currentFile.status === 'draft' ? '草稿' : currentFile.status === 'pending' ? '审核中' : currentFile.status }}
            </el-tag>
          </div>
        </div>
        <div class="detail-row">
          <div class="detail-label">上传时间：</div>
          <div class="detail-value">{{ currentFile.upload_time }}</div>
        </div>
      </div>
    </el-card>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="viewDialogVisible.value = false">关闭</el-button>
        <el-button type="primary" @click="handleEdit(currentFile!)">编辑</el-button>
      </span>
    </template>
  </el-dialog>
  
  <!-- 编辑数据对话框 -->
  <el-dialog
    v-model="editDialogVisible"
    title="编辑数据"
    width="60%"
    :before-close="() => { editDialogVisible.value = false }"
  >
    <el-form v-if="currentFile" label-position="top" label-width="100px">
      <el-form-item label="文件名称">
        <el-input v-model="currentFile.file_name" placeholder="请输入文件名称" />
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="currentFile.status" placeholder="请选择状态">
          <el-option label="已发布" value="published" />
          <el-option label="草稿" value="draft" />
          <el-option label="审核中" value="pending" />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="editDialogVisible.value = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">保存</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Plus, Search, RefreshRight, View, EditPen, Delete, ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage, ElDialog, ElForm, ElFormItem, ElInput, ElSelect, ElOption, ElButton, ElTable, ElTableColumn, ElMessageBox } from 'element-plus'
import * as dataApi from '../api/data'

const searchQuery = ref('')
const dataType = ref('')
const status = ref('')
const currentPage = ref(1)
const pageSize = ref(12)
const total = ref(0)
const loading = ref(false)

// 使用与后端API匹配的数据结构
const dataList = ref<dataApi.DataFile[]>([])
const currentFile = ref<dataApi.DataFile | null>(null)

// 对话框控制
const viewDialogVisible = ref(false)
const editDialogVisible = ref(false)

const getTypeTagType = (type: string) => {
  switch (type) {
    case 'structured':
      return 'success'
    case 'unstructured':
      return 'warning'
    case 'semi-structured':
      return 'info'
    default:
      return 'default'
  }
}

const getStatusTagType = (status: string) => {
  switch (status) {
    case 'published':
      return 'success'
    case 'draft':
      return 'warning'
    case 'pending':
      return 'info'
    default:
      return 'default'
  }
}

// 获取数据文件列表
const fetchFiles = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      status_filter: status.value || undefined
    }
    const result = await dataApi.getFiles(params)
    dataList.value = result.data
    total.value = result.total
    loading.value = false
  } catch (error) {
    console.error('获取文件列表失败:', error)
    ElMessage.error('获取文件列表失败，请稍后重试')
    loading.value = false
  }
}

// 组件挂载时获取数据
onMounted(() => {
  fetchFiles()
})

const handleSearch = async () => {
  currentPage.value = 1
  await fetchFiles()
  ElMessage.success('搜索完成')
}

const resetFilters = () => {
  searchQuery.value = ''
  dataType.value = ''
  status.value = ''
  currentPage.value = 1
  fetchFiles()
  ElMessage.success('筛选条件已重置')
}

const handleAdd = () => {
  ElMessage.info('新增数据功能开发中')
}

// 查看数据详情
const handleView = async (file: dataApi.DataFile) => {
  try {
    const fileDetail = await dataApi.getFileById(file.file_id)
    currentFile.value = fileDetail
    viewDialogVisible.value = true
  } catch (error) {
    console.error('获取文件详情失败:', error)
    ElMessage.error('获取文件详情失败，请稍后重试')
  }
}

// 编辑数据
const handleEdit = (file: dataApi.DataFile) => {
  currentFile.value = file
  editDialogVisible.value = true
}

// 删除数据
const handleDelete = async (file: dataApi.DataFile) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除文件 "${file.file_name}" 吗？此操作不可恢复。`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const result = await dataApi.deleteFile(file.file_id)
    if (result.deleted) {
      ElMessage.success(`文件 "${file.file_name}" 已成功删除`)
      fetchFiles() // 重新获取文件列表
    } else {
      ElMessage.error(result.message || '删除失败，请稍后重试')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除文件失败:', error)
      ElMessage.error('删除文件失败，请稍后重试')
    }
  }
}

const handleSizeChange = (size: number) => {
  pageSize.value = size
  fetchFiles()
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page
  fetchFiles()
}

// 格式化文件大小
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}
</script>

<style scoped>
.data-list-container {
  padding: 20px;
  min-height: 100vh;
  background-color: #f5f7fa;
}

.main-card {
  border-radius: 12px;
  background-color: #ffffff;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.08);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.back-button {
  margin-right: 12px;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
}

.add-button {
  border-radius: 8px;
  padding: 8px 20px;
  font-weight: 500;
}

/* 筛选区域样式 */
.filter-section {
  margin-bottom: 24px;
  padding: 16px;
  background-color: #f9fafb;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.search-input {
  border-radius: 8px;
  height: 40px;
}

.filter-select {
  border-radius: 8px;
  height: 40px;
  width: 100%;
}

.action-buttons {
  display: flex;
  gap: 12px;
  align-items: center;
}

.search-button, .reset-button {
  border-radius: 8px;
  padding: 8px 20px;
  height: 40px;
  font-weight: 500;
}

/* 卡片列表样式 */
.card-list {
  margin-bottom: 24px;
}

.card-item {
  margin-bottom: 20px;
}

.data-card {
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid #e5e7eb;
  height: 100%;
}

.data-card:hover {
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

.data-name {
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
.data-info {
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
  min-width: 60px;
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

.edit-btn {
  background-color: #10b981;
  border-color: #10b981;
}

.edit-btn:hover {
  background-color: #059669;
  border-color: #059669;
}

.delete-btn {
  background-color: #ef4444;
  border-color: #ef4444;
}

.delete-btn:hover {
  background-color: #dc2626;
  border-color: #dc2626;
}

/* 分页样式 */
.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 24px;
  padding: 16px;
  background-color: #f9fafb;
  border-radius: 8px;
  border-top: 1px solid #e5e7eb;
}

.modern-pagination {
  --el-pagination-font-size: 14px;
  --el-pagination-button-size: 32px;
}

.modern-pagination .el-pagination__sizes .el-input__wrapper {
  border-radius: 6px;
}

.modern-pagination .el-pagination__btn {
  border-radius: 6px;
}

.modern-pagination .el-pager li {
  border-radius: 6px;
  margin: 0 4px;
}

.modern-pagination .el-pager li.is-active {
  background-color: #3b82f6;
  border-color: #3b82f6;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .data-list-container {
    padding: 12px;
  }
  
  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .page-title {
    font-size: 20px;
  }
  
  .add-button {
    width: 100%;
    justify-content: center;
  }
  
  .filter-section {
    padding: 12px;
  }
  
  .action-buttons {
    flex-direction: column;
  }
  
  .search-button, .reset-button {
    width: 100%;
    justify-content: center;
  }
  
  .card-content {
    padding: 12px;
  }
  
  .data-name {
    font-size: 16px;
  }
  
  .card-actions {
    flex-direction: column;
  }
  
  .action-btn {
    width: 100%;
  }
  
  .pagination-container {
    padding: 12px;
  }
  
  .modern-pagination {
    justify-content: center;
  }
}

@media (max-width: 480px) {
  .data-list-container {
    padding: 8px;
  }
  
  .info-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  
  .info-label {
    min-width: auto;
  }
}
</style>