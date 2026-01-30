/**
 * 数据管理状态模块（Redux Slice）
 * 
 * 管理数据集相关的全局状态，包括：
 * - 数据集列表
 * - 当前选中的数据集
 * - 加载状态和错误信息
 * 
 * 功能特性：
 * - 数据集列表管理
 * - 当前数据集跟踪
 * - 加载和错误状态管理
 * 
 * 使用示例：
 *   import { useDispatch, useSelector } from 'react-redux';
 *   import { setDatasets, setCurrentDataset } from './slices/dataSlice';
 *   
 *   const dispatch = useDispatch();
 *   const { datasets, currentDataset } = useSelector((state) => state.data);
 *   
 *   // 设置数据集列表
 *   dispatch(setDatasets(datasetsArray));
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit';

/**
 * 数据集接口
 */
export interface Dataset {
  id: number;              // 数据集ID
  name: string;            // 数据集名称
  description?: string;    // 数据集描述
  file_size: number;       // 文件大小（字节）
  record_count?: number;   // 记录数量
  format: string;          // 文件格式（csv, txt, excel）
  status: string;          // 状态（uploaded, validating, validated, error）
  created_at: string;      // 创建时间
}

/**
 * 数据管理状态接口
 */
export interface DataState {
  datasets: Dataset[];           // 数据集列表
  currentDataset: Dataset | null; // 当前选中的数据集
  loading: boolean;              // 加载状态
  error: string | null;          // 错误信息
}

/**
 * 初始状态
 */
const initialState: DataState = {
  datasets: [],
  currentDataset: null,
  loading: false,
  error: null,
};

/**
 * 数据管理状态切片
 */
const dataSlice = createSlice({
  name: 'data',
  initialState,
  reducers: {
    /** 设置数据集列表 */
    setDatasets: (state, action: PayloadAction<Dataset[]>) => {
      state.datasets = action.payload;
    },
    
    /** 设置当前选中的数据集 */
    setCurrentDataset: (state, action: PayloadAction<Dataset | null>) => {
      state.currentDataset = action.payload;
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
export const { setDatasets, setCurrentDataset, setLoading, setError, clearError } = dataSlice.actions;

// 导出reducer供store配置使用
export default dataSlice.reducer;