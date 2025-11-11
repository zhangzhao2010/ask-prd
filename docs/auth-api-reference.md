# 认证和授权系统 - API接口文档

## 目录

- [认证API](#认证api)
- [用户管理API](#用户管理api)
- [知识库权限管理API](#知识库权限管理api)
- [其他已修改的API](#其他已修改的api)

---

## 认证API

### 1. 用户登录

**接口**: `POST /api/v1/auth/login`

**说明**: 用户登录，获取JWT Token

**请求头**: 无需认证

**请求体**:

```json
{
  "username": "admin",
  "password": "admin123"
}
```

**响应 200**:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin",
    "is_active": true,
    "created_at": "2025-11-11T10:00:00",
    "updated_at": "2025-11-11T10:00:00"
  }
}
```

**错误响应**:

- `401 Unauthorized`: 用户名或密码错误

```json
{
  "detail": "Incorrect username or password"
}
```

- `400 Bad Request`: 用户被禁用

```json
{
  "detail": "User is disabled"
}
```

**cURL示例**:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

---

### 2. 获取当前用户信息

**接口**: `GET /api/v1/auth/me`

**说明**: 获取当前登录用户的详细信息

**请求头**: 需要认证

```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

**响应 200**:

```json
{
  "id": 1,
  "username": "admin",
  "role": "admin",
  "is_active": true,
  "created_at": "2025-11-11T10:00:00",
  "updated_at": "2025-11-11T10:00:00"
}
```

**错误响应**:

- `401 Unauthorized`: Token无效或过期
- `403 Forbidden`: 未提供Token

**cURL示例**:

```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 用户管理API

⚠️ **注意**: 以下所有API仅限管理员访问

### 1. 列出所有用户

**接口**: `GET /api/v1/users`

**说明**: 获取系统中所有用户列表（仅管理员）

**请求头**: 需要管理员Token

```
Authorization: Bearer ADMIN_TOKEN
```

**查询参数**: 无

**响应 200**:

```json
{
  "users": [
    {
      "id": 1,
      "username": "admin",
      "role": "admin",
      "is_active": true,
      "created_at": "2025-11-11T10:00:00",
      "updated_at": "2025-11-11T10:00:00"
    },
    {
      "id": 2,
      "username": "alice",
      "role": "user",
      "is_active": true,
      "created_at": "2025-11-11T10:05:00",
      "updated_at": "2025-11-11T10:05:00"
    }
  ]
}
```

**错误响应**:

- `403 Forbidden`: 非管理员访问

**cURL示例**:

```bash
curl -X GET http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

---

### 2. 创建用户

**接口**: `POST /api/v1/users`

**说明**: 创建新的普通用户（仅管理员）

**请求头**: 需要管理员Token

**请求体**:

```json
{
  "username": "alice",
  "password": "secure_password_123"
}
```

**字段说明**:

- `username`: 用户名，唯一，1-50个字符
- `password`: 密码，明文（系统会自动加密）

**响应 201**:

```json
{
  "id": 2,
  "username": "alice",
  "role": "user",
  "is_active": true,
  "created_at": "2025-11-11T10:05:00",
  "updated_at": "2025-11-11T10:05:00"
}
```

**错误响应**:

- `400 Bad Request`: 用户名已存在

```json
{
  "detail": "Username already exists"
}
```

- `403 Forbidden`: 非管理员访问

**cURL示例**:

```bash
curl -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "secure_password_123"
  }'
```

---

### 3. 删除用户

**接口**: `DELETE /api/v1/users/{user_id}`

**说明**: 删除指定用户及其所有相关数据（仅管理员）

**请求头**: 需要管理员Token

**路径参数**:

- `user_id`: 要删除的用户ID

**响应 204**: 无内容（删除成功）

**错误响应**:

- `404 Not Found`: 用户不存在
- `403 Forbidden`: 非管理员访问

**级联删除说明**:

删除用户会级联删除以下数据：
- 用户拥有的所有知识库
- 知识库下的所有文档、chunks
- 用户被授予的所有权限
- 用户的所有查询历史

**cURL示例**:

```bash
curl -X DELETE http://localhost:8000/api/v1/users/2 \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

---

## 知识库权限管理API

### 1. 修改知识库可见性

**接口**: `PUT /api/v1/knowledge-bases/{kb_id}/visibility`

**说明**: 修改知识库的可见性（仅所有者和管理员）

**请求头**: 需要认证

```
Authorization: Bearer OWNER_OR_ADMIN_TOKEN
```

**路径参数**:

- `kb_id`: 知识库ID

**请求体**:

```json
{
  "visibility": "public"
}
```

**可选值**:

- `private`: 私有（仅所有者可见）
- `public`: 公开（所有人可见，默认只读）
- `shared`: 共享（仅被授权用户可见）

**响应 200**:

```json
{
  "id": "kb-xxx",
  "name": "我的知识库",
  "description": "描述",
  "visibility": "public",
  "owner_id": 2,
  "status": "active",
  "created_at": "2025-11-11T10:00:00",
  "updated_at": "2025-11-11T10:10:00",
  ...
}
```

**错误响应**:

- `403 Forbidden`: 非所有者尝试修改
- `404 Not Found`: 知识库不存在

**cURL示例**:

```bash
curl -X PUT http://localhost:8000/api/v1/knowledge-bases/kb-xxx/visibility \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "visibility": "public"
  }'
```

---

### 2. 查看知识库权限列表

**接口**: `GET /api/v1/knowledge-bases/{kb_id}/permissions`

**说明**: 查看知识库的共享权限列表（仅所有者和管理员）

**请求头**: 需要认证

**路径参数**:

- `kb_id`: 知识库ID

**响应 200**:

```json
{
  "permissions": [
    {
      "id": 1,
      "kb_id": "kb-xxx",
      "user_id": 3,
      "username": "bob",
      "permission_type": "read",
      "granted_by": 2,
      "created_at": "2025-11-11T10:15:00"
    },
    {
      "id": 2,
      "kb_id": "kb-xxx",
      "user_id": 4,
      "username": "charlie",
      "permission_type": "write",
      "granted_by": 2,
      "created_at": "2025-11-11T10:20:00"
    }
  ]
}
```

**字段说明**:

- `permission_type`: 权限类型（`read` 或 `write`）
- `granted_by`: 授权人ID

**错误响应**:

- `403 Forbidden`: 非所有者尝试查看
- `404 Not Found`: 知识库不存在

**cURL示例**:

```bash
curl -X GET http://localhost:8000/api/v1/knowledge-bases/kb-xxx/permissions \
  -H "Authorization: Bearer OWNER_TOKEN"
```

---

### 3. 添加或更新知识库权限

**接口**: `POST /api/v1/knowledge-bases/{kb_id}/permissions`

**说明**: 授予用户访问权限，如果已存在则更新（仅所有者和管理员）

**请求头**: 需要认证

**路径参数**:

- `kb_id`: 知识库ID

**请求体**:

```json
{
  "username": "bob",
  "permission_type": "read"
}
```

**字段说明**:

- `username`: 要授权的用户名（不是user_id）
- `permission_type`: 权限类型
  - `read`: 只读（查看文档、问答）
  - `write`: 管理（上传/删除文档、修改知识库）

**响应 201** (创建新权限):

```json
{
  "id": 1,
  "kb_id": "kb-xxx",
  "user_id": 3,
  "username": "bob",
  "permission_type": "read",
  "granted_by": 2,
  "created_at": "2025-11-11T10:15:00"
}
```

**响应 200** (更新已有权限):

```json
{
  "id": 1,
  "kb_id": "kb-xxx",
  "user_id": 3,
  "username": "bob",
  "permission_type": "write",
  "granted_by": 2,
  "created_at": "2025-11-11T10:15:00"
}
```

**注意**: 该接口是**upsert**操作（存在则更新，不存在则创建），因此可能返回200或201。

**错误响应**:

- `404 Not Found`: 用户名不存在或知识库不存在
- `400 Bad Request`: 尝试给所有者添加权限
- `403 Forbidden`: 非所有者尝试添加权限

**cURL示例**:

```bash
# 授予读权限
curl -X POST http://localhost:8000/api/v1/knowledge-bases/kb-xxx/permissions \
  -H "Authorization: Bearer OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "bob",
    "permission_type": "read"
  }'

