# ASK-PRD Frontend

> 基于PRD文档的智能检索问答系统 - 前端应用

---

## 技术栈

- **框架**: Next.js 15.1.4 (App Router)
- **UI库**: AWS Cloudscape Design System v3
- **语言**: TypeScript 5.x
- **样式**: Tailwind CSS 3.4
- **HTTP**: axios
- **Markdown**: react-markdown

---

## 快速开始

### 安装依赖
```bash
npm install
```

### 启动开发服务器
```bash
npm run dev
```

访问: http://localhost:3000

### 构建生产版本
```bash
npm run build
npm start
```

---

## 环境配置

复制 `.env.local.example` 为 `.env.local`:
```bash
cp .env.local.example .env.local
```

配置后端API地址:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

## 项目状态

**当前进度**: Phase 4 - 80% (核心功能完成)

### ✅ 已完成
- [x] Next.js 项目初始化
- [x] TypeScript 配置
- [x] Cloudscape Design System 集成
- [x] 依赖安装 (546个包)
- [x] 主布局实现 (TopNav + SideNav)
- [x] API服务封装
- [x] TypeScript类型定义
- [x] 知识库管理页面
- [x] 文档管理页面 (含同步任务监控)
- [x] 智能问答页面 (SSE流式输出)

### 🚧 待优化
- [ ] 端到端测试
- [ ] 查询历史侧边栏
- [ ] 响应式布局优化

---

## 开发指南

查看 `CONTINUE.md` 获取详细的开发继续指南。

---

## 目录结构

```
frontend/
├── app/                    # Next.js App Router
│   ├── layout.tsx         # 根布局
│   ├── page.tsx           # 首页
│   ├── knowledge-bases/   # 知识库页面
│   ├── documents/         # 文档管理页面
│   └── query/             # 问答页面
├── components/            # React组件
│   ├── knowledge-base/    # 知识库组件
│   ├── document/          # 文档组件
│   └── query/             # 问答组件
├── services/              # API服务
│   └── api.ts            # API封装
├── types/                 # TypeScript类型
│   └── index.ts          # 类型定义
├── lib/                   # 工具函数
└── public/                # 静态资源
```

---

## API接口

后端API文档: `/home/ubuntu/ask-prd/docs/api-*.md`

### 主要接口
- 知识库: `/api/v1/knowledge-bases`
- 文档: `/api/v1/documents`
- 同步任务: `/api/v1/sync-tasks`
- 问答: `/api/v1/query/stream` (SSE)

---

## 相关文档

- [继续开发指南](./CONTINUE.md)
- [后端文档](../backend/README.md)
- [项目需求](../docs/requirements.md)
- [API文档](../docs/api-overview.md)

---

## License

MIT
