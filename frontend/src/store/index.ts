/**
 * Redux Store配置文件
 * 
 * 使用Redux Toolkit配置全局状态管理store，集中管理应用的所有状态。
 * 
 * 状态模块（Slices）：
 * - auth: 用户认证状态（登录信息、令牌等）
 * - data: 数据管理状态（数据集列表、上传状态等）
 * - training: 训练管理状态（训练任务、进度等）
 * - model: 模型管理状态（模型列表、部署状态等）
 * - qa: 问答服务状态（会话、历史记录等）
 * 
 * Redux Toolkit特性：
 * - 简化的store配置
 * - 内置Immer用于不可变更新
 * - 集成Redux DevTools
 * - 默认的中间件配置
 * 
 * 使用示例：
 *   import { useSelector, useDispatch } from 'react-redux';
 *   import type { RootState, AppDispatch } from './store';
 *   
 *   const user = useSelector((state: RootState) => state.auth.user);
 *   const dispatch = useDispatch<AppDispatch>();
 */

import { configureStore } from '@reduxjs/toolkit';
import authSlice from './slices/authSlice';
import dataSlice from './slices/dataSlice';
import trainingSlice from './slices/trainingSlice';
import modelSlice from './slices/modelSlice';
import qaSlice from './slices/qaSlice';

// 配置Redux store
export const store = configureStore({
  // 注册所有reducer
  reducer: {
    auth: authSlice,           // 认证状态
    data: dataSlice,           // 数据管理状态
    training: trainingSlice,   // 训练管理状态
    model: modelSlice,         // 模型管理状态
    qa: qaSlice,               // 问答服务状态
  },
  // 配置中间件
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      // 序列化检查配置
      serializableCheck: {
        // 忽略redux-persist的PERSIST action
        ignoredActions: ['persist/PERSIST'],
      },
    }),
});

// 导出类型定义，用于TypeScript类型推断
export type RootState = ReturnType<typeof store.getState>;  // 根状态类型
export type AppDispatch = typeof store.dispatch;             // Dispatch类型