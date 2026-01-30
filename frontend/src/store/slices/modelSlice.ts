/**
 * 模型管理状态模块（Redux Slice）
 * 
 * 管理AI模型相关的全局状态，包括：
 * - 模型列表
 * - 当前选中的模型
 * - 加载状态和错误信息
 * 
 * 功能特性：
 * - 模型列表管理
 * - 当前模型跟踪
 * - 加载和错误状态管理
 * 
 * 使用示例：
 *   import { useDispatch, useSelector } from 'react-redux';
 *   import { setModels, setCurrentModel } from './slices/modelSlice';
 *   
 *   const dispatch = useDispatch();
 *   const { models, currentModel } = useSelector((state) => state.model);
 *   
 *   // 设置模型列表
 *   dispatch(setModels(modelsArray));
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit';

/**
 * 模型接口
 */
export interface Model {
  id: number;           // 模型ID
  name: string;         // 模型名称
  version: string;      // 模型版本
  model_type: string;   // 模型类型
  accuracy?: number;    // 准确率
  status: string;       // 状态（registered, testing, active, inactive）
  is_active: boolean;   // 是否激活（部署到生产环境）
  created_at: string;   // 创建时间
}

/**
 * 模型管理状态接口
 */
export interface ModelState {
  models: Model[];              // 模型列表
  currentModel: Model | null;   // 当前选中的模型
  loading: boolean;             // 加载状态
  error: string | null;         // 错误信息
}

/**
 * 初始状态
 */
const initialState: ModelState = {
  models: [],
  currentModel: null,
  loading: false,
  error: null,
};

/**
 * 模型管理状态切片
 */
const modelSlice = createSlice({
  name: 'model',
  initialState,
  reducers: {
    /** 设置模型列表 */
    setModels: (state, action: PayloadAction<Model[]>) => {
      state.models = action.payload;
    },
    
    /** 设置当前选中的模型 */
    setCurrentModel: (state, action: PayloadAction<Model | null>) => {
      state.currentModel = action.payload;
    },
    
    /** 设置加载状态 */
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },
    
    /** 设置错误信息 */
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    
    /** 清除错误信息 */
    clearError: (state) => {
      state.error = null;
    },
  },
});

// 导出actions供组件使用
export const { setModels, setCurrentModel, setLoading, setError, clearError } = modelSlice.actions;

// 导出reducer供store配置使用
export default modelSlice.reducer;