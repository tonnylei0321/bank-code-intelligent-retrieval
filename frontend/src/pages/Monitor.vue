<template>
  <div class="monitor-container">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-button type="default" @click="$router.push('/dashboard')" class="back-button">
              <el-icon><ArrowLeft /></el-icon>
              返回首页
            </el-button>
            <span>系统监控</span>
          </div>
        </div>
      </template>
      
      <el-row :gutter="20" style="margin-bottom: 20px;">
        <el-col :xs="24" :sm="12" :md="6">
          <div class="monitor-card">
            <h3>CPU使用率</h3>
            <div class="monitor-value">{{ cpuUsage }}%</div>
            <el-progress
              :percentage="cpuUsage"
              :stroke-width="10"
              :color="cpuUsage > 80 ? '#F56C6C' : cpuUsage > 60 ? '#E6A23C' : '#67C23A'"
            />
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <div class="monitor-card">
            <h3>内存使用率</h3>
            <div class="monitor-value">{{ memoryUsage }}%</div>
            <el-progress
              :percentage="memoryUsage"
              :stroke-width="10"
              :color="memoryUsage > 80 ? '#F56C6C' : memoryUsage > 60 ? '#E6A23C' : '#67C23A'"
            />
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <div class="monitor-card">
            <h3>磁盘使用率</h3>
            <div class="monitor-value">{{ diskUsage }}%</div>
            <el-progress
              :percentage="diskUsage"
              :stroke-width="10"
              :color="diskUsage > 80 ? '#F56C6C' : diskUsage > 60 ? '#E6A23C' : '#67C23A'"
            />
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <div class="monitor-card">
            <h3>网络流量</h3>
            <div class="monitor-value">{{ networkTraffic }}</div>
            <el-progress
              :percentage="networkProgress"
              :stroke-width="10"
              :color="networkProgress > 80 ? '#F56C6C' : networkProgress > 60 ? '#E6A23C' : '#67C23A'"
            />
          </div>
        </el-col>
      </el-row>
      
      <el-row :gutter="20" style="margin-bottom: 20px;">
        <el-col :xs="24" :md="12">
          <el-card shadow="hover">
            <template #header>
              <div class="card-header">
                <span>服务状态</span>
              </div>
            </template>
            <el-table :data="services" stripe style="width: 100%">
              <el-table-column prop="name" label="服务名称" width="200" />
              <el-table-column prop="status" label="状态" width="120">
                <template #default="scope">
                  <el-tag :type="scope.row.status === 'running' ? 'success' : 'danger'">
                    {{ scope.row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="port" label="端口" width="100" />
              <el-table-column prop="responseTime" label="响应时间" width="120">
                <template #default="scope">
                  <el-tag :type="scope.row.responseTime < 100 ? 'success' : scope.row.responseTime < 500 ? 'warning' : 'danger'">
                    {{ scope.row.responseTime }}ms
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="lastCheck" label="最后检查" width="180" />
            </el-table>
          </el-card>
        </el-col>
        <el-col :xs="24" :md="12">
          <el-card shadow="hover">
            <template #header>
              <div class="card-header">
                <span>数据库状态</span>
              </div>
            </template>
            <el-table :data="databases" stripe style="width: 100%">
              <el-table-column prop="name" label="数据库名称" width="200" />
              <el-table-column prop="status" label="状态" width="120">
                <template #default="scope">
                  <el-tag :type="scope.row.status === 'connected' ? 'success' : 'danger'">
                    {{ scope.row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="type" label="类型" width="120" />
              <el-table-column prop="tables" label="表数量" width="100" />
              <el-table-column prop="size" label="大小" width="120" />
              <el-table-column prop="lastBackup" label="最后备份" width="180" />
            </el-table>
          </el-card>
        </el-col>
      </el-row>
      
      <el-card shadow="hover">
        <template #header>
          <div class="card-header">
            <span>系统日志</span>
          </div>
        </template>
        <el-tabs v-model="activeLogTab" type="border-card">
          <el-tab-pane label="错误日志" name="error">
            <div class="log-container">
              <div v-for="(log, index) in errorLogs" :key="index" class="log-item error">
                <span class="log-time">{{ log.time }}</span>
                <span class="log-level">ERROR</span>
                <span class="log-message">{{ log.message }}</span>
              </div>
            </div>
          </el-tab-pane>
          <el-tab-pane label="警告日志" name="warning">
            <div class="log-container">
              <div v-for="(log, index) in warningLogs" :key="index" class="log-item warning">
                <span class="log-time">{{ log.time }}</span>
                <span class="log-level">WARNING</span>
                <span class="log-message">{{ log.message }}</span>
              </div>
            </div>
          </el-tab-pane>
          <el-tab-pane label="信息日志" name="info">
            <div class="log-container">
              <div v-for="(log, index) in infoLogs" :key="index" class="log-item info">
                <span class="log-time">{{ log.time }}</span>
                <span class="log-level">INFO</span>
                <span class="log-message">{{ log.message }}</span>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ArrowLeft } from '@element-plus/icons-vue'

const cpuUsage = ref(45)
const memoryUsage = ref(60)
const diskUsage = ref(75)
const networkTraffic = ref('1.2 MB/s')
const networkProgress = ref(55)
const activeLogTab = ref('error')

const services = ref([
  { id: 1, name: 'API服务', status: 'running', port: 8000, responseTime: 15, lastCheck: '2026-01-06 14:30' },
  { id: 2, name: '前端服务', status: 'running', port: 3000, responseTime: 8, lastCheck: '2026-01-06 14:30' },
  { id: 3, name: '定时任务', status: 'running', port: '', responseTime: 25, lastCheck: '2026-01-06 14:30' },
  { id: 4, name: '缓存服务', status: 'running', port: 6379, responseTime: 5, lastCheck: '2026-01-06 14:30' },
])

const databases = ref([
  { id: 1, name: 'smp.db', status: 'connected', type: 'SQLite', tables: 10, size: '500 MB', lastBackup: '2026-01-05 23:00' },
  { id: 2, name: 'smp_platform.db', status: 'connected', type: 'SQLite', tables: 5, size: '200 MB', lastBackup: '2026-01-05 23:00' },
])

const errorLogs = ref([
  { time: '2026-01-06 14:30:15', level: 'ERROR', message: 'API请求超时: /api/v1/tasks/123' },
  { time: '2026-01-06 14:25:30', level: 'ERROR', message: '数据库连接失败: Connection refused' },
  { time: '2026-01-06 14:20:45', level: 'ERROR', message: '文件上传失败: File too large' },
])

const warningLogs = ref([
  { time: '2026-01-06 14:35:20', level: 'WARNING', message: '内存使用率超过60%' },
  { time: '2026-01-06 14:32:10', level: 'WARNING', message: 'API请求响应时间过长' },
  { time: '2026-01-06 14:28:55', level: 'WARNING', message: '磁盘空间不足' },
])

const infoLogs = ref([
  { time: '2026-01-06 14:36:05', level: 'INFO', message: '用户登录成功: admin' },
  { time: '2026-01-06 14:34:40', level: 'INFO', message: '任务创建成功: 模型训练任务1' },
  { time: '2026-01-06 14:33:25', level: 'INFO', message: '数据导入完成: 客户数据.csv' },
])

onMounted(() => {
  // 模拟数据更新
  const updateMetrics = () => {
    cpuUsage.value = Math.floor(Math.random() * 20) + 40
    memoryUsage.value = Math.floor(Math.random() * 20) + 50
    diskUsage.value = Math.floor(Math.random() * 10) + 70
    networkProgress.value = Math.floor(Math.random() * 30) + 40
  }
  
  setInterval(updateMetrics, 5000)
})
</script>

<style scoped>
.monitor-container {
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

.monitor-card {
  padding: 20px;
  background-color: #f5f7fa;
  border-radius: 8px;
  text-align: center;
}

.monitor-card h3 {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: #666;
}

.monitor-value {
  font-size: 36px;
  font-weight: bold;
  margin-bottom: 12px;
  color: #333;
}

.log-container {
  max-height: 300px;
  overflow-y: auto;
  padding: 16px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.log-item {
  padding: 8px 12px;
  margin-bottom: 8px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 14px;
  line-height: 1.5;
}

.log-item.error {
  background-color: rgba(245, 108, 108, 0.1);
  border-left: 4px solid #f56c6c;
}

.log-item.warning {
  background-color: rgba(230, 162, 60, 0.1);
  border-left: 4px solid #e6a23c;
}

.log-item.info {
  background-color: rgba(64, 158, 255, 0.1);
  border-left: 4px solid #409eff;
}

.log-time {
  color: #909399;
  margin-right: 12px;
}

.log-level {
  font-weight: bold;
  margin-right: 12px;
}

.log-item.error .log-level {
  color: #f56c6c;
}

.log-item.warning .log-level {
  color: #e6a23c;
}

.log-item.info .log-level {
  color: #409eff;
}

.log-message {
  color: #333;
}
</style>