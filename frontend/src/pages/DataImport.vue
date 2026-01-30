<template>
  <div class="data-import-container">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-button type="default" @click="$router.push('/dashboard')" class="back-button">
              <el-icon><ArrowLeft /></el-icon>
              返回首页
            </el-button>
            <span>数据导入</span>
          </div>
        </div>
      </template>
      
      <el-upload
        class="upload-demo"
        drag
        action=""
        :before-upload="handleBeforeUpload"
        :on-success="handleSuccess"
        :on-error="handleError"
        multiple
        :file-list="fileList"
        :auto-upload="false"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip text-center">
            支持上传 CSV, JSON, Excel 文件，单个文件不超过 100MB
          </div>
        </template>
      </el-upload>
      
      <el-row :gutter="20" style="margin-top: 24px;">
        <el-col :xs="24" :sm="12" :md="8">
          <el-form-item label="数据类型">
            <el-select v-model="dataType" placeholder="选择数据类型" required>
              <el-option label="结构化数据" value="structured" />
              <el-option label="非结构化数据" value="unstructured" />
              <el-option label="半结构化数据" value="semi-structured" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :xs="24" :sm="12" :md="8">
          <el-form-item label="数据名称">
            <el-input v-model="dataName" placeholder="请输入数据名称" required />
          </el-form-item>
        </el-col>
        <el-col :xs="24" :sm="12" :md="8">
          <el-form-item label="数据来源">
            <el-input v-model="dataSource" placeholder="请输入数据来源" />
          </el-form-item>
        </el-col>
      </el-row>
      
      <el-form-item label="数据描述">
        <el-input
          v-model="dataDescription"
          type="textarea"
          :rows="4"
          placeholder="请输入数据描述"
        />
      </el-form-item>
      
      <el-form-item label="导入策略">
        <el-radio-group v-model="importStrategy">
          <el-radio label="覆盖现有数据">覆盖现有数据</el-radio>
          <el-radio label="追加到现有数据">追加到现有数据</el-radio>
          <el-radio label="跳过重复数据">跳过重复数据</el-radio>
        </el-radio-group>
      </el-form-item>
      
      <div class="button-group">
        <el-button type="primary" @click="handleUpload">开始导入</el-button>
        <el-button @click="handleReset">重置</el-button>
      </div>
      
      <el-divider />
      
      <div class="import-history">
        <h3>导入历史</h3>
        <el-timeline>
          <el-timeline-item
            v-for="(item, index) in importHistory"
            :key="index"
            :timestamp="item.time"
            :type="item.status === 'success' ? 'success' : item.status === 'error' ? 'danger' : 'warning'"
          >
            <div class="timeline-content">
              <h4>{{ item.filename }}</h4>
              <p>{{ item.message }}</p>
              <el-tag :type="item.status === 'success' ? 'success' : item.status === 'error' ? 'danger' : 'warning'">
                {{ item.status }}
              </el-tag>
            </div>
          </el-timeline-item>
        </el-timeline>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { UploadFilled, ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const fileList = ref([])
const dataType = ref('structured')
const dataName = ref('')
const dataSource = ref('')
const dataDescription = ref('')
const importStrategy = ref('覆盖现有数据')

const importHistory = ref([
  { filename: '客户数据.csv', time: '2026-01-06 14:30', status: 'success', message: '导入成功，共导入 500000 条记录' },
  { filename: '交易记录.xlsx', time: '2026-01-05 13:20', status: 'success', message: '导入成功，共导入 1200000 条记录' },
  { filename: '用户行为日志.json', time: '2026-01-04 11:10', status: 'warning', message: '导入部分成功，跳过 100 条重复记录' },
])

const handleBeforeUpload = (file: any) => {
  const fileSize = file.size / 1024 / 1024
  if (fileSize > 100) {
    ElMessage.error('文件大小不能超过 100MB')
    return false
  }
  return true
}

const handleUpload = () => {
  if (!dataName.value) {
    ElMessage.error('请输入数据名称')
    return
  }
  if (fileList.value.length === 0) {
    ElMessage.error('请选择要上传的文件')
    return
  }
  
  ElMessage.success('数据导入已开始，请耐心等待')
}

const handleSuccess = (_response: any, file: any) => {
  ElMessage.success(`文件 ${file.name} 导入成功`)
}

const handleError = (_error: any, file: any) => {
  ElMessage.error(`文件 ${file.name} 导入失败`)
}

const handleReset = () => {
  fileList.value = []
  dataType.value = 'structured'
  dataName.value = ''
  dataSource.value = ''
  dataDescription.value = ''
  importStrategy.value = '覆盖现有数据'
}
</script>

<style scoped>
.data-import-container {
  padding: 20px;
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

.button-group {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

.import-history {
  margin-top: 24px;
}

.import-history h3 {
  margin-bottom: 16px;
  font-size: 18px;
  color: #333;
}

.timeline-content {
  padding: 8px 16px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.timeline-content h4 {
  margin: 0 0 8px 0;
  font-size: 16px;
  color: #333;
}

.timeline-content p {
  margin: 0 0 8px 0;
  color: #666;
}
</style>