# 升级为写权限（再次调用相同接口）
curl -X POST http://localhost:8000/api/v1/knowledge-bases/kb-xxx/permissions \
  -H "Authorization: Bearer OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "bob",
    "permission_type": "write"
  }'
```

---

### 4. 移除知识库权限

**接口**: `DELETE /api/v1/knowledge-bases/{kb_id}/permissions/{user_id}`

**说明**: 撤销用户的访问权限（仅所有者和管理员）

**请求头**: 需要认证

**路径参数**:

- `kb_id`: 知识库ID
- `user_id`: 要撤销权限的用户ID（注意是user_id，不是username）

**响应 204**: 无内容（删除成功）

**错误响应**:

- `403 Forbidden`: 非所有者尝试删除权限
- `404 Not Found`: 知识库不存在

**注意**: 即使该用户没有权限记录，删除操作也会成功返回204（幂等性）。

**cURL示例**:

```bash
curl -X DELETE http://localhost:8000/api/v1/knowledge-bases/kb-xxx/permissions/3 \
  -H "Authorization: Bearer OWNER_TOKEN"
```

---

## 其他已修改的API

以下API已添加认证和权限检查，但接口签名未变化：

### 知识库API

| 接口 | 方法 | 权限要求 | 说明 |
|-----|------|---------|------|
| `/api/v1/knowledge-bases` | GET | 需登录 | 列出有权限的知识库 |
| `/api/v1/knowledge-bases` | POST | 需登录 | 创建知识库（自动设为所有者） |
| `/api/v1/knowledge-bases/{kb_id}` | GET | READ权限 | 查看知识库详情 |
| `/api/v1/knowledge-bases/{kb_id}` | PATCH | WRITE权限 | 修改知识库信息 |
| `/api/v1/knowledge-bases/{kb_id}` | DELETE | 仅所有者/管理员 | 删除知识库 |

**变化说明**:

1. `GET /api/v1/knowledge-bases` 现在会根据用户权限过滤：
   - 管理员：看到所有知识库
   - 普通用户：看到自己的 + 公开的 + 被共享的

2. `POST /api/v1/knowledge-bases` 创建时自动设置：
   - `owner_id`: 当前用户ID
   - `visibility`: `private`（默认）

---

### 文档API

| 接口 | 方法 | 权限要求 | 说明 |
|-----|------|---------|------|
| `/api/v1/documents` | POST | WRITE权限 | 上传文档 |
| `/api/v1/documents` | GET | READ权限 | 列出文档 |
| `/api/v1/documents/{doc_id}` | GET | READ权限 | 查看文档详情 |
| `/api/v1/documents/{doc_id}` | DELETE | WRITE权限 | 删除文档 |
| `/api/v1/documents/{doc_id}/images/{filename}` | GET | READ权限 | 获取文档图片 |

**请求参数变化**:

所有文档API都需要提供 `kb_id` 查询参数，系统会先检查用户对该知识库的权限。

---

### 同步任务API

| 接口 | 方法 | 权限要求 | 说明 |
|-----|------|---------|------|
| `/api/v1/sync-tasks` | POST | WRITE权限 | 创建同步任务 |
| `/api/v1/sync-tasks` | GET | READ权限 | 列出同步任务 |
| `/api/v1/sync-tasks/{task_id}` | GET | READ权限 | 查看任务详情 |
| `/api/v1/sync-tasks/{task_id}/cancel` | POST | WRITE权限 | 取消任务 |

---

### 查询API

| 接口 | 方法 | 权限要求 | 说明 |
|-----|------|---------|------|
| `/api/v1/query/stream` | POST | READ权限 | 流式问答 |

**变化说明**:

- 查询会自动记录到 `query_history` 表，关联当前用户ID
- 查询参数需要提供 `kb_id`，系统会检查READ权限

---

## 通用错误响应格式

所有API的错误响应遵循统一格式：

```json
{
  "detail": "错误描述信息"
}
```

### 常见错误码和原因

| 状态码 | 原因 | 解决方法 |
|-------|------|---------|
| 400 | 请求参数错误 | 检查请求体是否符合要求 |
| 401 | Token无效或过期 | 重新登录获取新Token |
| 403 | 无权限访问 | 检查用户角色和知识库权限 |
| 404 | 资源不存在 | 检查ID是否正确，或是否有权限 |
| 500 | 服务器内部错误 | 查看服务器日志 |

---

## API使用最佳实践

### 1. Token管理

```javascript
// 前端示例：保存和使用Token

