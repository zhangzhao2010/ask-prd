# 认证和授权系统 - 使用示例

## 目录

- [基础认证流程](#基础认证流程)
- [知识库管理示例](#知识库管理示例)
- [权限管理示例](#权限管理示例)
- [前端集成示例](#前端集成示例)

---

## 基础认证流程

### 示例1：完整的登录流程

```bash
# 1. 用户登录
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "password123"
  }'

# 响应
{
  "access_token": "eyJhbGc...xyz",
  "token_type": "bearer",
  "user": {
    "id": 2,
    "username": "alice",
    "role": "user",
    "is_active": true,
    "created_at": "2025-11-11T10:00:00",
    "updated_at": "2025-11-11T10:00:00"
  }
}

# 2. 保存token（前端代码示例）
const token = response.access_token;
localStorage.setItem('access_token', token);

# 3. 使用token访问API
curl -X GET http://localhost:8000/api/v1/knowledge-bases \
  -H "Authorization: Bearer eyJhbGc...xyz"
```

---

### 示例2：管理员创建用户流程

```bash
# 1. 管理员登录
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' \
  | jq -r '.access_token')

# 2. 创建新用户
curl -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "bob",
    "password": "secure_pass_456"
  }'

# 响应
{
  "id": 3,
  "username": "bob",
  "role": "user",
  "is_active": true,
  "created_at": "2025-11-11T11:00:00",
  "updated_at": "2025-11-11T11:00:00"
}

# 3. 新用户登录测试
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "bob",
    "password": "secure_pass_456"
  }'
```

---

## 知识库管理示例

### 示例3：创建知识库并管理可见性

```bash
# 获取用户token
ALICE_TOKEN="eyJhbGc...xyz"

# 1. 创建私有知识库
KB_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/knowledge-bases \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice的产品文档",
    "description": "产品需求文档库"
  }')

KB_ID=$(echo $KB_RESPONSE | jq -r '.id')
echo "创建的知识库ID: $KB_ID"

# 2. 查看知识库详情
curl -X GET http://localhost:8000/api/v1/knowledge-bases/$KB_ID \
  -H "Authorization: Bearer $ALICE_TOKEN"

# 响应
{
  "id": "kb-xxx",
  "name": "Alice的产品文档",
  "description": "产品需求文档库",
  "visibility": "private",  // 默认私有
  "owner_id": 2,
  "status": "active",
  ...
}

# 3. 修改为公开
curl -X PUT http://localhost:8000/api/v1/knowledge-bases/$KB_ID/visibility \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"visibility": "public"}'

# 4. 验证：其他用户现在可以看到
BOB_TOKEN="eyJhbGc...abc"
curl -X GET http://localhost:8000/api/v1/knowledge-bases \
  -H "Authorization: Bearer $BOB_TOKEN"
# Bob的列表中会出现Alice的知识库
```

---

### 示例4：文档上传和权限验证

```bash
# Alice上传文档到自己的知识库
curl -X POST "http://localhost:8000/api/v1/documents?kb_id=$KB_ID" \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  -F "file=@/path/to/document.pdf"

# 响应
{
  "id": "doc-xxx",
  "kb_id": "kb-xxx",
  "filename": "document.pdf",
  "status": "uploaded",
  ...
}

# Bob尝试上传文档（如果知识库是public且无write权限）
curl -X POST "http://localhost:8000/api/v1/documents?kb_id=$KB_ID" \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -F "file=@/path/to/document.pdf"

# 响应 403
{
  "detail": "Write permission required"
}

# Bob可以查看文档列表（因为是public）
curl -X GET "http://localhost:8000/api/v1/documents?kb_id=$KB_ID" \
  -H "Authorization: Bearer $BOB_TOKEN"
# 成功返回文档列表
```

---

## 权限管理示例

### 示例5：共享知识库给团队

```bash
# 场景：Alice创建知识库并共享给团队成员

# 1. 创建知识库（默认private）
KB_ID=$(curl -s -X POST http://localhost:8000/api/v1/knowledge-bases \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "团队协作文档", "description": "项目文档"}' \
  | jq -r '.id')

# 2. 修改为shared
curl -X PUT http://localhost:8000/api/v1/knowledge-bases/$KB_ID/visibility \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"visibility": "shared"}'

# 3. 授予Bob读权限
curl -X POST http://localhost:8000/api/v1/knowledge-bases/$KB_ID/permissions \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "bob",
    "permission_type": "read"
  }'

# 4. 授予Charlie写权限
curl -X POST http://localhost:8000/api/v1/knowledge-bases/$KB_ID/permissions \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "charlie",
    "permission_type": "write"
  }'

# 5. 查看权限列表
curl -X GET http://localhost:8000/api/v1/knowledge-bases/$KB_ID/permissions \
  -H "Authorization: Bearer $ALICE_TOKEN"

# 响应
{
  "permissions": [
    {
      "id": 1,
      "kb_id": "kb-xxx",
      "user_id": 3,
      "username": "bob",
      "permission_type": "read",
      "granted_by": 2,
      "created_at": "2025-11-11T12:00:00"
    },
    {
      "id": 2,
      "kb_id": "kb-xxx",
      "user_id": 4,
      "username": "charlie",
      "permission_type": "write",
      "granted_by": 2,
      "created_at": "2025-11-11T12:01:00"
    }
  ]
}
```

---

### 示例6：权限升级和降级

```bash
# 场景：Bob需要临时编辑文档

# 1. 查看Bob当前权限（read）
curl -X GET http://localhost:8000/api/v1/knowledge-bases/$KB_ID/permissions \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  | jq '.permissions[] | select(.username=="bob")'

# 2. 升级Bob为write权限
curl -X POST http://localhost:8000/api/v1/knowledge-bases/$KB_ID/permissions \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "bob",
    "permission_type": "write"
  }'

# 3. Bob上传文档（现在可以了）
curl -X POST "http://localhost:8000/api/v1/documents?kb_id=$KB_ID" \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -F "file=@/path/to/document.pdf"
# 成功

# 4. 编辑完成后，降级回read
curl -X POST http://localhost:8000/api/v1/knowledge-bases/$KB_ID/permissions \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "bob",
    "permission_type": "read"
  }'

# 5. 验证：Bob再次尝试上传
curl -X POST "http://localhost:8000/api/v1/documents?kb_id=$KB_ID" \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -F "file=@/path/to/document.pdf"
# 返回 403
```

---

## 前端集成示例

### 示例7：React前端完整集成

```javascript
// src/services/auth.js

class AuthService {
  constructor() {
    this.baseURL = 'http://localhost:8000/api/v1';
  }

  // 登录
  async login(username, password) {
    const response = await fetch(`${this.baseURL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    if (!response.ok) {
      throw new Error('Login failed');
    }

    const data = await response.json();
    // 保存token
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('user', JSON.stringify(data.user));
    return data;
  }

  // 登出
  logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
  }

  // 获取当前用户
  getCurrentUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  }

  // 检查是否登录
  isAuthenticated() {
    return !!localStorage.getItem('access_token');
  }

  // 检查是否管理员
  isAdmin() {
    const user = this.getCurrentUser();
    return user && user.role === 'admin';
  }

  // 获取token
  getToken() {
    return localStorage.getItem('access_token');
  }
}

export default new AuthService();
```

```javascript
// src/services/api.js

import authService from './auth';

class ApiService {
  constructor() {
    this.baseURL = 'http://localhost:8000/api/v1';
  }

  // 通用请求方法
  async request(url, options = {}) {
    const token = authService.getToken();

    const headers = {
      ...options.headers,
      'Authorization': `Bearer ${token}`
    };

    const response = await fetch(`${this.baseURL}${url}`, {
      ...options,
      headers
    });

    // Token过期处理
    if (response.status === 401) {
      authService.logout();
      window.location.href = '/login';
      throw new Error('Token expired');
    }

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Request failed');
    }

    // 204 No Content
    if (response.status === 204) {
      return null;
    }

    return response.json();
  }

  // 知识库API
  async listKnowledgeBases() {
    return this.request('/knowledge-bases');
  }

  async createKnowledgeBase(name, description) {
    return this.request('/knowledge-bases', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description })
    });
  }

  async updateKBVisibility(kbId, visibility) {
    return this.request(`/knowledge-bases/${kbId}/visibility`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ visibility })
    });
  }

  // 权限API
  async listKBPermissions(kbId) {
    return this.request(`/knowledge-bases/${kbId}/permissions`);
  }

  async grantPermission(kbId, username, permissionType) {
    return this.request(`/knowledge-bases/${kbId}/permissions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, permission_type: permissionType })
    });
  }

  async revokePermission(kbId, userId) {
    return this.request(`/knowledge-bases/${kbId}/permissions/${userId}`, {
      method: 'DELETE'
    });
  }
}

export default new ApiService();
```

```javascript
// src/components/Login.jsx

import React, { useState } from 'react';
import authService from '../services/auth';

function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      await authService.login(username, password);
      window.location.href = '/dashboard';
    } catch (err) {
      setError('用户名或密码错误');
    }
  };

  return (
    <div>
      <h2>登录</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="用户名"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          type="password"
          placeholder="密码"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button type="submit">登录</button>
        {error && <div className="error">{error}</div>}
      </form>
    </div>
  );
}

export default Login;
```

```javascript
// src/components/ProtectedRoute.jsx

import React from 'react';
import { Navigate } from 'react-router-dom';
import authService from '../services/auth';

function ProtectedRoute({ children, requireAdmin = false }) {
  if (!authService.isAuthenticated()) {
    return <Navigate to="/login" />;
  }

  if (requireAdmin && !authService.isAdmin()) {
    return <Navigate to="/forbidden" />;
  }

  return children;
}

export default ProtectedRoute;
```

```javascript
// src/App.jsx

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import UserManagement from './components/UserManagement';
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />

        <Route path="/dashboard" element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        } />

        <Route path="/users" element={
          <ProtectedRoute requireAdmin={true}>
            <UserManagement />
          </ProtectedRoute>
        } />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
```

---

### 示例8：权限管理UI组件

```javascript
// src/components/PermissionManager.jsx

import React, { useState, useEffect } from 'react';
import apiService from '../services/api';

function PermissionManager({ kbId }) {
  const [permissions, setPermissions] = useState([]);
  const [newUsername, setNewUsername] = useState('');
  const [newPermType, setNewPermType] = useState('read');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPermissions();
  }, [kbId]);

  const loadPermissions = async () => {
    try {
      const data = await apiService.listKBPermissions(kbId);
      setPermissions(data.permissions);
    } catch (err) {
      console.error('加载权限失败', err);
    } finally {
      setLoading(false);
    }
  };

  const handleGrant = async (e) => {
    e.preventDefault();
    try {
      await apiService.grantPermission(kbId, newUsername, newPermType);
      alert('权限授予成功');
      setNewUsername('');
      loadPermissions();
    } catch (err) {
      alert('授予失败: ' + err.message);
    }
  };

  const handleRevoke = async (userId, username) => {
    if (!confirm(`确定撤销 ${username} 的权限？`)) return;

    try {
      await apiService.revokePermission(kbId, userId);
      alert('权限已撤销');
      loadPermissions();
    } catch (err) {
      alert('撤销失败: ' + err.message);
    }
  };

  if (loading) return <div>加载中...</div>;

  return (
    <div>
      <h3>权限管理</h3>

      {/* 权限列表 */}
      <table>
        <thead>
          <tr>
            <th>用户名</th>
            <th>权限类型</th>
            <th>授予时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {permissions.map(perm => (
            <tr key={perm.id}>
              <td>{perm.username}</td>
              <td>{perm.permission_type}</td>
              <td>{new Date(perm.created_at).toLocaleString()}</td>
              <td>
                <button onClick={() => handleRevoke(perm.user_id, perm.username)}>
                  撤销
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* 添加权限表单 */}
      <h4>添加新权限</h4>
      <form onSubmit={handleGrant}>
        <input
          type="text"
          placeholder="用户名"
          value={newUsername}
          onChange={(e) => setNewUsername(e.target.value)}
          required
        />
        <select value={newPermType} onChange={(e) => setNewPermType(e.target.value)}>
          <option value="read">只读</option>
          <option value="write">管理</option>
        </select>
        <button type="submit">授予权限</button>
      </form>
    </div>
  );
}

export default PermissionManager;
```

---

## 下一步

继续阅读：

- **[故障排查](./auth-troubleshooting.md)** - 常见问题和解决方法
- **[权限管理指南](./auth-permission-guide.md)** - 权限管理最佳实践
- **[系统概述](./auth-system-overview.md)** - 回到系统概述
