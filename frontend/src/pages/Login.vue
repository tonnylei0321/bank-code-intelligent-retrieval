<template>
  <div class="login-container">
    <el-card class="login-card" shadow="hover">
      <template #header>
        <div class="login-header">
          <h2>智能管理平台</h2>
          <p>请登录您的账户</p>
        </div>
      </template>
      
      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        label-position="top"
        class="login-form"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            size="large"
            prefix-icon="User"
          />
        </el-form-item>
        
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            @click="handleLogin"
            :loading="loading"
            block
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, FormInstance, FormRules } from 'element-plus'
import AuthService from '@/api/auth'

const router = useRouter()
const loginFormRef = ref<FormInstance | null>(null)
const loading = ref(false)

const loginForm = reactive({
  username: 'admin',
  password: 'Admin@123456'
})

const loginRules = reactive<FormRules>({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在 3 到 20 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于 6 个字符', trigger: 'blur' }
  ]
})

const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  try {
    await loginFormRef.value.validate()
    loading.value = true
    
    const response = await AuthService.login(loginForm)
    AuthService.saveAuthInfo(response)
    
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch (error: any) {
    console.error('登录失败:', error)
    
    if (error.response?.data?.message) {
      ElMessage.error(error.response.data.message)
    } else if (error.response?.status === 401) {
      ElMessage.error('用户名或密码错误')
    } else {
      ElMessage.error('登录失败，请稍后重试')
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 400px;
  border-radius: 12px;
  overflow: hidden;
}

.login-header {
  text-align: center;
}

.login-header h2 {
  margin: 0;
  color: #333;
  font-size: 24px;
}

.login-header p {
  margin: 8px 0 0;
  color: #666;
  font-size: 14px;
}

.login-form {
  padding: 24px;
}
</style>