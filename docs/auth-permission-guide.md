# 认证和授权系统 - 权限管理指南

## 目录

- [权限管理概述](#权限管理概述)
- [知识库可见性管理](#知识库可见性管理)
- [用户权限管理](#用户权限管理)
- [权限管理最佳实践](#权限管理最佳实践)
- [常见权限场景](#常见权限场景)

---

## 权限管理概述

### 权限模型

ASK-PRD使用**两层权限模型**：

```
第一层：知识库可见性（Visibility）
  ├─ private（私有）：仅所有者可见
  ├─ public（公开）：所有人可见
  └─ shared（共享）：指定人可见

第二层：用户权限（Permission）
  ├─ read（只读）：查看和问答
  └─ write（管理）：修改和管理
```

### 权限继承规则

| 角色/身份 | 自动拥有的权限 |
|----------|--------------|
| **管理员** | 所有知识库的所有权限 |
| **知识库所有者** | 该知识库的所有权限 |
| **被授权用户** | 根据权限表中的记录 |
| **普通用户** | 仅公开知识库的读权限 |

---

## 知识库可见性管理

### 三种可见性类型对比

#### 1. Private（私有）- 默认

**适用场景**：
- 个人知识库
- 敏感信息
- 开发测试阶段

**访问规则**：
- ✅ 所有者：全部权限
- ✅ 管理员：全部权限
- ❌ 其他用户：无法看到（返回404）

**特点**：
- 其他用户无法通过列表API看到该知识库
- 即使知道KB ID也无法访问（返回404假装不存在）
- 无法通过权限表授权（shared类型才支持）

**设置方法**：

```bash
# 创建时默认就是private
curl -X POST http://localhost:8000/api/v1/knowledge-bases \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "我的私有知识库",
    "description": "这是私有的"
  }'

# 或者修改为private
curl -X PUT http://localhost:8000/api/v1/knowledge-bases/kb-xxx/visibility \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"visibility": "private"}'
```

---

#### 2. Public（公开）

**适用场景**：
- 公司公共文档
- 团队共享知识库
- 公开资料库

**访问规则**：
- ✅ 所有登录用户：默认只读
- ✅ 被明确授予write权限的用户：可以管理
- ✅ 所有者和管理员：全部权限

**特点**：
- 所有用户都能在列表中看到
- 所有用户默认有read权限（无需添加权限记录）
- 如需write权限，必须通过权限表明确授予

**设置方法**：

```bash
# 修改为public
curl -X PUT http://localhost:8000/api/v1/knowledge-bases/kb-xxx/visibility \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"visibility": "public"}'
```

**授予写权限**：

```bash
# 授予某用户写权限（否则只能读）
curl -X POST http://localhost:8000/api/v1/knowledge-bases/kb-xxx/permissions \
  -H "Authorization: Bearer OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "permission_type": "write"
  }'
```

---

#### 3. Shared（共享）

**适用场景**：
- 团队协作
- 特定人员可见
- 细粒度权限控制

**访问规则**：
- ✅ 权限表中的用户：根据权限类型
- ✅ 所有者和管理员：全部权限
- ❌ 其他用户：无法看到和访问

**特点**：
- 必须通过权限表明确授权
- 支持read和write两种权限
- 未授权用户无法访问（返回403）

**设置方法**：

```bash
# 1. 修改为shared
curl -X PUT http://localhost:8000/api/v1/knowledge-bases/kb-xxx/visibility \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"visibility": "shared"}'

# 2. 授予用户权限
curl -X POST http://localhost:8000/api/v1/knowledge-bases/kb-xxx/permissions \
  -H "Authorization: Bearer OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "permission_type": "read"
  }'

curl -X POST http://localhost:8000/api/v1/knowledge-bases/kb-xxx/permissions \
  -H "Authorization: Bearer OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "bob",
    "permission_type": "write"
  }'
```

---

### 可见性选择指南

| 需求 | 推荐可见性 | 原因 |
|-----|----------|------|
| 个人笔记 | Private | 完全隔离 |
| 公司手册 | Public | 所有人可读 |
| 项目文档（小团队） | Shared | 细粒度控制 |
| 开发测试 | Private | 避免干扰 |
| 公开资料库 | Public | 方便访问 |
| 敏感数据 | Private | 最安全 |

---

## 用户权限管理

### 权限操作流程

#### 1. 查看当前权限列表

```bash
# 查看知识库的所有权限
curl -X GET http://localhost:8000/api/v1/knowledge-bases/kb-xxx/permissions \
  -H "Authorization: Bearer OWNER_TOKEN"
```

响应：

```json
{
  "permissions": [
    {
      "id": 1,
      "kb_id": "kb-xxx",
      "user_id": 3,
      "username": "alice",
      "permission_type": "read",
      "granted_by": 2,
      "created_at": "2025-11-11T10:00:00"
    }
  ]
}
```

---

#### 2. 添加新权限

```bash
# 授予alice读权限
curl -X POST http://localhost:8000/api/v1/knowledge-bases/kb-xxx/permissions \
  -H "Authorization: Bearer OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "permission_type": "read"
  }'
```

**注意事项**：

- ✅ 使用username（不是user_id）
- ✅ 知识库必须是shared或public类型（public类型仅授予write时需要）
- ✅ 不能给所有者添加权限（所有者自动拥有全部权限）
- ✅ 如果该用户已有权限，会更新权限类型

---

#### 3. 升级权限

```bash
# 将alice的权限从read升级为write
curl -X POST http://localhost:8000/api/v1/knowledge-bases/kb-xxx/permissions \
  -H "Authorization: Bearer OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "permission_type": "write"
  }'
```

**说明**：使用相同的POST接口，系统会自动检测权限是否已存在并更新。

---

#### 4. 撤销权限

```bash
# 撤销alice的权限
curl -X DELETE http://localhost:8000/api/v1/knowledge-bases/kb-xxx/permissions/3 \
  -H "Authorization: Bearer OWNER_TOKEN"
```

**注意**：需要使用user_id（不是username）。

**获取user_id的方法**：

1. 通过权限列表API获取
2. 通过用户列表API获取（仅管理员）

---

### 权限变更的影响

#### 从write降级为read

```
用户之前可以：
  ✅ 查看文档
  ✅ 上传文档
  ✅ 删除文档
  ✅ 问答查询

降级后只能：
  ✅ 查看文档
  ✅ 问答查询
  ❌ 上传文档（403）
  ❌ 删除文档（403）
```

#### 撤销权限（shared类型）

```
撤销前：
  ✅ 可以看到知识库
  ✅ 可以访问文档

撤销后：
  ❌ 知识库从列表中消失
  ❌ 访问返回403
  ❌ 无法查询
```

#### 从shared改为private

```
影响：
  - 所有权限记录失效
  - 被授权用户无法访问（返回404）
  - 权限表记录保留（但不生效）

如果再改回shared：
  - 权限记录自动恢复生效
```

---

## 权限管理最佳实践

### 1. 可见性设置原则

#### ✅ 推荐做法

- **默认私有**：创建知识库时保持private，测试完成后再开放
- **明确需求**：根据实际使用场景选择可见性，不要盲目设为public
- **最小权限**：优先使用read权限，确实需要时再授予write
- **定期审查**：定期检查权限列表，删除不再需要的权限

#### ❌ 不推荐做法

- **过度开放**：不要随意将敏感知识库设为public
- **权限混乱**：避免同时使用public + 权限表（public已经所有人可读，无需再加read权限）
- **忽略撤销**：员工离职或项目结束后，记得撤销权限

---

### 2. 团队协作场景

#### 场景1：项目团队（5人）

**需求**：项目成员都需要访问，其中2人需要管理文档

**方案**：

```bash
# 1. 创建知识库（所有者：项目经理）
# 2. 设置为shared
# 3. 授予成员权限
#    - 3人read（开发、测试）
#    - 2人write（项目经理、文档管理员）

curl -X PUT .../visibility -d '{"visibility": "shared"}'

curl -X POST .../permissions -d '{"username": "dev1", "permission_type": "read"}'
curl -X POST .../permissions -d '{"username": "dev2", "permission_type": "read"}'
curl -X POST .../permissions -d '{"username": "qa1", "permission_type": "read"}'
curl -X POST .../permissions -d '{"username": "pm1", "permission_type": "write"}'
curl -X POST .../permissions -d '{"username": "doc_admin", "permission_type": "write"}'
```

---

#### 场景2：全公司文档库

**需求**：所有员工都能查看，HR部门可以编辑

**方案**：

```bash
# 1. 创建知识库
# 2. 设置为public（所有人自动有read权限）
# 3. 仅授予HR write权限

curl -X PUT .../visibility -d '{"visibility": "public"}'

curl -X POST .../permissions -d '{"username": "hr_alice", "permission_type": "write"}'
curl -X POST .../permissions -d '{"username": "hr_bob", "permission_type": "write"}'
```

---

#### 场景3：临时协作

**需求**：短期项目，需要外部顾问访问

**方案**：

```bash
# 1. 创建或使用现有知识库（shared）
# 2. 授予顾问read权限
# 3. 项目结束后撤销权限

# 授予权限
curl -X POST .../permissions -d '{"username": "consultant", "permission_type": "read"}'

# 项目结束后撤销
curl -X DELETE .../permissions/consultant_user_id
```

---

### 3. 权限审计

#### 定期检查权限

```bash
# 1. 列出所有知识库
curl -X GET http://localhost:8000/api/v1/knowledge-bases \
  -H "Authorization: Bearer ADMIN_TOKEN"

# 2. 逐个检查权限列表
curl -X GET http://localhost:8000/api/v1/knowledge-bases/kb-xxx/permissions \
  -H "Authorization: Bearer ADMIN_TOKEN"

# 3. 分析结果
#    - 是否有不再需要的权限？
#    - 是否有权限过高（应该read却是write）？
#    - 是否有离职员工的权限未撤销？
```

#### 权限审计清单

- [ ] 检查所有public知识库（是否应该是shared？）
- [ ] 检查write权限用户（是否确实需要写权限？）
- [ ] 检查长期未使用的知识库（是否可以删除或归档？）
- [ ] 检查孤立权限（用户已删除但权限记录还在）

---

### 4. 安全建议

#### 密码管理

- ✅ 使用强密码（至少8位，字母数字混合）
- ✅ 定期更换密码
- ✅ 不要共享账号
- ✅ 管理员账号使用更强的密码

#### Token管理

- ✅ 不要在URL中传递Token
- ✅ 不要在日志中记录Token
- ✅ 浏览器中使用localStorage存储
- ✅ Token过期后立即清除

#### 权限管理

- ✅ 遵循最小权限原则
- ✅ 定期审查权限列表
- ✅ 及时撤销不再需要的权限
- ✅ 敏感知识库使用private

---

## 常见权限场景

### 场景1：新员工入职

**操作流程**：

```bash
# 1. 管理员创建用户
curl -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "new_employee",
    "password": "temp_password_123"
  }'

# 2. 通知用户首次登录修改密码
#    （当前系统未实现强制修改，需要用户自觉）

# 3. 所有者授予相关知识库权限
curl -X POST http://localhost:8000/api/v1/knowledge-bases/kb-xxx/permissions \
  -H "Authorization: Bearer OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "new_employee",
    "permission_type": "read"
  }'
```

---

### 场景2：员工离职

**操作流程**：

```bash
# 方案A：删除用户（彻底清除）
curl -X DELETE http://localhost:8000/api/v1/users/{user_id} \
  -H "Authorization: Bearer ADMIN_TOKEN"

# 级联效果：
# - 用户拥有的所有知识库被删除
# - 用户被授予的所有权限被删除
# - 用户的查询历史被删除

# 方案B：仅撤销权限（保留用户账号）
# 逐个撤销权限
curl -X DELETE http://localhost:8000/api/v1/knowledge-bases/kb-xxx/permissions/{user_id} \
  -H "Authorization: Bearer OWNER_TOKEN"
```

**建议**：

- 如果该员工拥有重要知识库，先转移所有权（当前系统未实现转移功能，可以重新创建）
- 然后删除用户或禁用账号

---

### 场景3：项目交接

**需求**：项目从TeamA转移到TeamB

**操作流程**：

```bash
# 1. TeamB负责人创建新知识库
# 2. 上传或同步文档
# 3. 授予TeamB成员权限
# 4. TeamA负责人删除旧知识库或保留为只读

# 或者：修改现有知识库的权限
# 1. 撤销TeamA成员的write权限
# 2. 授予TeamB成员write权限
```

---

### 场景4：临时提权

**需求**：普通用户临时需要write权限（如修复文档错误）

**操作流程**：

```bash
# 1. 所有者授予临时write权限
curl -X POST http://localhost:8000/api/v1/knowledge-bases/kb-xxx/permissions \
  -H "Authorization: Bearer OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "temp_user",
    "permission_type": "write"
  }'

# 2. 用户完成操作

# 3. 降级回read权限
curl -X POST http://localhost:8000/api/v1/knowledge-bases/kb-xxx/permissions \
  -H "Authorization: Bearer OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "temp_user",
    "permission_type": "read"
  }'

# 或直接撤销权限
curl -X DELETE http://localhost:8000/api/v1/knowledge-bases/kb-xxx/permissions/{user_id} \
  -H "Authorization: Bearer OWNER_TOKEN"
```

---

### 场景5：跨部门协作

**需求**：产品部门和技术部门共同使用一个知识库

**方案1**：Shared + 细粒度权限

```bash
# 产品部门成员：write权限（编辑PRD）
curl -X POST .../permissions -d '{"username": "pm1", "permission_type": "write"}'
curl -X POST .../permissions -d '{"username": "pm2", "permission_type": "write"}'

# 技术部门成员：read权限（查看PRD）
curl -X POST .../permissions -d '{"username": "dev1", "permission_type": "read"}'
curl -X POST .../permissions -d '{"username": "dev2", "permission_type": "read"}'
curl -X POST .../permissions -d '{"username": "dev3", "permission_type": "read"}'
```

**方案2**：Public + 选择性write

```bash
# 设为public（技术部门自动可读）
curl -X PUT .../visibility -d '{"visibility": "public"}'

# 仅授予产品部门write权限
curl -X POST .../permissions -d '{"username": "pm1", "permission_type": "write"}'
curl -X POST .../permissions -d '{"username": "pm2", "permission_type": "write"}'
```

**选择建议**：如果技术部门人数多，用方案2更简单。

---

## 下一步

继续阅读：

- **[使用示例](./auth-examples.md)** - 完整的代码示例
- **[故障排查](./auth-troubleshooting.md)** - 常见问题和解决方法
- **[系统概述](./auth-system-overview.md)** - 回到系统概述