// 登录后保存Token
const loginResponse = await fetch('/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username, password })
});

const { access_token } = await loginResponse.json();
localStorage.setItem('access_token', access_token);

// 在后续请求中使用Token
const token = localStorage.getItem('access_token');
const response = await fetch('/api/v1/knowledge-bases', {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

### 2. 错误处理

```javascript
// 前端示例：统一错误处理

async function apiCall(url, options = {}) {
  const token = localStorage.getItem('access_token');

  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${token}`
    }
  });

  if (response.status === 401) {
    // Token过期，跳转到登录页
    localStorage.removeItem('access_token');
    window.location.href = '/login';
    return;
  }

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Request failed');
  }

  return response.json();
}
```

### 3. 权限检查

```javascript
// 前端示例：根据用户角色显示/隐藏功能

const user = await apiCall('/api/v1/auth/me');

if (user.role === 'admin') {
  // 显示用户管理按钮
  document.getElementById('user-management').style.display = 'block';
}

// 根据知识库可见性和权限显示操作按钮
const kb = await apiCall(`/api/v1/knowledge-bases/${kbId}`);

if (kb.owner_id === user.id || user.role === 'admin') {
  // 显示删除按钮
  document.getElementById('delete-kb-btn').style.display = 'block';
  // 显示权限管理按钮
  document.getElementById('manage-permissions-btn').style.display = 'block';
}
```

---

## 下一步

继续阅读：

- **[权限管理指南](./auth-permission-guide.md)** - 权限管理最佳实践
- **[使用示例](./auth-examples.md)** - 常见场景的完整示例
- **[故障排查](./auth-troubleshooting.md)** - 常见问题和解决方法
