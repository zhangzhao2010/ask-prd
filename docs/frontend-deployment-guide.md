# 前端部署和测试指南

## 🎉 已完成功能

### 核心认证功能

✅ **认证服务** (`frontend/services/auth.ts`)
- JWT Token管理
- 用户信息本地存储
- 登录/登出功能
- 权限检查辅助函数

✅ **API客户端** (`frontend/services/api.ts`)
- 统一的HTTP请求封装
- 自动添加认证Token
- 401自动跳转登录
- 完整的用户管理和权限管理API

✅ **登录页面** (`frontend/app/login/page.tsx`)
- 用户名密码登录
- 错误提示
- 默认管理员提示
- 加载状态

✅ **路由守卫** (`frontend/components/ProtectedRoute.tsx`)
- 认证状态检查
- 管理员权限检查
- 自动重定向
- 403禁止访问页面

✅ **导航栏更新** (`frontend/app/layout.tsx`)
- 显示当前用户名和角色
- 用户菜单（登出、用户管理）
- 管理员侧边栏菜单
- 动态显示/隐藏

✅ **用户管理页面** (`frontend/app/admin/users/page.tsx`)
- 用户列表展示
- 创建新用户
- 删除用户（级联删除警告）
- 仅管理员可访问

✅ **权限管理组件** (`frontend/components/knowledge-base/PermissionManager.tsx`)
- 修改知识库可见性（private/public/shared）
- 授予用户权限（read/write）
- 撤销用户权限
- 权限列表展示

✅ **知识库列表更新** (`frontend/app/knowledge-bases/page.tsx`)
- 显示可见性状态
- 显示所有者标识
- 权限管理入口按钮
- 只有所有者/管理员可删除

---

## 🚀 快速启动

### 1. 启动后端服务

```bash
cd /home/ubuntu/ask-prd/backend

# 确保数据库已初始化
python scripts/migrate_add_users_and_permissions.py --yes

# 启动后端服务
python -m app.main
```

后端运行在：`http://localhost:8000`

### 2. 启动前端服务

```bash
cd /home/ubuntu/ask-prd/frontend

# 安装依赖（如果还没安装）
npm install

# 启动开发服务器
npm run dev
```

前端运行在：`http://localhost:3000`

---

## 🧪 功能测试清单

### 测试1：管理员登录

1. 打开浏览器访问：`http://localhost:3000`
2. 应该自动跳转到 `/login`
3. 输入默认管理员账号：
   - 用户名：`admin`
   - 密码：`admin123`
4. 点击"登录"按钮
5. ✅ **期望**：跳转到知识库列表页面，右上角显示 "admin（管理员）"

### 测试2：导航栏功能

1. 登录后，检查顶部导航栏
2. ✅ **期望**：
   - 显示用户名 "admin"
   - 点击用户名下拉菜单，显示"用户管理"和"登出"选项
3. 检查侧边导航栏
4. ✅ **期望**：
   - 显示"系统管理 > 用户管理"菜单（管理员专属）

### 测试3：用户管理功能

1. 点击侧边栏"系统管理 > 用户管理"
2. 点击"创建用户"按钮
3. 输入：
   - 用户名：`testuser`
   - 密码：`password123`
4. 点击"创建"
5. ✅ **期望**：用户列表中出现新用户，角色为"普通用户"

### 测试4：普通用户登录

1. 点击右上角用户菜单 > "登出"
2. 使用新创建的账号登录：
   - 用户名：`testuser`
   - 密码：`password123`
3. ✅ **期望**：
   - 登录成功
   - 右上角显示 "testuser（用户）"
   - 侧边栏**没有**"系统管理"菜单

### 测试5：创建知识库

1. 使用testuser账号，点击"创建知识库"
2. 输入知识库名称和描述
3. 创建成功后
4. ✅ **期望**：
   - 列表中出现新知识库
   - 可见性显示"私有"
   - 显示"所有者"标识

### 测试6：修改知识库可见性

1. 点击知识库操作列的"权限"按钮
2. 在"可见性设置"中，修改为"公开"
3. 点击确认
4. ✅ **期望**：
   - 成功提示
   - 知识库列表中可见性变为"公开"

### 测试7：授予权限

1. 创建另一个测试用户（使用admin账号）：`testuser2`
2. 使用testuser账号
3. 将知识库可见性改为"共享"
4. 点击"添加权限"
5. 输入：
   - 用户名：`testuser2`
   - 权限类型：只读
