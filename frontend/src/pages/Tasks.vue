<template>
  <div class="tasks-container">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-button type="default" @click="$router.push('/dashboard')" class="back-button">
              <el-icon><ArrowLeft /></el-icon>
              返回首页
            </el-button>
            <span>训练任务</span>
          </div>
          <el-button type="primary" @click="handleCreateTask">
            <el-icon><Plus /></el-icon>
            创建任务
          </el-button>
        </div>
      </template>
      
      <el-row :gutter="20" style="margin-bottom: 16px;">
        <el-col :xs="24" :sm="12" :md="8">
          <el-input
            v-model="searchQuery"
            placeholder="搜索任务名称"
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
          <el-select v-model="taskStatus" placeholder="选择任务状态" clearable>
            <el-option label="全部" value="" />
            <el-option label="等待中" value="waiting" />
            <el-option label="运行中" value="running" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
            <el-option label="已暂停" value="paused" />
          </el-select>
        </el-col>
        <el-col :xs="24" :sm="12" :md="8">
          <el-select v-model="modelId" placeholder="选择模型" clearable>
            <el-option label="全部" value="" />
            <el-option label="客户分类模型" value="1" />
            <el-option label="交易预测模型" value="2" />
            <el-option label="用户聚类模型" value="3" />
          </el-select>
        </el-col>
      </el-row>
      
      <el-table :data="tasks" stripe style="width: 100%">
        <el-table-column type="index" label="序号" width="80" />
        <el-table-column prop="name" label="任务名称" width="200" />
        <el-table-column prop="modelName" label="所属模型" width="180" />
        <el-table-column prop="dataName" label="使用数据" width="180" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="scope">
            <el-tag :type="getStatusTagType(scope.row.status)">
              {{ scope.row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="progress" label="进度" width="160">
          <template #default="scope">
            <el-progress
              :percentage="scope.row.progress"
              :stroke-width="8"
              :color="[
                {
                  color: '#FFEC3D',
                  percentage: 0
                },
                {
                  color: '#67C23A',
                  percentage: 100
                }
              ]"
            />
          </template>
        </el-table-column>
        <el-table-column prop="startTime" label="开始时间" width="180" />
        <el-table-column prop="endTime" label="结束时间" width="180" />
        <el-table-column prop="duration" label="耗时" width="120" />
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="scope">
            <el-button type="primary" size="small" @click="handleView(scope.row)">
              查看
            </el-button>
            <el-button v-if="scope.row.status === 'waiting'" type="success" size="small" @click="handleStart(scope.row)">
              开始
            </el-button>
            <el-button v-if="scope.row.status === 'running'" type="warning" size="small" @click="handlePause(scope.row)">
              暂停
            </el-button>
            <el-button v-if="scope.row.status === 'paused'" type="success" size="small" @click="handleResume(scope.row)">
              继续
            </el-button>
            <el-button type="danger" size="small" @click="handleCancel(scope.row)">
              取消
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
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
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Plus, Search, ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const searchQuery = ref('')
const taskStatus = ref('')
const modelId = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(30)

const tasks = ref([
  { id: 1, name: '客户分类模型训练任务', modelName: '客户分类模型', dataName: '客户数据集合', status: 'completed', progress: 100, startTime: '2026-01-06 14:30', endTime: '2026-01-06 15:45', duration: '1h 15m' },
  { id: 2, name: '交易预测模型训练任务', modelName: '交易预测模型', dataName: '交易记录数据', status: 'completed', progress: 100, startTime: '2026-01-05 13:20', endTime: '2026-01-05 16:10', duration: '2h 50m' },
  { id: 3, name: '用户聚类模型训练任务', modelName: '用户聚类模型', dataName: '用户行为日志', status: 'running', progress: 75, startTime: '2026-01-04 11:10', endTime: '', duration: '2h 45m' },
  { id: 4, name: '产品推荐模型训练任务', modelName: '产品推荐模型', dataName: '交易记录数据', status: 'waiting', progress: 0, startTime: '', endTime: '', duration: '' },
  { id: 5, name: '欺诈检测模型训练任务', modelName: '欺诈检测模型', dataName: '交易记录数据', status: 'failed', progress: 65, startTime: '2026-01-03 16:45', endTime: '2026-01-03 18:30', duration: '1h 45m' },
])

const getStatusTagType = (status: string) => {
  switch (status) {
    case 'completed':
      return 'success'
    case 'running':
      return 'primary'
    case 'waiting':
      return 'warning'
    case 'paused':
      return 'info'
    case 'failed':
      return 'danger'
    default:
      return 'default'
  }
}

const handleSearch = () => {
  ElMessage.info('搜索功能开发中')
}

const handleCreateTask = () => {
  ElMessage.info('创建任务功能开发中')
}

const handleView = (row: any) => {
  ElMessage.info(`查看任务: ${row.name}`)
}

const handleStart = (row: any) => {
  ElMessage.info(`开始任务: ${row.name}`)
}

const handlePause = (row: any) => {
  ElMessage.info(`暂停任务: ${row.name}`)
}

const handleResume = (row: any) => {
  ElMessage.info(`继续任务: ${row.name}`)
}

const handleCancel = (row: any) => {
  ElMessage.info(`取消任务: ${row.name}`)
}

const handleSizeChange = (size: number) => {
  pageSize.value = size
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page
}
</script>

<style scoped>
.tasks-container {
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

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>