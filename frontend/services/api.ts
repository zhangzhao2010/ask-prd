/**
 * API服务封装
 * 统一管理所有后端API调用
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import type {
  KnowledgeBase,
  KnowledgeBaseCreate,
  KnowledgeBaseUpdate,
  KnowledgeBaseListResponse,
  KnowledgeBaseDetail,
  Document,
  DocumentListResponse,
  DocumentUploadResponse,
  SyncTask,
  SyncTaskCreate,
  SyncTaskListResponse,
  QueryHistory,
  QueryHistoryListResponse,
  ErrorResponse,
} from '@/types';

// API基础URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// 创建axios实例
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30秒超时
});

// 响应拦截器：统一错误处理
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ErrorResponse>) => {
    // 统一错误处理
    if (error.response) {
      // 服务器返回错误
      const errorData = error.response.data;
      console.error('API Error:', errorData);
      return Promise.reject(errorData);
    } else if (error.request) {
      // 请求发送但没有响应
      console.error('Network Error:', error.message);
      return Promise.reject({
        error_code: 'NETWORK_ERROR',
        message: '网络连接失败，请检查后端服务是否启动',
        details: { originalError: error.message },
      });
    } else {
      // 其他错误
      console.error('Request Error:', error.message);
      return Promise.reject({
        error_code: 'REQUEST_ERROR',
        message: error.message,
        details: {},
      });
    }
  }
);

// ============ 知识库API ============

export const knowledgeBaseAPI = {
  /**
   * 获取知识库列表
   */
  async list(params?: { page?: number; page_size?: number }): Promise<KnowledgeBaseListResponse> {
    const response = await apiClient.get<KnowledgeBaseListResponse>('/knowledge-bases', { params });
    return response.data;
  },

  /**
   * 创建知识库
   */
  async create(data: KnowledgeBaseCreate): Promise<KnowledgeBase> {
    const response = await apiClient.post<KnowledgeBase>('/knowledge-bases', data);
    return response.data;
  },

  /**
   * 获取知识库详情
   */
  async get(kbId: string): Promise<KnowledgeBaseDetail> {
    const response = await apiClient.get<KnowledgeBaseDetail>(`/knowledge-bases/${kbId}`);
    return response.data;
  },

  /**
   * 更新知识库
   */
  async update(kbId: string, data: KnowledgeBaseUpdate): Promise<KnowledgeBase> {
    const response = await apiClient.put<KnowledgeBase>(`/knowledge-bases/${kbId}`, data);
    return response.data;
  },

  /**
   * 删除知识库
   */
  async delete(kbId: string): Promise<{ message: string }> {
    const response = await apiClient.delete<{ message: string }>(`/knowledge-bases/${kbId}`);
    return response.data;
  },
};

// ============ 文档API ============

export const documentAPI = {
  /**
   * 获取文档列表
   */
  async list(params: {
    kb_id: string;
    page?: number;
    page_size?: number;
  }): Promise<DocumentListResponse> {
    const response = await apiClient.get<DocumentListResponse>('/documents', { params });
    return response.data;
  },

  /**
   * 上传文档
   */
  async upload(kbId: string, file: File): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<DocumentUploadResponse>(
      '/documents',
      formData,
      {
        params: { kb_id: kbId },
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  /**
   * 获取文档详情
   */
  async get(docId: string): Promise<Document> {
    const response = await apiClient.get<Document>(`/documents/${docId}`);
    return response.data;
  },

  /**
   * 删除文档
   */
  async delete(docId: string): Promise<{ message: string }> {
    const response = await apiClient.delete<{ message: string }>(`/documents/${docId}`);
    return response.data;
  },
};

// ============ 同步任务API ============

export const syncTaskAPI = {
  /**
   * 创建同步任务
   */
  async create(data: SyncTaskCreate): Promise<SyncTask> {
    const response = await apiClient.post<SyncTask>('/sync-tasks', data);
    return response.data;
  },

  /**
   * 获取同步任务列表
   */
  async list(params: {
    kb_id: string;
    status?: string;
    limit?: number;  // 返回数量（后端参数名是limit）
  }): Promise<SyncTaskListResponse> {
    const response = await apiClient.get<SyncTaskListResponse>('/sync-tasks', { params });
    return response.data;
  },

  /**
   * 获取同步任务详情
   */
  async get(taskId: string): Promise<SyncTask> {
    const response = await apiClient.get<SyncTask>(`/sync-tasks/${taskId}`);
    return response.data;
  },
};

// ============ 查询API ============

export const queryAPI = {
  /**
   * 流式查询（SSE）
   * 返回ReadableStream，需要手动处理
   */
  async stream(kbId: string, query: string): Promise<ReadableStream<Uint8Array>> {
    const response = await fetch(
      `${API_BASE_URL}/query/stream?kb_id=${encodeURIComponent(kbId)}&query=${encodeURIComponent(query)}`,
      {
        method: 'POST',
        headers: {
          'Accept': 'text/event-stream',
        },
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    if (!response.body) {
      throw new Error('Response body is null');
    }

    return response.body;
  },

  /**
   * 获取查询历史列表
   */
  async listHistory(params: {
    kb_id: string;
    page?: number;
    page_size?: number;
  }): Promise<QueryHistoryListResponse> {
    const response = await apiClient.get<QueryHistoryListResponse>('/query/history', { params });
    return response.data;
  },

  /**
   * 获取查询历史详情
   */
  async getHistory(queryId: string): Promise<QueryHistory> {
    const response = await apiClient.get<QueryHistory>(`/query/history/${queryId}`);
    return response.data;
  },
};

// ============ 健康检查API ============

export const healthAPI = {
  /**
   * 检查后端服务健康状态
   */
  async check(): Promise<{ status: string; timestamp: string }> {
    const response = await apiClient.get<{ status: string; timestamp: string }>('/health');
    return response.data;
  },
};

// 导出默认的API客户端
export default apiClient;
