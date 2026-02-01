/**
 * API服务模块
 * 
 * 本模块封装了所有与后端API的交互逻辑，提供统一的HTTP请求接口。
 * 
 * 主要功能：
 * - Axios实例配置（基础URL、超时、请求头等）
 * - 请求拦截器（自动添加认证令牌）
 * - 响应拦截器（统一错误处理、令牌刷新）
 * - 分类的API方法（认证、用户、数据、训练、模型、问答、系统）
 * 
 * 技术特性：
 * - 自动令牌刷新：当访问令牌过期时，自动使用刷新令牌获取新令牌
 * - 统一错误处理：拦截所有HTTP错误并显示友好提示
 * - TypeScript类型支持：完整的类型定义确保类型安全
 * - 请求重试：令牌刷新后自动重试原始请求
 * 
 * 使用示例：
 *   import { authAPI, userAPI } from '@/services/api';
 *   
 *   // 登录
 *   const response = await authAPI.login({ username: 'admin', password: '123456' });
 *   
 *   // 获取用户列表
 *   const users = await userAPI.getUsers({ page: 1, size: 20 });
 */

import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { message } from 'antd';

// API基础URL配置
// 优先使用环境变量，否则使用默认的本地开发地址
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

/**
 * 创建axios实例
 * 
 * 配置项：
 * - baseURL: API基础路径
 * - timeout: 请求超时时间（30秒）
 * - headers: 默认请求头（JSON格式）
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,  // 增加到60秒
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * 请求拦截器
 * 
 * 在每个请求发送前执行，主要用于：
 * - 从localStorage读取访问令牌
 * - 将令牌添加到请求头的Authorization字段
 * - 格式：Bearer <token>
 * 
 * 这样所有需要认证的API请求都会自动携带令牌。
 */
