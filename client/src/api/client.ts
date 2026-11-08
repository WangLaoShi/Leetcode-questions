/**
 * API 客户端
 */
import axios, { type AxiosInstance, type AxiosError } from 'axios';

// 创建 axios 实例
const apiClient: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 添加认证令牌
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器 - 处理令牌刷新
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config;
    
    // 如果是 401 错误且有刷新令牌，尝试刷新
    if (error.response?.status === 401 && originalRequest) {
      const refreshToken = localStorage.getItem('refreshToken');
      
      if (refreshToken && !(originalRequest as any)._retry) {
        (originalRequest as any)._retry = true;
        
        try {
          const response = await axios.post('/api/auth/refresh', {
            refreshToken,
          });
          
          const { accessToken, refreshToken: newRefreshToken } = response.data.data;
          localStorage.setItem('accessToken', accessToken);
          localStorage.setItem('refreshToken', newRefreshToken);
          
          originalRequest.headers.Authorization = `Bearer ${accessToken}`;
          return apiClient(originalRequest);
        } catch (refreshError) {
          // 刷新失败，清除令牌并跳转到登录页
          localStorage.removeItem('accessToken');
          localStorage.removeItem('refreshToken');
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      }
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;

// API 方法
export const authApi = {
  register: (data: { username: string; email: string; password: string }) =>
    apiClient.post('/auth/register', data),
  
  login: (data: { username: string; password: string }) =>
    apiClient.post('/auth/login', data),
  
  logout: (refreshToken: string) =>
    apiClient.post('/auth/logout', { refreshToken }),
  
  getMe: () =>
    apiClient.get('/auth/me'),
  
  refresh: (refreshToken: string) =>
    apiClient.post('/auth/refresh', { refreshToken }),
};

export const problemsApi = {
  getList: (params: {
    page?: number;
    limit?: number;
    search?: string;
    difficulty?: string;
    category?: string;
    tag?: string;
    site?: string;
    locale?: string;
    sort?: string;
    order?: 'asc' | 'desc';
  }) => apiClient.get('/problems', { params }),
  
  getDetail: (identifier: string | number, params?: { site?: string; locale?: string }) =>
    apiClient.get(`/problems/${identifier}`, { params }),
  
  getHints: (identifier: string | number, params?: { site?: string; locale?: string }) =>
    apiClient.get(`/problems/${identifier}/hints`, { params }),
  
  getTags: () =>
    apiClient.get('/problems/tags'),
  
  getCategories: () =>
    apiClient.get('/problems/categories'),
};

export const recordsApi = {
  getList: (params?: { status?: string }) =>
    apiClient.get('/records', { params }),
  
  getStats: () =>
    apiClient.get('/records/stats'),
  
  getRecord: (problemId: number) =>
    apiClient.get(`/records/${problemId}`),
  
  upsert: (data: {
    problemId: number;
    slug: string;
    status?: string;
    language?: string;
    viewedHints?: boolean;
    notes?: string;
  }) => apiClient.post('/records', data),
};
