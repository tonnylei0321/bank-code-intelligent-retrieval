<template>
  <div class="dashboard-container">
    <el-container>
      <el-header class="dashboard-header">
        <div class="header-left">
          <h1>SynapseAI Platform 突触智联平台</h1>
        </div>
        <div class="header-right">
          <el-dropdown>
            <span class="user-info">
              <el-avatar :size="40" :src="userAvatar"></el-avatar>
              <span>{{ currentUser?.username || '用户' }}</span>
              <el-icon class="el-icon--right"><arrow-down /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item>
                  <el-icon><user /></el-icon>
                  个人中心
                </el-dropdown-item>
                <el-dropdown-item>
                  <el-icon><setting /></el-icon>
                  设置
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">
                  <el-icon><switch-button /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <el-container>
        <el-aside width="200px" class="dashboard-aside">
          <el-menu
            :default-active="activeMenu"
            class="el-menu-vertical"
            background-color="#545c64"
            text-color="#fff"
            active-text-color="#ffd04b"
            @select="handleMenuSelect"
          >
            <el-menu-item index="dashboard">
              <el-icon><data-analysis /></el-icon>
              <span>仪表盘</span>
            </el-menu-item>
            <el-sub-menu index="2">
              <template #title>
                <el-icon><collection /></el-icon>
                <span>数据管理</span>
              </template>
              <el-menu-item index="data-list">数据列表</el-menu-item>
              <el-menu-item index="data-import">数据导入</el-menu-item>
            </el-sub-menu>
            <el-menu-item index="models">
              <el-icon><cpu /></el-icon>
              <span>模型管理</span>
            </el-menu-item>
            <el-menu-item index="tasks">
              <el-icon><calendar /></el-icon>
              <span>训练任务</span>
            </el-menu-item>
            <el-menu-item index="monitor">
              <el-icon><monitor /></el-icon>
              <span>系统监控</span>
            </el-menu-item>
          </el-menu>
        </el-aside>
        
        <el-main class="dashboard-main">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowDown, DataAnalysis, Collection, Cpu, Calendar, Monitor, User, Setting, SwitchButton } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()

// 用户信息
const currentUser = ref({ username: 'admin' })
const userAvatar = ref('')

// 当前激活的菜单
const activeMenu = computed(() => {
  const path = route.path
  if (path === '/dashboard') return 'dashboard'
  if (path === '/data/list') return 'data-list'
  if (path === '/data/import') return 'data-import'
  if (path === '/models') return 'models'
  if (path === '/tasks') return 'tasks'
  if (path === '/monitor') return 'monitor'
  return 'dashboard'
})

// 处理菜单选择
const handleMenuSelect = (key: string) => {
  switch (key) {
    case 'dashboard':
      router.push('/dashboard')
      break
    case 'data-list':
      router.push('/data/list')
      break
    case 'data-import':
      router.push('/data/import')
      break
    case 'models':
      router.push('/models')
      break
    case 'tasks':
      router.push('/tasks')
      break
    case 'monitor':
      router.push('/monitor')
      break
  }
}

// 处理退出登录
const handleLogout = () => {
  localStorage.removeItem('access_token')
  router.push('/login')
}

onMounted(() => {
  // 可以在这里加载用户信息
})
</script>

<style scoped>
.dashboard-container {
  width: 100%;
  height: 100vh;
  overflow: hidden;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.header-left h1 {
  margin: 0;
  font-size: 24px;
  color: #333;
}

.user-info {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.user-info:hover {
  background-color: #f5f7fa;
}

.user-info span {
  margin-left: 8px;
  margin-right: 4px;
}

.dashboard-aside {
  background-color: #545c64;
  height: calc(100vh - 60px);
  overflow-y: auto;
}

.dashboard-main {
  padding: 20px;
  overflow-y: auto;
  height: calc(100vh - 60px);
  background-color: #f5f7fa;
}
</style>