/**
 * 应用程序主入口文件
 * 
 * 负责初始化Vue应用并配置全局插件：
 * - Vue 3: 渐进式JavaScript框架
 * - Element Plus: 基于Vue 3的UI组件库
 * - Vue Router: 官方路由管理器
 * 
 * 应用启动流程：
 * 1. 创建Vue应用实例
 * 2. 注册Element Plus UI组件库
 * 3. 注册Vue Router路由
 * 4. 挂载应用到DOM节点#app
 */

import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'

// 创建Vue应用实例
const app = createApp(App)

// 注册Element Plus UI组件库
app.use(ElementPlus)

// 注册路由
app.use(router)

// 挂载应用到DOM
app.mount('#app')