/**
 * 训练管理状态模块（Redux Slice）
 * 
 * 管理模型训练任务相关的全局状态，包括：
 * - 训练任务列表
 * - 当前选中的任务
 * - 任务进度跟踪
 * - 加载状态和错误信息
 * 
 * 功能特性：
 * - 训练任务列表管理
 * - 当前任务跟踪
 * - 实时进度更新
 * - 加载和错误状态管理
 * 
 * 使用示例：
 *   import { useDispatch, useSelector } from 'react-redux';
 *   import { setTasks, updateTaskProgress } from './slices/trainingSlice';
 *   
 *   const dispatch = useDispatch();
 *   const { tasks, currentTask } = useSelector((state) => state.training);
 *   
 *   // 更新任务进度
 *   dispatch(updateTaskProgress({ id: 1, progress: 50, status: 'training' }));
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit';

/**
 * 训练任务接口
 */
export interface TrainingTask {
  id: number;              // 任务ID
  name: string;            // 任务名称
  description?: string;    // 任务描述
  dataset_id: number;      // 数据集ID
  model_type: string;      // 模型类型
  status: string;          // 状态（created, queued, training, completed, failed）
  progress: number;        // 进度（0-100）
  created_at: string;      // 创建时间
}

/**
 * 训练管理状态接口
 */
export interface TrainingState {
  tasks: TrainingTask[];           // 训练任务列表
  currentTask: TrainingTask | null; // 当前选中的任务
  loading: boolean;                // 加载状态
  error: string | null;            // 错误信息
}

/**
 * 初始状态
 */
const initialState: TrainingState = {
  tasks: [],
  currentTask: null,
  loading: false,
  error: null,
};

/**
 * 训练管理状态切片
 */
const trainingSlice = createSlice({
  name: 'training',
  initialState,
  reducers: {
    /** 设置训练任务列表 */
    setTasks: (state, action: PayloadAction<TrainingTask[]>) => {
      state.tasks = action.payload;
    },
    
    /** 设置当前选中的任务 */
    setCurrentTask: (state, action: PayloadAction<TrainingTask | null>) => {
      state.currentTask = action.payload;
    },
    
    /**
     * 更新任务进度
     * 同时更新任务列表和当前任务中的进度信息
     */
    updateTaskProgress: (state, action: PayloadAction<{ id: number; progress: number; status: string }>) => {
      // 更新任务列表中的任务
      const task = state.tasks.find(t => t.id === action.payload.id);
      if (task) {
        task.progress = action.payload.progress;
        task.status = action.payload.status;
      }
      
      // 如果是当前任务，也更新当前任务的进度
      if (state.currentTask?.id === action.payload.id) {
        state.currentTask.progress = action.payload.progress;
        state.currentTask.status = action.payload.status;
      }
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
export const { setTasks, setCurrentTask, updateTaskProgress, setLoading, setError, clearError } = trainingSlice.actions;

// 导出reducer供store配置使用
export default trainingSlice.reducer;