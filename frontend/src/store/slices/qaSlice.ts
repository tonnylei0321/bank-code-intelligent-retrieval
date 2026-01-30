/**
 * 问答服务状态模块（Redux Slice）
 * 
 * 管理问答服务相关的全局状态，包括：
 * - 问答消息列表
 * - 当前会话ID
 * - 加载状态和错误信息
 * 
 * 功能特性：
 * - 消息历史管理
 * - 会话跟踪
 * - 实时消息添加
 * - 加载和错误状态管理
 * 
 * 使用示例：
 *   import { useDispatch, useSelector } from 'react-redux';
 *   import { addMessage, setCurrentSessionId } from './slices/qaSlice';
 *   
 *   const dispatch = useDispatch();
 *   const { messages, currentSessionId } = useSelector((state) => state.qa);
 *   
 *   // 添加新消息
 *   dispatch(addMessage({ id: 1, question: '...', answer: '...' }));
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit';

/**
 * 问答消息接口
 */
export interface QAMessage {
  id: number;              // 消息ID
  question: string;        // 用户问题
  answer: string;          // AI回答
  confidence?: number;     // 置信度（0-1）
  response_time?: number;  // 响应时间（毫秒）
  created_at: string;      // 创建时间
}

/**
 * 问答服务状态接口
 */
export interface QAState {
  messages: QAMessage[];          // 消息列表
  currentSessionId: string | null; // 当前会话ID
  loading: boolean;               // 加载状态
  error: string | null;           // 错误信息
}

/**
 * 初始状态
 */
const initialState: QAState = {
  messages: [],
  currentSessionId: null,
  loading: false,
  error: null,
};

/**
 * 问答服务状态切片
 */
const qaSlice = createSlice({
  name: 'qa',
  initialState,
  reducers: {
    /** 设置消息列表（替换整个列表） */
    setMessages: (state, action: PayloadAction<QAMessage[]>) => {
      state.messages = action.payload;
    },
    
    /** 添加新消息到列表末尾 */
    addMessage: (state, action: PayloadAction<QAMessage>) => {
      state.messages.push(action.payload);
    },
    
    /** 设置当前会话ID */
    setCurrentSessionId: (state, action: PayloadAction<string | null>) => {
      state.currentSessionId = action.payload;
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
    
    /** 清除所有消息和会话ID（开始新会话） */
    clearMessages: (state) => {
      state.messages = [];
      state.currentSessionId = null;
    },
  },
});

// 导出actions供组件使用
export const { setMessages, addMessage, setCurrentSessionId, setLoading, setError, clearError, clearMessages } = qaSlice.actions;

// 导出reducer供store配置使用
export default qaSlice.reducer;