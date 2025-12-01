# 认证和授权系统 - 概述

## 目录

- [系统简介](#系统简介)
- [核心特性](#核心特性)
- [快速开始](#快速开始)
- [核心概念](#核心概念)
- [系统架构](#系统架构)

---

## 系统简介

ASK-PRD 认证和授权系统是一个基于 JWT（JSON Web Token）的安全访问控制系统，支持多用户、多角色、细粒度的知识库权限管理。

### 技术栈

- **认证方式**: JWT (JSON Web Token)
- **密码加密**: Bcrypt (强加密算法)
- **Token有效期**: 7天（可配置）
- **授权模型**: RBAC（基于角色）+ ABAC（基于属性）

### 设计目标

1. **安全性**: 密码强加密、Token过期机制、权限严格验证
2. **灵活性**: 支持三级可见性、两级权限、灵活的共享机制
3. **易用性**: 清晰的权限模型、直观的API设计
4. **数据隔离**: 用户之间数据完全隔离，防止越权访问

---

## 核心特性

### 1. 用户系统

- ✅ 两种用户角色：**管理员（admin）** 和 **普通用户（user）**
- ✅ JWT Token认证，有效期7天
- ✅ 密码Bcrypt强加密存储
- ✅ 用户状态管理（激活/禁用）

### 2. 知识库可见性

支持三级可见性控制：

| 可见性类型 | 说明 | 谁可以访问 | 默认权限 |
|-----------|------|-----------|---------|
| **private** | 私有 | 仅所有者和管理员 | 所有者：全部权限 |
| **public** | 公开 | 所有登录用户 | 只读（除非明确授权写权限） |
| **shared** | 共享 | 所有者 + 被授权用户 | 根据权限表决定 |

### 3. 权限类型

支持两级权限：

| 权限类型 | 说明 | 可以执行的操作 |
|---------|------|--------------|
| **read** | 只读 | - 查看知识库详情<br>- 查看文档列表<br>- 查看文档内容<br>- 执行问答查询 |
| **write** | 管理 | - read权限的所有操作<br>- 上传文档<br>- 删除文档<br>- 修改知识库信息<br>- 创建同步任务 |

**注意**：删除知识库和管理权限（添加/删除共享用户）仅限所有者和管理员。

### 4. 管理员特权

管理员（admin角色）拥有以下特权：

- ✅ 访问和管理所有知识库（无视可见性）
- ✅ 创建和删除用户
- ✅ 查看所有用户列表
- ✅ 查看和修改所有知识库
- ✅ 访问系统级管理功能

---

## 快速开始

### 1. 系统初始化

首次启动系统时，会自动创建默认管理员账户：

```bash
cd backend
python scripts/migrate_add_users_and_permissions.py --yes
```

**默认管理员账户**：
- 用户名：`admin`
- 密码：`admin123`

⚠️ **重要**：首次登录后请立即修改默认密码！

### 2. 管理员登录

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

响应示例：

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

### 3. 使用Token访问API

获得Token后，在所有API请求的Header中携带：

```bash
curl -X GET http://localhost:8000/api/v1/knowledge-bases \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4. 创建普通用户（仅管理员）

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

## 核心概念

### 1. JWT Token

**什么是JWT？**

JWT（JSON Web Token）是一种开放标准（RFC 7519），用于在各方之间安全地传输信息。

**Token结构**：

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.  ← Header（算法和类型）
eyJzdWIiOiIxIiwiZXhwIjoxNjM5NTU1NTU1fQ.  ← Payload（用户信息和过期时间）
SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c   ← Signature（签名）
```

**Payload内容**：

```json
{
  "sub": "1",           // 用户ID（字符串格式）
  "exp": 1639555555     // 过期时间（Unix时间戳）
}
```

**Token有效期**：

- 默认：7天
- 配置文件：`backend/app/core/config.py` 中的 `jwt_access_token_expire_days`
- 过期后需要重新登录

### 2. 权限检查流程

当用户访问一个知识库时，系统按以下顺序检查权限：

```
1. 知识库是否存在？
   └─ 不存在 → 返回 404

2. 用户是管理员？
   └─ 是 → ✅ 允许访问（拥有所有权限）

3. 用户是所有者？
   └─ 是 → ✅ 允许访问（拥有所有权限）

4. 知识库可见性是什么？

   ├─ private（私有）
   │  └─ 非所有者/管理员 → ❌ 返回 404（假装不存在）

   ├─ public（公开）
   │  ├─ 请求读权限 → ✅ 允许
   │  └─ 请求写权限
   │     ├─ 检查权限表是否有write权限
   │     ├─ 有 → ✅ 允许
   │     └─ 无 → ❌ 返回 403

   └─ shared（共享）
      ├─ 检查权限表是否有记录
      ├─ 无记录 → ❌ 返回 403
      └─ 有记录
         ├─ 请求读权限 → ✅ 允许（read或write权限都可以读）
         └─ 请求写权限
            ├─ 权限是write → ✅ 允许
            └─ 权限是read → ❌ 返回 403
```

### 3. HTTP状态码说明

系统使用标准HTTP状态码表示不同的错误情况：

| 状态码 | 说明 | 何时返回 | 示例场景 |
|-------|------|---------|---------|
| **200** | 成功 | 请求成功完成 | 获取知识库列表 |
| **201** | 创建成功 | 资源创建成功 | 创建用户、创建知识库 |
| **204** | 无内容 | 删除成功 | 删除用户、删除知识库 |
| **400** | 请求错误 | 请求参数不合法 | 密码格式错误、必填字段缺失 |
| **401** | 未认证 | Token无效或过期 | Token格式错误、Token已过期 |
| **403** | 无权限 | 用户无权限执行操作 | 普通用户尝试创建用户、非所有者尝试删除知识库 |
| **404** | 不存在 | 资源不存在 | 知识库不存在、访问他人私有知识库 |

**注意**：私有知识库对无权限用户返回404而非403，避免泄露知识库是否存在。

---

## 系统架构

### 数据库表结构

系统新增以下表：

#### 1. users（用户表）

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,  -- Bcrypt加密
    role VARCHAR(20) NOT NULL,            -- admin | user
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
```

#### 2. knowledge_base_permissions（权限表）

```sql
CREATE TABLE knowledge_base_permissions (
    id INTEGER PRIMARY KEY,
    kb_id VARCHAR NOT NULL,               -- 知识库ID
    user_id INTEGER NOT NULL,             -- 被授权用户ID
    permission_type VARCHAR(20) NOT NULL, -- read | write
    granted_by INTEGER NOT NULL,          -- 授权人ID
    created_at DATETIME NOT NULL,

    FOREIGN KEY(kb_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(granted_by) REFERENCES users(id),

    UNIQUE(kb_id, user_id)  -- 每个用户对每个知识库只能有一条权限记录
);
```

#### 3. query_history（查询历史表）

```sql
CREATE TABLE query_history (
    id VARCHAR PRIMARY KEY,
    user_id INTEGER NOT NULL,
    kb_id VARCHAR NOT NULL,
    query_text TEXT NOT NULL,
    answer_text TEXT,
    citations_count INTEGER,
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    response_time_ms INTEGER,
    created_at DATETIME NOT NULL,

    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(kb_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE
);
```

#### 4. knowledge_bases（知识库表修改）

新增字段：

```sql
ALTER TABLE knowledge_bases ADD COLUMN owner_id INTEGER NOT NULL;
ALTER TABLE knowledge_bases ADD COLUMN visibility VARCHAR(20) NOT NULL DEFAULT 'private';

-- 添加外键
FOREIGN KEY(owner_id) REFERENCES users(id) ON DELETE CASCADE;
```

### 级联删除规则

系统实现了完整的级联删除，确保数据一致性：

```
删除用户（User）
  └─ 级联删除其拥有的知识库（KnowledgeBase）
      ├─ 级联删除知识库下的文档（Document）
      │   └─ 级联删除文档的chunks（Chunk）
      ├─ 级联删除知识库的同步任务（SyncTask）
      ├─ 级联删除知识库的权限记录（KBPermission）
      └─ 级联删除知识库的查询历史（QueryHistory）

  └─ 级联删除该用户被授予的权限（KBPermission where user_id）
  └─ 级联删除该用户的查询历史（QueryHistory）
```

### API分层架构

```
┌─────────────────────────────────────────────────┐
│           API Routes（路由层）                    │
│  - 接收HTTP请求                                   │
│  - 参数验证（Pydantic）                           │
│  - 认证检查（get_current_user）                   │
│  - 权限检查（check_kb_permission）                │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│         Service Layer（业务逻辑层）               │
│  - 业务逻辑处理                                   │
│  - 数据库操作                                     │
│  - 调用工具类                                     │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│      Database & Utilities（数据层和工具层）       │
│  - SQLAlchemy ORM                                │
│  - S3、OpenSearch、Bedrock客户端                 │
└──────────────────────────────────────────────────┘
```

### 核心模块说明

| 模块路径 | 作用 | 关键文件 |
|---------|------|---------|
| `app/api/v1/auth/` | 认证API | `routes.py` - 登录、获取当前用户 |
| `app/api/v1/users/` | 用户管理API | `routes.py` - 创建、列出、删除用户 |
| `app/core/security.py` | 安全工具 | JWT生成/验证、密码加密/验证 |
| `app/core/dependencies.py` | 依赖注入 | `get_current_user`、`require_admin` |
| `app/core/permissions.py` | 权限检查 | `check_kb_permission`、`check_kb_ownership` |
| `app/models/database.py` | ORM模型 | User、KBPermission、QueryHistory |
| `app/models/schemas.py` | API数据模型 | Request/Response的Pydantic模型 |

---

## 安全注意事项

### 1. 密码安全

✅ **系统已实现**：
- Bcrypt强加密算法（计算成本高，抗暴力破解）
- 自动加盐（每个密码使用不同的salt）
- 密码不可逆（无法从hash还原密码）

⚠️ **用户需注意**：
- 使用强密码（建议至少8位，包含字母数字）
- 不要共享密码
- 定期更换密码
- 首次登录后立即修改默认管理员密码

### 2. Token安全

✅ **系统已实现**：
- Token有过期时间（默认7天）
- 使用HS256算法签名（防篡改）
- Secret Key配置在环境变量中

⚠️ **部署注意事项**：
- **生产环境必须修改JWT Secret Key**（在`.env`文件中配置）
- Secret Key至少32个字符，使用随机字符串
- 不要将Secret Key提交到代码仓库
- 使用HTTPS传输Token（防止中间人攻击）

示例生成安全的Secret Key：

```python
import secrets
secret_key = secrets.token_urlsafe(32)
print(secret_key)  # 复制到 .env 文件
```

### 3. API安全

✅ **系统已实现**：
- 所有API都需要认证（除了登录接口）
- 细粒度的权限检查
- 数据隔离（用户只能访问有权限的资源）
- 防止信息泄露（私有KB返回404而非403）

### 4. 数据库安全

✅ **系统已实现**：
- SQLAlchemy参数化查询（防SQL注入）
- 外键约束（保证数据完整性）
- 级联删除（防止孤立数据）

---

## 配置说明

### 环境变量配置

在 `backend/.env` 文件中配置：

```bash
# JWT配置
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production-min-32-chars
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_DAYS=7

# 数据库配置
DATABASE_PATH=./data/ask-prd.db

# API配置
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
LOG_LEVEL=INFO
```

⚠️ **生产环境必须修改**：
- `JWT_SECRET_KEY`：使用随机生成的强密钥
- `DEBUG`：设置为false
- `LOG_LEVEL`：设置为INFO或WARNING

---

## 性能和限制

### 当前限制

1. **SQLite单实例**：当前使用SQLite数据库，仅支持单机部署
2. **无Token刷新**：Token过期后需要重新登录（未来可实现refresh token）
3. **无密码策略**：系统不强制密码复杂度（可根据需要添加）
4. **无登录限流**：暂无登录失败限制（可能受到暴力破解攻击）

### 扩展性建议

**如需支持高并发和多实例部署**：

1. **迁移到PostgreSQL/MySQL**：
   - 修改数据库连接配置
   - 调整SQLite特有的SQL语法

2. **实现Token刷新机制**：
   - 添加refresh token（有效期更长）
   - 使用短期access token（如1小时）

3. **添加Redis缓存**：
   - 缓存用户信息（减少数据库查询）
   - 实现Token黑名单（支持强制登出）

4. **添加登录限流**：
   - 使用Redis记录登录失败次数
   - 实现IP限流或账号锁定机制

---

## 下一步

继续阅读：

- **[API接口文档](./auth-api-reference.md)** - 详细的API使用说明
- **[权限管理指南](./auth-permission-guide.md)** - 权限管理最佳实践
- **[使用示例](./auth-examples.md)** - 常见场景的完整示例
- **[故障排查](./auth-troubleshooting.md)** - 常见问题和解决方法
