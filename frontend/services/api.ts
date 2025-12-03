/**
 * API客户端
 * 统一的API调用封装，自动处理认证、错误等
 */

import { authService, User } from './auth';

interface RequestOptions extends RequestInit {
  requireAuth?: boolean; // 是否需要认证，默认true
}

class ApiClient {
  private readonly baseURL = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

  /**
   * 通用请求方法
   */
  private async request<T>(
    url: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const { requireAuth = true, ...fetchOptions } = options;

    // 构建请求头
    const headers: Record<string, string> = {
      ...(fetchOptions.headers as Record<string, string>),
    };

    // 添加认证Token
    if (requireAuth) {
      const token = authService.getToken();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    }

    // 发送请求
    const response = await fetch(`${this.baseURL}${url}`, {
      ...fetchOptions,
      headers,
    });

    // 处理401 - Token过期或无效
    if (response.status === 401) {
      authService.logout();
      window.location.href = '/login';
      throw new Error('认证失败，请重新登录');
    }

    // 处理204 - No Content
    if (response.status === 204) {
      return null as T;
    }

    // 处理错误响应
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `请求失败: ${response.status}`);
    }

    return response.json();
  }

  /**
   * GET请求
   */
  async get<T>(url: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(url, { ...options, method: 'GET' });
  }

  /**
   * POST请求
   */
  async post<T>(
    url: string,
    data?: unknown,
    options?: RequestOptions
  ): Promise<T> {
    // 如果data是FormData，不设置Content-Type（让浏览器自动设置）
    // 并且不使用JSON.stringify
    const isFormData = data instanceof FormData;

    return this.request<T>(url, {
      ...options,
      method: 'POST',
      headers: isFormData
        ? options?.headers  // FormData: 不设置Content-Type
        : {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
      body: isFormData
        ? data  // FormData: 直接传递
        : data
          ? JSON.stringify(data)  // 其他: JSON序列化
          : undefined,
    });
  }

  /**
   * PUT请求
   */
  async put<T>(
    url: string,
    data?: unknown,
    options?: RequestOptions
  ): Promise<T> {
    return this.request<T>(url, {
      ...options,
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * PATCH请求
   */
  async patch<T>(
    url: string,
    data?: unknown,
    options?: RequestOptions
  ): Promise<T> {
    return this.request<T>(url, {
      ...options,
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * DELETE请求
   */
  async delete<T>(url: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(url, { ...options, method: 'DELETE' });
  }

  // ==================== 用户管理API ====================

  /**
   * 获取所有用户（仅管理员）
   */
  async listUsers(): Promise<{ items: User[]; total: number }> {
    return this.get('/users');
  }

  /**
   * 创建用户（仅管理员）
   */
  async createUser(username: string, password: string): Promise<User> {
    return this.post('/users', { username, password });
  }

  /**
   * 删除用户（仅管理员）
   */
  async deleteUser(userId: number): Promise<void> {
    return this.delete(`/users/${userId}`);
  }

  /**
   * 修改密码
   */
  async changePassword(
    oldPassword: string,
    newPassword: string
  ): Promise<{ message: string }> {
    return this.put('/auth/change-password', {
      old_password: oldPassword,
      new_password: newPassword,
    });
  }

  // ==================== 知识库权限API ====================

  /**
   * 修改知识库可见性
   */
  async updateKBVisibility(
    kbId: string,
    visibility: 'private' | 'public' | 'shared'
  ): Promise<any> {
    return this.put(`/knowledge-bases/${kbId}/visibility`, { visibility });
  }

  /**
   * 查看知识库权限列表
   */
  async listKBPermissions(kbId: string): Promise<{
    permissions: Array<{
      id: number;
      kb_id: string;
      user_id: number;
      username: string;
      permission_type: 'read' | 'write';
      granted_by: number;
      created_at: string;
    }>;
  }> {
    return this.get(`/knowledge-bases/${kbId}/permissions`);
  }

  /**
   * 授予或更新知识库权限
   */
  async grantKBPermission(
    kbId: string,
    username: string,
    permissionType: 'read' | 'write'
  ): Promise<any> {
    return this.post(`/knowledge-bases/${kbId}/permissions`, {
      username,
      permission_type: permissionType,
    });
  }

  /**
   * 撤销知识库权限
   */
  async revokeKBPermission(kbId: string, userId: number): Promise<void> {
    return this.delete(`/knowledge-bases/${kbId}/permissions/${userId}`);
  }
}

export const apiClient = new ApiClient();

// ==================== 兼容性导出（为旧代码提供支持） ====================

export const knowledgeBaseAPI = {
  async list(params?: { page?: number; page_size?: number }) {
    const query = new URLSearchParams();
    if (params?.page) query.append('page', params.page.toString());
    if (params?.page_size) query.append('page_size', params.page_size.toString());
    return apiClient.get<{ items: any[]; meta: any }>(`/knowledge-bases?${query}`);
  },
  async get(id: string) {
    return apiClient.get(`/knowledge-bases/${id}`);
  },
  async create(data: any) {
    return apiClient.post('/knowledge-bases', data);
  },
  async update(id: string, data: any) {
    return apiClient.put(`/knowledge-bases/${id}`, data);
  },
  async delete(id: string) {
    return apiClient.delete(`/knowledge-bases/${id}`);
  },
};

export const documentAPI = {
  async list(params: { kb_id: string; page?: number; page_size?: number }) {
    const query = new URLSearchParams();
    query.append('kb_id', params.kb_id);
    if (params.page) query.append('page', params.page.toString());
    if (params.page_size) query.append('page_size', params.page_size.toString());
    return apiClient.get<{ items: any[]; meta: any }>(`/documents?${query}`);
  },
  async upload(kbId: string, file: File) {
    const formData = new FormData();
    formData.append('file', file);
    // kb_id 作为 query 参数传递，而不是在 FormData 中
    // apiClient.post 会自动识别 FormData 并正确处理
    return apiClient.post(`/documents?kb_id=${kbId}`, formData);
  },
  async delete(id: string) {
    return apiClient.delete(`/documents/${id}`);
  },
};

export const syncTaskAPI = {
  async list(params: { kb_id: string; limit?: number }) {
    const query = new URLSearchParams();
    query.append('kb_id', params.kb_id);
    if (params.limit) query.append('limit', params.limit.toString());
    return apiClient.get<{ items: any[]; meta: any }>(`/sync-tasks?${query}`);
  },
  async create(data: { kb_id: string; task_type: string; document_ids?: string[] }) {
    return apiClient.post('/sync-tasks', data);
  },
  async get(id: string) {
    return apiClient.get(`/sync-tasks/${id}`);
  },
  async cancel(id: string) {
    return apiClient.post(`/sync-tasks/${id}/cancel`);
  },
};

export const queryAPI = {
  /**
   * 流式查询接口（SSE）
   * 返回 ReadableStream 用于处理服务器推送事件
   */
  async stream(kbId: string, queryText: string): Promise<ReadableStream<Uint8Array>> {
    const token = authService.getToken();
    if (!token) {
      throw new Error('未登录，请先登录');
    }

    // 构建查询参数
    const params = new URLSearchParams();
    params.append('kb_id', kbId);
    params.append('query', queryText);

    // 发起流式请求
    const baseURL = process.env.NEXT_PUBLIC_API_URL || '/api/v1';
    const response = await fetch(`${baseURL}/query/stream?${params}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '查询失败' }));
      throw new Error(error.detail || `查询失败: ${response.status}`);
    }

    if (!response.body) {
      throw new Error('响应没有body');
    }

    return response.body;
  },
};
