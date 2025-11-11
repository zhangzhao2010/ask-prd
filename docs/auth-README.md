# ASK-PRD 认证和授权系统文档

欢迎使用ASK-PRD认证和授权系统！本文档将帮助您快速理解和使用系统的用户认证、权限管理功能。

---

## 📚 文档导航

### 1. [系统概述](./auth-system-overview.md) ⭐ **从这里开始**

**适合人群**：所有用户

**内容**：
- 系统简介和核心特性
- JWT认证机制
- 权限模型（可见性和权限类型）
- 数据库架构
- 安全注意事项
- 配置说明

**阅读时间**：15-20分钟

---

### 2. [API接口文档](./auth-api-reference.md)

**适合人群**：开发人员、API集成

**内容**：
- 认证API（登录、获取用户信息）
- 用户管理API（创建、删除用户）
- 知识库权限管理API（可见性、权限授予/撤销）
- 其他已修改的API说明
- API使用最佳实践

**阅读时间**：30分钟

---

### 3. [权限管理指南](./auth-permission-guide.md)

**适合人群**：系统管理员、知识库所有者

**内容**：
- 三种可见性类型详解（private/public/shared）
- 用户权限管理流程
- 权限管理最佳实践
- 团队协作场景方案
- 常见权限场景处理

**阅读时间**：25分钟

---

### 4. [使用示例](./auth-examples.md)

**适合人群**：开发人员

**内容**：
- 完整的认证流程示例
- 知识库管理示例
- 权限管理操作示例
- React前端集成完整代码
- 权限管理UI组件

**阅读时间**：20分钟

---

### 5. [故障排查](./auth-troubleshooting.md)

**适合人群**：遇到问题的用户

**内容**：
- 认证问题解决
- 权限问题解决
- Token问题处理
- 数据库问题诊断
- 系统配置问题
- 诊断工具和命令
- 常见错误速查表

**阅读时间**：按需查阅

---

## 🚀 快速开始

### 首次使用（5分钟）

1. **初始化数据库**
   ```bash
   cd backend
   python scripts/migrate_add_users_and_permissions.py --yes
   ```

2. **启动服务**
   ```bash
   python -m app.main
   ```

3. **测试登录**
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "admin123"}'
   ```

4. **保存Token并使用**
   ```bash
   TOKEN="your_access_token_here"
   curl -X GET http://localhost:8000/api/v1/knowledge-bases \
     -H "Authorization: Bearer $TOKEN"
   ```

---

## 📖 学习路径推荐

### 路径1：快速上手（30分钟）

适合只想快速使用系统的用户：

1. 阅读 [系统概述 - 快速开始](./auth-system-overview.md#快速开始)
2. 阅读 [系统概述 - 核心概念](./auth-system-overview.md#核心概念)
3. 浏览 [使用示例](./auth-examples.md) 中的基础认证流程
4. 遇到问题查看 [故障排查](./auth-troubleshooting.md)

### 路径2：深入理解（1小时）

适合需要深入了解系统的管理员：

1. 完整阅读 [系统概述](./auth-system-overview.md)
2. 重点阅读 [权限管理指南](./auth-permission-guide.md)
3. 了解 [API接口文档](./auth-api-reference.md) 中的权限API
4. 参考 [使用示例](./auth-examples.md) 中的权限管理示例

### 路径3：开发集成（1.5小时）

适合需要集成到前端的开发人员：

1. 阅读 [系统概述](./auth-system-overview.md) 了解架构
2. 详细阅读 [API接口文档](./auth-api-reference.md)
3. 重点学习 [使用示例 - 前端集成](./auth-examples.md#前端集成示例)
4. 开发过程中参考 [故障排查](./auth-troubleshooting.md)

---

## 🎯 核心功能速览

### 用户认证

- ✅ JWT Token认证（7天有效期）
- ✅ 密码Bcrypt强加密
- ✅ 两种用户角色：管理员、普通用户
- ✅ 用户状态管理

**默认管理员账户**：
- 用户名：`admin`
- 密码：`admin123`
- ⚠️ 首次登录后请立即修改密码

### 知识库可见性

| 类型 | 说明 | 适用场景 |
|-----|------|---------|
| **private** | 仅所有者可见 | 个人知识库、敏感信息 |
| **public** | 所有人可见（默认只读） | 公司手册、公开资料 |
| **shared** | 指定人可见 | 团队协作、项目文档 |

### 用户权限

| 权限 | 可执行操作 |
|-----|----------|
| **read** | 查看文档、问答查询 |
| **write** | read权限 + 上传/删除文档、修改知识库 |

**注意**：删除知识库仅限所有者和管理员

---

## ⚠️ 重要提醒

### 安全相关

1. **首次登录后立即修改默认管理员密码**
2. **生产环境必须修改JWT Secret Key**
3. **使用HTTPS传输（生产环境）**
4. **不要将Token和Secret Key提交到代码仓库**

### 权限管理

1. **遵循最小权限原则**（优先使用read权限）
2. **定期审查权限列表**
3. **员工离职及时撤销权限**
4. **敏感知识库使用private可见性**

---

## 🔧 测试验证

运行完整的系统测试（27个测试用例）：

```bash
cd backend
python scripts/test_auth_and_permissions.py
```

测试覆盖：
- ✅ 认证功能（登录、Token）
- ✅ 用户管理（创建、删除）
- ✅ 知识库可见性
- ✅ 权限管理（授予、撤销、升级）
- ✅ 数据隔离
- ✅ 级联删除
- ✅ 安全验证

---

## 📊 系统架构图

```
┌─────────────────────────────────────────────────────────┐
│                    前端应用                               │
│  - 登录界面                                               │
│  - 知识库管理界面                                          │
│  - 权限管理界面                                            │
└─────────────────┬───────────────────────────────────────┘
                  │ HTTP + JWT Token
