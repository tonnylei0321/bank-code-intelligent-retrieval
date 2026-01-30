<template>
  <div class="dashboard-container">
    <el-card shadow="hover" class="stats-card">
      <template #header>
        <div class="card-header">
          <span>系统统计</span>
        </div>
      </template>
      
      <el-row :gutter="20">
        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <div class="stat-item">
            <div class="stat-icon data">
              <el-icon><collection /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">1,234</div>
              <div class="stat-label">数据集</div>
            </div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <div class="stat-item">
            <div class="stat-icon model">
              <el-icon><cpu /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">56</div>
              <div class="stat-label">模型</div>
            </div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <div class="stat-item">
            <div class="stat-icon task">
              <el-icon><calendar /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">23</div>
              <div class="stat-label">训练任务</div>
            </div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <div class="stat-item">
            <div class="stat-icon user">
              <el-icon><user /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">15</div>
              <div class="stat-label">用户</div>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>
    
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :xs="24" :md="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>最近训练任务</span>
            </div>
          </template>
          
          <el-table :data="recentTasks" stripe style="width: 100%">
            <el-table-column prop="name" label="任务名称" />
            <el-table-column prop="status" label="状态">
              <template #default="scope">
                <el-tag
                  :type="scope.row.status === 'success' ? 'success' : scope.row.status === 'error' ? 'danger' : 'warning'"
                >
                  {{ scope.row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="progress" label="进度">
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
            <el-table-column prop="createTime" label="创建时间" />
          </el-table>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :md="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>系统状态</span>
            </div>
          </template>
          
          <el-descriptions :column="1" border>
            <el-descriptions-item label="CPU使用率">
              <el-progress type="dashboard" :percentage="45" :width="80" />
            </el-descriptions-item>
            <el-descriptions-item label="内存使用率">
              <el-progress type="dashboard" :percentage="60" :width="80" />
            </el-descriptions-item>
            <el-descriptions-item label="磁盘使用率">
              <el-progress type="dashboard" :percentage="75" :width="80" />
            </el-descriptions-item>
            <el-descriptions-item label="系统版本">v1.0.0</el-descriptions-item>
            <el-descriptions-item label="运行时间">7 天 12 小时</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { 
  Collection, Cpu, Calendar
} from '@element-plus/icons-vue'

const recentTasks = ref([
  { name: '模型训练任务1', status: 'success', progress: 100, createTime: '2026-01-06 14:30' },
  { name: '模型训练任务2', status: 'error', progress: 60, createTime: '2026-01-06 13:20' },
  { name: '模型训练任务3', status: 'warning', progress: 80, createTime: '2026-01-06 11:10' },
  { name: '模型训练任务4', status: 'success', progress: 100, createTime: '2026-01-05 16:45' },
  { name: '模型训练任务5', status: 'warning', progress: 45, createTime: '2026-01-05 15:30' }
])

onMounted(() => {
  // 可以在这里加载实际的仪表盘数据
})
</script>

<style scoped>
.dashboard-container {
  width: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stats-card {
  margin-bottom: 20px;
}

.stat-item {
  display: flex;
  align-items: center;
  padding: 16px;
  background-color: #f5f7fa;
  border-radius: 8px;
  transition: transform 0.3s, box-shadow 0.3s;
}

.stat-item:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
}

.stat-icon {
  width: 50px;
  height: 50px;
  display: flex;
  justify-content: center;
  align-items: center;
  border-radius: 50%;
  font-size: 24px;
  margin-right: 16px;
  color: #fff;
}

.stat-icon.data {
  background-color: #67c23a;
}

.stat-icon.model {
  background-color: #409eff;
}

.stat-icon.task {
  background-color: #e6a23c;
}

.stat-icon.user {
  background-color: #f56c6c;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #333;
}

.stat-label {
  font-size: 14px;
  color: #666;
  margin-top: 4px;
}
</style>