6. 点击"添加"
7. ✅ **期望**：
   - 权限列表中出现testuser2
   - 权限类型为"只读"

### 测试8：数据隔离验证

1. 登出testuser，登录testuser2
2. 查看知识库列表
3. ✅ **期望**：
   - 看到testuser共享的知识库
   - 看不到其他私有知识库

### 测试9：权限升级

1. 使用testuser账号
2. 在权限管理中，将testuser2的权限升级为"管理"
3. ✅ **期望**：成功提示，权限列表更新

### 测试10：撤销权限

1. 继续使用testuser账号
2. 点击testuser2权限的"撤销"按钮
3. 确认撤销
4. ✅ **期望**：
   - 成功提示
   - 权限列表中不再显示testuser2

### 测试11：管理员全局权限

1. 登出，使用admin账号登录
2. 查看知识库列表
3. ✅ **期望**：
   - 看到所有知识库（包括其他用户的私有知识库）
   - 每个知识库都显示"管理员"标识

### 测试12：删除权限验证

1. 使用testuser2账号登录
2. 尝试删除testuser创建的知识库
3. ✅ **期望**：
   - 删除按钮不可点击（如果有选择）
   - 或删除失败，提示无权限

### 测试13：用户删除级联

1. 使用admin账号
2. 进入"用户管理"
3. 删除testuser
4. 查看警告提示
5. ✅ **期望**：
   - 显示级联删除警告（知识库、文档等）
   - 删除成功后，testuser的知识库也被删除

---

## 📋 API测试（可选）

如果想单独测试后端API：

```bash
# 1. 登录获取Token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# 保存返回的access_token
TOKEN="your_access_token_here"

# 2. 获取知识库列表
curl -X GET http://localhost:8000/api/v1/knowledge-bases \
  -H "Authorization: Bearer $TOKEN"

# 3. 创建用户（仅管理员）
curl -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username": "newuser", "password": "password123"}'
```

---

## ⚠️ 已知问题和限制

### 当前系统限制

1. **密码策略**：无密码复杂度要求
2. **Token刷新**：Token过期需要重新登录（未实现refresh token）
3. **登录限流**：暂无登录失败限制（可能受暴力破解）
4. **密码重置**：未实现密码找回功能

### 开发环境注意事项

1. **JWT Secret Key**：使用默认值，生产环境必须修改
2. **CORS配置**：开发环境允许所有域，生产环境需限制
3. **SQLite限制**：单机单进程，不支持高并发

---

## 🔧 故障排查

### 前端无法启动

```bash
# 检查端口是否被占用
lsof -i :3000

# 清理缓存
rm -rf .next
npm run dev
```

### 后端无法启动

```bash
# 检查端口
lsof -i :8000

# 检查数据库
ls -la /home/ubuntu/ask-prd/backend/data/ask-prd.db

# 重新初始化
python scripts/migrate_add_users_and_permissions.py --yes
```

### 登录失败

1. 检查后端是否运行：`curl http://localhost:8000/health`
2. 检查用户是否存在：使用admin/admin123
3. 查看后端日志：`tail -f logs/app.log`

### Token过期

- Token默认有效期7天
- 过期后自动跳转登录页
- 重新登录即可

---

## 📚 相关文档

- **[认证系统概述](./auth-system-overview.md)** - 系统设计和架构
- **[API接口文档](./auth-api-reference.md)** - 完整的API说明
- **[权限管理指南](./auth-permission-guide.md)** - 权限管理最佳实践
- **[故障排查](./auth-troubleshooting.md)** - 常见问题解决

---

## ✅ 测试完成确认

完成上述测试后，您应该已经验证了：

- [x] 用户认证（登录/登出）
- [x] 路由守卫（未登录跳转）
- [x] 管理员权限（用户管理）
- [x] 知识库可见性管理
- [x] 用户权限授予/撤销
- [x] 数据隔离
- [x] 级联删除

如果所有测试通过，恭喜您！系统已经可以正常使用了！🎉

---

## 🚀 下一步

系统已经具备基本的认证和权限功能，可以考虑：

1. **添加密码修改功能**
2. **实现Token刷新机制**
3. **添加登录限流**
4. **迁移到PostgreSQL（生产环境）**
5. **添加审计日志**
6. **性能优化和压力测试**

祝您使用愉快！