┌─────────────────▼───────────────────────────────────────┐
│                  API Routes                              │
│  - 认证API (/auth/login, /auth/me)                      │
│  - 用户管理API (/users)                                  │
│  - 知识库API (/knowledge-bases)                          │
│  - 权限管理API (/knowledge-bases/{id}/permissions)      │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│              权限检查层                                    │
│  - get_current_user（认证）                              │
│  - check_kb_permission（权限验证）                        │
│  - check_kb_ownership（所有权验证）                       │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│             业务逻辑层                                     │
│  - KnowledgeBaseService                                  │
│  - DocumentService                                       │
│  - QueryService                                          │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│              数据层                                        │
│  - SQLite数据库（users, knowledge_bases, permissions）   │
│  - S3（文件存储）                                          │
│  - OpenSearch（向量检索）                                  │
└──────────────────────────────────────────────────────────┘
```

---

## 🆘 需要帮助？

### 遇到问题

1. 查看 [故障排查](./auth-troubleshooting.md)
2. 查看系统日志：`tail -f logs/app.log`
3. 运行测试脚本诊断：`python scripts/test_auth_and_permissions.py`
4. 检查数据库状态：参考故障排查中的诊断命令

### 常见问题

- **登录失败？** → [故障排查 - 认证问题](./auth-troubleshooting.md#认证问题)
- **无权限访问？** → [故障排查 - 权限问题](./auth-troubleshooting.md#权限问题)
- **Token过期？** → [故障排查 - Token问题](./auth-troubleshooting.md#token问题)

### 学习资源

- [系统概述](./auth-system-overview.md) - 了解系统设计
- [使用示例](./auth-examples.md) - 参考代码示例
- [权限管理指南](./auth-permission-guide.md) - 学习最佳实践

---

## 📝 版本信息

- **当前版本**：1.0.0
- **最后更新**：2025-11-11
- **Python版本要求**：3.12+
- **主要依赖**：FastAPI, SQLAlchemy, python-jose, passlib

---

## 🎉 开始使用

准备好了吗？

1. 📖 从 [系统概述](./auth-system-overview.md) 开始阅读
2. 💻 参考 [使用示例](./auth-examples.md) 动手实践
3. ⚙️ 遇到问题查看 [故障排查](./auth-troubleshooting.md)

祝您使用愉快！🚀
