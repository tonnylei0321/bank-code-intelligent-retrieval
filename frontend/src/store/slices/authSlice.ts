/**
 * 认证状态管理模块（Redux Slice）
 * 
 * 管理用户认证相关的全局状态，包括：
 * - 用户登录/登出
 * - 令牌管理（访问令牌和刷新令牌）
 * - 认证状态跟踪
 * - 用户信息存储
 * 
 * 功能特性：
 * - 异步登录操作（createAsyncThunk）
 * - 自动令牌刷新
 * - 本地存储同步（localStorage）
 * - 错误状态管理
 * 
 * 使用示例：
 *   import { useDispatch, useSelector } from 'react-redux';
 *   import { login, logout } from './slices/authSlice';
 *   
 *   const dispatch = useDispatch();
 *   const { user, isAuthenticated } = useSelector((state) => state.auth);
 *   
 *   // 登录
 *   dispatch(login({ username: 'admin', password: '123456' }));
 *   
 *   // 登出
 *   dispatch(logout());
 */

import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { authAPI } from '../../services/api';

/**
 * 用户信息接口
 */
export interface User {
  id: number;           // 用户ID
  username: string;     // 用户名
  email: string;        // 邮箱
  role: 'admin' | 'user';  // 用户角色
}

/**
 * 认证状态接口
 */
export interface AuthState {
  isAuthenticated: boolean;  // 是否已认证
  user: User | null;          // 当前用户信息
  token: string | null;       // 访问令牌
  refreshToken: string | null; // 刷新令牌
  loading: boolean;           // 加载状态
  error: string | null;       // 错误信息
}

/**
 * 初始状态
 * 从localStorage恢复令牌，实现页面刷新后保持登录状态
 */
const token = localStorage.getItem('access_token');
const storedRefreshToken = localStorage.getItem('refresh_token');

const initialState: AuthState = {
  isAuthenticated: !!token, // 如果有token就认为已认证
  user: null,
  token,
  refreshToken: storedRefreshToken,
  loading: false,
  error: null,
};

/**
 * 异步操作：验证现有token并获取用户信息
 * 
 * 在应用启动时调用，检查localStorage中的token是否有效
 * 如果有效则获取用户信息，否则清除认证状态
 */
export const validateToken = createAsyncThunk(
  'auth/validateToken',
  async (_, { rejectWithValue }) => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      return rejectWithValue('No token found');
    }
    
    try {
      const userResponse = await authAPI.getCurrentUser();
      return {
        user: userResponse.data,
        token,
      };
    } catch (error) {
      // Token无效，清除localStorage
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      return rejectWithValue('Token invalid');
    }
  }
);

/**
 * 异步操作：用户登录
 * 
 * 调用登录API，成功后自动保存令牌和用户信息到状态和localStorage
 * 
 * @param credentials - 登录凭证（用户名和密码）
 * @returns 包含令牌和用户信息的响应数据
 */
export const login = createAsyncThunk(
  'auth/login',
  async (credentials: { username: string; password: string }) => {
    // 1. 先登录获取token
    const loginResponse = await authAPI.login(credentials);
    const { access_token } = loginResponse.data;
    
    // 2. 使用token获取用户信息
    // 临时设置token到localStorage，以便后续请求可以使用
    localStorage.setItem('access_token', access_token);
    
    const userResponse = await authAPI.getCurrentUser();
    
    return {
      access_token,
      token_type: 'bearer',
      user: userResponse.data,
    };
  }
);

/**
 * 异步操作：刷新访问令牌
 * 
 * 使用刷新令牌获取新的访问令牌，延长用户会话
 * 
 * @param refreshToken - 刷新令牌
 * @returns 新的访问令牌和刷新令牌
 */
export const refreshToken = createAsyncThunk(
  'auth/refreshToken',
  async (refreshToken: string) => {
    const response = await authAPI.refreshToken(refreshToken);
    return response.data;
  }
);

/**
 * 异步操作：用户登出
 * 
 * 清除本地令牌和用户信息
 * 注意：JWT是无状态的，不需要调用服务器端API
 */
export const logout = createAsyncThunk(
  'auth/logout',
  async () => {
    // JWT是无状态的，只需要清除本地存储即可
    // 不需要调用服务器端API
    return;
  }
);

/**
 * 认证状态切片
 */
const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    /**
     * 清除错误信息
     */
    clearError: (state) => {
      state.error = null;
    },
    
    /**
     * 设置认证凭证
     * 用于手动设置用户信息和令牌（例如从localStorage恢复）
     */
    setCredentials: (state, action: PayloadAction<{ user: User; token: string; refreshToken: string }>) => {
      const { user, token, refreshToken } = action.payload;
      state.user = user;
      state.token = token;
      state.refreshToken = refreshToken;
      state.isAuthenticated = true;
      // 同步到localStorage
      localStorage.setItem('access_token', token);
      localStorage.setItem('refresh_token', refreshToken);
    },
    
    /**
     * 清除认证凭证
     * 用于登出或令牌失效时清除所有认证信息
     */
    clearCredentials: (state) => {
      state.user = null;
      state.token = null;
      state.refreshToken = null;
      state.isAuthenticated = false;
      // 清除localStorage
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    },
  },
  /**
   * 处理异步操作的状态变化
   */
  extraReducers: (builder) => {
    builder
      // 验证token操作的状态处理
      .addCase(validateToken.pending, (state) => {
        state.loading = true;
      })
      .addCase(validateToken.fulfilled, (state, action) => {
        state.loading = false;
        state.isAuthenticated = true;
        state.user = action.payload.user;
        state.token = action.payload.token;
      })
      .addCase(validateToken.rejected, (state) => {
        state.loading = false;
        state.isAuthenticated = false;
        state.user = null;
        state.token = null;
        state.refreshToken = null;
      })
      
      // 登录操作的状态处理
      .addCase(login.pending, (state) => {
        // 登录请求中
        state.loading = true;
        state.error = null;
      })
      .addCase(login.fulfilled, (state, action) => {
        // 登录成功
        state.loading = false;
        state.isAuthenticated = true;
        state.user = action.payload.user;
        state.token = action.payload.access_token;
        // 注意：当前后端不返回refresh_token，暂时设为null
        state.refreshToken = null;
        // 保存到localStorage
        localStorage.setItem('access_token', action.payload.access_token);
      })
      .addCase(login.rejected, (state, action) => {
        // 登录失败
        state.loading = false;
        state.error = action.error.message || '登录失败';
      })
      
      // 刷新令牌操作的状态处理
      .addCase(refreshToken.fulfilled, (state, action) => {
        // 令牌刷新成功，更新令牌
        state.token = action.payload.access_token;
        state.refreshToken = action.payload.refresh_token;
        localStorage.setItem('access_token', action.payload.access_token);
        localStorage.setItem('refresh_token', action.payload.refresh_token);
      })
      
      // 登出操作的状态处理
      .addCase(logout.fulfilled, (state) => {
        // 登出成功，清除所有认证信息
        state.isAuthenticated = false;
        state.user = null;
        state.token = null;
        state.refreshToken = null;
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
      });
  },
});

// 导出actions供组件使用
export const { clearError, setCredentials, clearCredentials } = authSlice.actions;

// 导出reducer供store配置使用
export default authSlice.reducer;