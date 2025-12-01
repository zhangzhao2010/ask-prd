# 认证和授权系统 - 故障排查

## 目录

- [认证问题](#认证问题)
- [权限问题](#权限问题)
- [Token问题](#token问题)
- [数据库问题](#数据库问题)
- [系统配置问题](#系统配置问题)

---

## 认证问题

### 问题1：登录失败 - 401 Unauthorized

**症状**：
```json
{
  "detail": "Incorrect username or password"
}
```

**可能原因**：

1. **用户名或密码错误**
   - 检查用户名拼写
   - 检查密码是否正确
   - 确认是否有大小写问题

2. **用户不存在**
   ```bash
   # 管理员查询用户列表
   curl -X GET http://localhost:8000/api/v1/users \
     -H "Authorization: Bearer ADMIN_TOKEN"
   ```

3. **用户被禁用**
   ```bash
   # 检查用户状态
   curl -X GET http://localhost:8000/api/v1/auth/me \
     -H "Authorization: Bearer USER_TOKEN"
   # 查看 is_active 字段
   ```

**解决方法**：

```bash
# 方法1：重置密码（需要管理员）
# 当前系统未实现密码重置，需要删除用户重建

# 方法2：删除并重新创建用户
curl -X DELETE http://localhost:8000/api/v1/users/{user_id} \
  -H "Authorization: Bearer ADMIN_TOKEN"

curl -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "new_password"}'
```

---

### 问题2：登录后无法访问任何API

**症状**：
- 登录成功
- 后续请求返回403或401

**可能原因**：

1. **Token未正确保存**
   ```javascript
   // 检查前端代码
   console.log(localStorage.getItem('access_token')); // 是否存在？
   ```

2. **Token未正确发送**
   ```bash
   # 检查请求头
   curl -v -X GET http://localhost:8000/api/v1/knowledge-bases \
     -H "Authorization: Bearer YOUR_TOKEN"
   # 查看请求头是否包含 Authorization
   ```

3. **Token格式错误**
   ```bash
   # 正确格式：Bearer {token}
   # 错误格式：{token}
   # 错误格式：Token {token}
   ```

**解决方法**：

```javascript
// 前端正确使用Token
const token = localStorage.getItem('access_token');

fetch('/api/v1/knowledge-bases', {
  headers: {
    'Authorization': `Bearer ${token}` // 注意Bearer前缀和空格
  }
})
```

---

## 权限问题

### 问题3：无法访问知识库 - 404 Not Found

**症状**：
```json
{
  "detail": "Knowledge base not found"
}
```

**可能原因**：

1. **知识库真的不存在**
   ```bash
   # 管理员查询所有知识库
   curl -X GET http://localhost:8000/api/v1/knowledge-bases \
     -H "Authorization: Bearer ADMIN_TOKEN"
   ```

2. **知识库是私有的，用户无权限**
   - 私有知识库对无权限用户返回404（假装不存在）
   - 检查知识库的visibility和owner_id

3. **知识库ID错误**
   - 检查KB ID是否正确
   - 注意ID格式：`kb-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

**解决方法**：

```bash
# 1. 确认知识库存在（使用管理员账号）
curl -X GET http://localhost:8000/api/v1/knowledge-bases/{kb_id} \
  -H "Authorization: Bearer ADMIN_TOKEN"

# 2. 检查可见性
# 如果是private，需要所有者修改为shared或public

# 3. 如果是shared，需要授予权限
curl -X POST http://localhost:8000/api/v1/knowledge-bases/{kb_id}/permissions \
  -H "Authorization: Bearer OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "permission_type": "read"}'
```

---

### 问题4：无法上传文档 - 403 Forbidden

**症状**：
```json
{
  "detail": "Write permission required"
}
```

**可能原因**：

1. **用户只有read权限**
   ```bash
   # 查看权限
   curl -X GET http://localhost:8000/api/v1/knowledge-bases/{kb_id}/permissions \
     -H "Authorization: Bearer OWNER_TOKEN"
   ```

2. **知识库是public，用户未被授予write权限**
   - Public知识库默认只读
   - 需要明确授予write权限

**解决方法**：

```bash
# 所有者授予write权限
curl -X POST http://localhost:8000/api/v1/knowledge-bases/{kb_id}/permissions \
  -H "Authorization: Bearer OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "permission_type": "write"}'

# 或者：修改为shared并授予权限
curl -X PUT http://localhost:8000/api/v1/knowledge-bases/{kb_id}/visibility \
  -H "Authorization: Bearer OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"visibility": "shared"}'

curl -X POST http://localhost:8000/api/v1/knowledge-bases/{kb_id}/permissions \
  -H "Authorization: Bearer OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "permission_type": "write"}'
```

---

### 问题5：无法删除知识库 - 403 Forbidden

**症状**：
```json
{
  "detail": "Only the owner can perform this operation"
}
```

**可能原因**：

- 只有所有者和管理员可以删除知识库
- 即使用户有write权限，也不能删除

**解决方法**：

```bash
# 方案1：使用所有者账号删除
curl -X DELETE http://localhost:8000/api/v1/knowledge-bases/{kb_id} \
  -H "Authorization: Bearer OWNER_TOKEN"

# 方案2：使用管理员账号删除
curl -X DELETE http://localhost:8000/api/v1/knowledge-bases/{kb_id} \
  -H "Authorization: Bearer ADMIN_TOKEN"

# 如需转移所有权（当前系统未实现）
# 需要：
# 1. 管理员创建新知识库
# 2. 复制文档
# 3. 删除旧知识库
```

---

### 问题6：授予权限失败 - 404 User not found

**症状**：
```json
{
  "detail": "User not found"
}
```

**可能原因**：

1. **用户名拼写错误**
   - 检查username是否正确

2. **用户不存在**
   ```bash
   # 查询所有用户（管理员）
   curl -X GET http://localhost:8000/api/v1/users \
     -H "Authorization: Bearer ADMIN_TOKEN"
   ```

**解决方法**：

```bash
# 1. 确认用户存在
curl -X GET http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  | jq '.users[] | select(.username=="alice")'

# 2. 如果不存在，创建用户
curl -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "password123"}'

# 3. 再次授予权限
curl -X POST http://localhost:8000/api/v1/knowledge-bases/{kb_id}/permissions \
  -H "Authorization: Bearer OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "permission_type": "read"}'
```

---

## Token问题

### 问题7：Token过期 - 401 Unauthorized

**症状**：
- 之前正常的Token突然失效
- 返回401错误

**原因**：
- Token默认有效期7天
- 超过有效期后自动失效

**解决方法**：

```javascript
// 前端处理Token过期
async function apiCall(url, options) {
  const response = await fetch(url, options);

  if (response.status === 401) {
    // Token过期，清除并跳转登录
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    window.location.href = '/login';
    throw new Error('Token expired, please login again');
  }

  return response.json();
}
```

**预防措施**：

1. 在前端检查Token是否即将过期
2. 提前提示用户重新登录
3. 未来可实现refresh token机制

---

### 问题8：Token无效 - 401 Invalid token

**症状**：
```json
{
  "detail": "Could not validate credentials"
}
```

**可能原因**：

1. **Token被篡改**
   - JWT签名验证失败

2. **Token格式错误**
   - 不是有效的JWT格式

3. **Secret Key不匹配**
   - 服务器重启后使用了不同的Secret Key

**解决方法**：

```bash
# 1. 检查Token格式
echo "YOUR_TOKEN" | base64 -d
# 应该包含三部分，用点分隔

# 2. 重新登录获取新Token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "password123"}'

# 3. 确认服务器配置
# 检查 .env 文件中的 JWT_SECRET_KEY
# 生产环境确保Secret Key不变
```

---

## 数据库问题

### 问题9：数据库锁定 - Database is locked

**症状**：
- SQLite报错：database is locked
- 写操作失败

**原因**：
- SQLite不支持高并发写
- 多个进程同时写数据库

**解决方法**：

```bash
# 方案1：重启服务
pkill -f "python -m app.main"
python -m app.main

# 方案2：检查是否有多个实例运行
ps aux | grep "python -m app.main"
# 只保留一个

# 方案3：长期解决 - 迁移到PostgreSQL
# 编辑 app/core/database.py
# 修改数据库连接字符串
```

---

### 问题10：外键约束失败

**症状**：
- 创建知识库失败
- 授予权限失败
- 报错：FOREIGN KEY constraint failed

**可能原因**：

1. **owner_id或user_id指向不存在的用户**
   ```bash
   # 检查用户是否存在
   curl -X GET http://localhost:8000/api/v1/users \
     -H "Authorization: Bearer ADMIN_TOKEN"
   ```

2. **kb_id指向不存在的知识库**

**解决方法**：

```bash
# 1. 确认关联的用户存在
# 2. 确认关联的知识库存在
# 3. 如果数据不一致，重新初始化数据库

python scripts/migrate_add_users_and_permissions.py --yes
```

---

## 系统配置问题

### 问题11：CORS错误（前端）

**症状**：
- 浏览器控制台报错：CORS policy
- 前端无法访问后端API

**原因**：
- 前端域名未在CORS白名单中

**解决方法**：

```python
# 编辑 backend/app/main.py

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # 添加前端地址
        "http://127.0.0.1:3000",
        "https://your-domain.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### 问题12：JWT Secret Key泄露

**症状**：
- Secret Key被提交到代码仓库
- 安全风险

**解决方法**：

```bash
# 1. 立即修改Secret Key
# 生成新的强密钥
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 2. 更新 .env 文件
echo "JWT_SECRET_KEY=NEW_STRONG_SECRET_KEY" >> backend/.env

# 3. 从Git历史中删除（如果已提交）
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch backend/.env" \
  --prune-empty --tag-name-filter cat -- --all

# 4. 强制推送
git push origin --force --all

# 5. 通知所有用户重新登录
# （修改Secret Key后，所有旧Token失效）
```

---

### 问题13：日志中看到Token

**症状**：
- 日志文件包含完整Token
- 安全风险

**解决方法**：

```python
# 编辑 app/core/logging.py
# 过滤敏感信息

import re

def sanitize_log(message):
    # 替换Token
    message = re.sub(
        r'Bearer [A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_.+/=]+',
        'Bearer ***',
        message
    )
    # 替换密码
    message = re.sub(
        r'"password"\s*:\s*"[^"]*"',
        '"password": "***"',
        message
    )
    return message
```

---

## 诊断工具

### 检查系统状态

```bash
# 1. 检查服务是否运行
curl http://localhost:8000/health

# 2. 检查数据库
sqlite3 data/ask-prd.db "SELECT * FROM users;"

# 3. 检查日志
tail -f logs/app.log

# 4. 测试登录
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' \
  -v
```

### 数据库诊断

```bash
# 查看所有表
sqlite3 data/ask-prd.db ".tables"

# 查看用户
sqlite3 data/ask-prd.db "SELECT id, username, role, is_active FROM users;"

# 查看知识库
sqlite3 data/ask-prd.db "SELECT id, name, visibility, owner_id FROM knowledge_bases;"

# 查看权限
sqlite3 data/ask-prd.db "SELECT * FROM knowledge_base_permissions;"
```

### Token诊断

```bash
# 解码Token（仅查看payload，不验证签名）
echo "YOUR_TOKEN" | cut -d'.' -f2 | base64 -d | jq

# 输出示例：
# {
#   "sub": "2",
#   "exp": 1639555555
# }

# 检查过期时间
python -c "import datetime; print(datetime.datetime.fromtimestamp(1639555555))"
```

---

## 常见错误速查表

| 错误码 | 错误信息 | 原因 | 解决方法 |
|-------|---------|------|---------|
| 400 | Bad Request | 请求参数错误 | 检查请求体格式 |
| 401 | Incorrect username or password | 用户名或密码错误 | 确认凭证 |
| 401 | Could not validate credentials | Token无效 | 重新登录 |
| 403 | Forbidden | 未提供Token | 添加Authorization头 |
| 403 | Write permission required | 权限不足 | 授予write权限 |
| 403 | Only the owner can... | 仅所有者操作 | 使用所有者账号 |
| 404 | Knowledge base not found | KB不存在或无权限 | 检查ID和权限 |
| 404 | User not found | 用户不存在 | 确认用户名 |
| 500 | Internal Server Error | 服务器错误 | 查看日志 |

---

## 获取帮助

如果以上方法无法解决问题：

1. **查看日志**：`tail -f logs/app.log`
2. **查看测试脚本**：`backend/scripts/test_auth_and_permissions.py`
3. **运行测试**：`python scripts/test_auth_and_permissions.py`
4. **查看数据库**：使用上述诊断SQL
5. **提交Issue**：记录详细错误信息和复现步骤

---

## 下一步

继续阅读：

- **[系统概述](./auth-system-overview.md)** - 回到系统概述
- **[API接口文档](./auth-api-reference.md)** - API使用说明
- **[使用示例](./auth-examples.md)** - 代码示例