apiClient.interceptors.request.use(
  (config) => {
    // 从本地存储获取访问令牌
    const token = localStorage.getItem('access_token');
    if (token) {
      // 添加Bearer令牌到请求头
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

/**
 * 响应拦截器
 * 
 * 在收到响应后执行，主要用于：
 * - 统一处理HTTP错误
 * - 自动刷新过期的访问令牌
 * - 显示错误提示消息
 * 
 * 令牌刷新流程：
 * 1. 检测到401错误（未授权）
 * 2. 使用刷新令牌请求新的访问令牌
 * 3. 更新本地存储的访问令牌
 * 4. 重试原始请求
 * 5. 如果刷新失败，清除令牌并跳转到登录页
 */
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    // 请求成功，直接返回响应
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // 处理401错误（令牌过期或无效）
    // 但排除登录和注册请求，避免无限循环
    if (
      error.response?.status === 401 && 
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/login') &&
      !originalRequest.url?.includes('/auth/register')
    ) {
      // 标记为已重试，避免无限循环
      originalRequest._retry = true;

      try {
        // 尝试使用刷新令牌获取新的访问令牌
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          const response = await authAPI.refreshToken(refreshToken);
          const { access_token } = response.data;
          
          // 更新本地存储
          localStorage.setItem('access_token', access_token);
          
          // 更新原始请求的令牌
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          
          // 重试原始请求
          return apiClient(originalRequest);
        }
      } catch (refreshError) {
        // 刷新令牌失败，清除本地存储并跳转到登录页
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    // 显示错误消息
    const errorMessage = error.response?.data?.error_message || 
                        error.response?.data?.message || 
                        error.response?.data?.detail ||
                        error.message || 
                        '请求失败';
    message.error(errorMessage);

    return Promise.reject(error);
  }
);

/**
 * 通用API响应类型
 * 
 * 所有API响应都遵循统一的格式，包含：
 * - code: 状态码
 * - message: 响应消息
 * - data: 实际数据（泛型，根据具体API而定）
 * - timestamp: 响应时间戳
 * - request_id: 可选的请求追踪ID
 */
export interface APIResponse<T = any> {
  code: number;
  message: string;
  data: T;
  timestamp: string;
  request_id?: string;
}

/**
 * 分页响应类型
 * 
 * 用于列表查询的分页数据，包含：
 * - items: 当前页的数据项数组
 * - pagination: 分页信息（页码、每页大小、总数、总页数）
 */
export interface PaginationResponse<T> {
  items: T[];
  pagination: {
    page: number;    // 当前页码
    size: number;    // 每页大小
    total: number;   // 总记录数
    pages: number;   // 总页数
  };
}

/**
 * 认证API
 * 
 * 提供用户认证相关的接口：
 * - login: 用户登录，返回访问令牌和刷新令牌
 * - refreshToken: 刷新访问令牌
 * - logout: 用户登出
 */
export const authAPI = {
  /**
   * 用户登录
   * @param credentials - 登录凭证（用户名和密码）
   * @returns 包含令牌的响应
   */
  login: (credentials: { username: string; password: string }) => {
    // 后端使用OAuth2PasswordRequestForm，需要发送application/x-www-form-urlencoded格式
    const formData = new URLSearchParams();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);
    
    return apiClient.post<{
      access_token: string;
      token_type: string;
    }>('/v1/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
  },

  /**
   * 获取当前用户信息
   * @returns 当前登录用户的详细信息
   */
  getCurrentUser: () =>
    apiClient.get<{
      id: number;
      username: string;
      email: string;
      role: string;
      is_active: boolean;
      created_at: string;
    }>('/v1/auth/me'),

  /**
   * 刷新访问令牌
   * @param refreshToken - 刷新令牌
   * @returns 新的访问令牌和用户信息
   */
  refreshToken: (refreshToken: string) =>
    apiClient.post<APIResponse<{
      access_token: string;
      refresh_token: string;
      token_type: string;
      expires_in: number;
      user: {
        id: number;
        username: string;
        email: string;
        role: string;
      };
    }>>('/v1/auth/refresh', { refresh_token: refreshToken }),

  /**
   * 用户登出
   * 注意：JWT是无状态的，不需要调用服务器端API
   * 前端只需清除本地存储的token即可
   */
  logout: () => Promise.resolve({ data: { message: 'Logged out successfully' } }),
};

/**
 * 用户管理API
 * 
 * 提供用户相关的CRUD操作：
 * - getProfile: 获取当前用户信息
 * - updateProfile: 更新当前用户信息
 * - getUsers: 获取用户列表（分页）
 * - createUser: 创建新用户
 * - updateUser: 更新指定用户
 * - deleteUser: 删除指定用户
 */
export const userAPI = {
  /** 获取当前用户个人资料 */
  getProfile: () => apiClient.get<APIResponse<any>>('/v1/users/profile'),
  
  /** 更新当前用户个人资料 */
  updateProfile: (data: any) => apiClient.put<APIResponse<any>>('/v1/users/profile', data),
  
  /** 获取用户列表（支持分页和过滤） */
  getUsers: (params?: any) => apiClient.get<APIResponse<PaginationResponse<any>>>('/v1/users', { params }),
  
  /** 创建新用户（管理员权限） */
  createUser: (data: any) => apiClient.post<APIResponse<any>>('/v1/users', data),
  
  /** 更新指定用户信息（管理员权限） */
  updateUser: (id: number, data: any) => apiClient.put<APIResponse<any>>(`/v1/users/${id}`, data),
  
  /** 删除指定用户（管理员权限） */
  deleteUser: (id: number) => apiClient.delete<APIResponse<any>>(`/v1/users/${id}`),
};

/**
 * 数据管理API
 * 
 * 提供数据集的上传、验证、预览和管理功能
 */
export const dataAPI = {
  /**
   * 上传数据文件
   */
  uploadDataset: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post('/v1/datasets/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  
  /** 获取数据集列表 */
  getDatasets: () => apiClient.get('/v1/datasets'),
  
  /** 获取指定数据集的详细信息 */
  getDataset: (id: number) => apiClient.get(`/v1/datasets/${id}`),
  
  /** 获取数据集统计信息 */
  getDatasetStats: (id: number) => apiClient.get(`/v1/datasets/${id}/stats`),
  
  /** 预览数据集内容 */
  previewDataset: (id: number, limit: number = 10) => 
    apiClient.get(`/v1/datasets/${id}/preview`, { params: { limit } }),
  
  /** 验证数据集格式和内容 */
  validateDataset: (id: number) => apiClient.post(`/v1/datasets/${id}/validate`),
  
  /** 删除数据集 */
  deleteDataset: (id: number) => apiClient.delete(`/v1/datasets/${id}`),
};

/**
 * 训练管理API
 */
export const trainingAPI = {
  /** 智能优化训练参数 */
  optimizeTrainingParams: (data: {
    dataset_id: number;
    model_name: string;
    target_training_time_hours: number;
  }) => apiClient.post('/v1/training/optimize', data),
  
  /** 启动训练任务 */
  startTraining: (data: {
    dataset_id: number;
    model_name?: string;
    use_optimized_params?: boolean;
    target_training_time_hours?: number;
    epochs?: number;
    batch_size?: number;
    learning_rate?: number;
    lora_r?: number;
    lora_alpha?: number;
    lora_dropout?: number;
  }) => apiClient.post('/v1/training/start', data),
  
  /** 获取训练任务列表 */
  getTrainingJobs: (params?: { dataset_id?: number; status?: string }) => 
    apiClient.get('/v1/training/jobs', { params }),
  
  /** 获取指定训练任务的详细信息 */
  getTrainingJob: (id: number) => apiClient.get(`/v1/training/${id}`),
  
  /** 停止正在运行的训练任务 */
  stopTrainingJob: (id: number) => apiClient.post(`/v1/training/${id}/stop`),
  
  /** 停止训练任务（别名） */
  stopTraining: (id: number) => apiClient.post(`/v1/training/${id}/stop`),
  
  /** 删除训练任务 */
  deleteTrainingJob: (id: number) => apiClient.post(`/v1/training/${id}/delete`),
  
  /** 批量删除训练任务 */
  batchDeleteTrainingJobs: (jobIds: number[]) => 
    apiClient.post('/v1/training/batch/delete', { job_ids: jobIds }),
};

/**
 * 评估管理API
 */
export const evaluationAPI = {
  /** 启动评估任务 */
  startEvaluation: (data: {
    training_job_id: number;
    evaluation_type: string;
    test_dataset_id?: number;
  }) => apiClient.post('/v1/evaluation/start', data),
  
  /** 获取评估详情 */
  getEvaluation: (id: number) => apiClient.get(`/v1/evaluation/${id}`),
  
  /** 获取评估报告 */
  getEvaluationReport: (id: number) => apiClient.get(`/v1/evaluation/${id}/report`),
  
  /** 获取训练任务的所有评估 */
  getEvaluationsByJob: (jobId: number) => 
    apiClient.get(`/v1/evaluation/jobs/${jobId}/evaluations`),
  
  /** 获取所有评估列表 */
  getAllEvaluations: (params?: { evaluation_type?: string; status?: string }) =>
    apiClient.get('/v1/evaluation/list', { params }),
};

/**
 * 问答对管理API
 */
export const qaPairsAPI = {
  /** 生成问答对 */
  generateQAPairs: (data: {
    dataset_id: number;
    num_pairs?: number;
    difficulty_level?: string;
  }) => apiClient.post('/v1/qa-pairs/generate', data),
  
  /** 获取问答对统计 */
  getQAPairStats: (datasetId: number) => apiClient.get(`/v1/qa-pairs/${datasetId}/stats`),
  
  /** 获取问答对列表 */
  getQAPairs: (datasetId: number, params?: { limit?: number; offset?: number }) =>
    apiClient.get(`/v1/qa-pairs/${datasetId}`, { params }),
  
  /** 删除问答对 */
  deleteQAPairs: (datasetId: number) => apiClient.delete(`/v1/qa-pairs/${datasetId}`),
  
  /** 导出问答对 */
  exportQAPairs: (datasetId: number) => apiClient.get(`/v1/qa-pairs/${datasetId}/export`),
};

/**
 * 问答查询API
 */
export const queryAPI = {
  /** 提交查询 */
  query: (data: { question: string; use_rag?: boolean; top_k?: number }) =>
    apiClient.post('/v1/query/', data),
  
  /** 批量查询 */
  batchQuery: (data: { questions: string[]; use_rag?: boolean; top_k?: number }) =>
    apiClient.post('/v1/query/batch', data),
  
  /** 获取查询历史 */
  getQueryHistory: (limit: number = 100) =>
    apiClient.get('/v1/query/history', { params: { limit } }),
};

/**
 * 用户管理API（管理员）
 */
export const adminAPI = {
  /** 获取所有用户 */
  getAllUsers: () => apiClient.get('/v1/admin/users'),
  
  /** 获取指定用户 */
  getUserById: (id: number) => apiClient.get(`/v1/admin/users/${id}`),
  
  /** 删除用户 */
  deleteUser: (id: number) => apiClient.delete(`/v1/admin/users/${id}`),
};

/**
 * 日志管理API
 */
export const logsAPI = {
  /** 获取日志 */
  getLogs: (params?: {
    page?: number;
    page_size?: number;
    level?: string;
    start_time?: string;
    end_time?: string;
  }) => apiClient.get('/v1/logs', { params }),
  
  /** 获取日志文件列表 */
  getLogFiles: () => apiClient.get('/v1/logs/files'),
};

// 导出axios实例供其他模块使用
export default apiClient;