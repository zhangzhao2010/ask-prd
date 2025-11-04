# AKS-PRD 开发任务清单

> 版本：v1.0
> 更新时间：2025-01-20

---

## 项目里程碑

```
Phase 1: 项目初始化和基础框架 (2周) ✅ 设计完成
    ↓
Phase 2: 知识库构建系统 (3周)
    ↓
Phase 3: 检索问答系统 (3周)
    ↓
Phase 4: 前端开发 (2周)
    ↓
Phase 5: 测试和优化 (1周)
```

**预计总工期**: 11周

---

## 各阶段概览

### Phase 1: 项目初始化和基础框架 (2周)

**目标**: 搭建项目骨架，完成基础设施配置

**关键产出**:
- ✅ 项目文档完成
- [ ] 项目目录结构创建
- [ ] 数据库Schema实现
- [ ] AWS服务配置
- [ ] 基础API框架

**详细任务**: 见 [todo-phase1-setup.md](./todo-phase1-setup.md)

---

### Phase 2: 知识库构建系统 (3周)

**目标**: 实现PDF上传、转换、向量化的完整流程

**关键产出**:
- [ ] 知识库管理API
- [ ] 文档上传功能
- [ ] PDF转Markdown（Marker集成）
- [ ] 图片理解（Bedrock Claude）
- [ ] 文本分块和向量化
- [ ] 同步任务系统

**详细任务**: 见 [todo-phase2-knowledge-base.md](./todo-phase2-knowledge-base.md)

---

### Phase 3: 检索问答系统 (3周)

**目标**: 实现基于Multi-Agent的智能问答

**关键产出**:
- [ ] Query Rewrite
- [ ] Hybrid Search（向量+BM25）
- [ ] Sub-Agent系统
- [ ] Main Agent综合
- [ ] 流式输出
- [ ] 引用提取

**详细任务**: 见 [todo-phase3-query.md](./todo-phase3-query.md)

---

### Phase 4: 前端开发 (2周)

**目标**: 实现用户界面和交互

**关键产出**:
- [ ] 知识库管理页面
- [ ] 文档管理页面
- [ ] 检索问答页面
- [ ] 历史记录展示
- [ ] 引用展示（文本+图片）

**详细任务**: 见 [todo-phase4-frontend.md](./todo-phase4-frontend.md)

---

### Phase 5: 测试和优化 (1周)

**目标**: 完善功能、修复bug、优化性能

**关键产出**:
- [ ] 单元测试
- [ ] 集成测试
- [ ] 性能测试
- [ ] 错误处理完善
- [ ] 文档完善

**详细任务**: 见 [todo-phase5-testing.md](./todo-phase5-testing.md)

---

## 当前进度

### 已完成 ✅
- [x] 需求文档
- [x] 架构设计文档
- [x] 数据库设计文档
- [x] API接口设计文档
- [x] 错误处理文档
- [x] README文档

### 进行中 🚧
- [ ] Phase 1: 项目初始化和基础框架

### 待开始 📋
- [ ] Phase 2: 知识库构建系统
- [ ] Phase 3: 检索问答系统
- [ ] Phase 4: 前端开发
- [ ] Phase 5: 测试和优化

---

## 关键依赖

### 外部依赖
- [ ] AWS账号开通
- [ ] S3 Bucket创建
- [ ] OpenSearch Serverless配置
- [ ] Bedrock模型访问权限
- [ ] EC2实例申请（带GPU）

### 技术依赖
- [ ] Python 3.11+ 环境
- [ ] Node.js 18+ 环境
- [ ] CUDA驱动安装（GPU）
- [ ] Marker安装配置

---

## 风险和挑战

### 高风险项
1. **Marker GPU依赖**: 需要GPU支持，可能存在环境配置问题
   - 缓解措施: 提前验证GPU环境，准备降级方案

2. **Bedrock限流**: 高并发时可能触发限流
   - 缓解措施: 实现重试机制、限流保护、申请提升配额

3. **Multi-Agent成本**: 多次调用大模型成本较高
   - 缓解措施: Demo阶段暂不考虑，后续可优化

### 中风险项
1. **OpenSearch性能**: 大规模向量检索性能
   - 缓解措施: 优化Index配置、向量维度

2. **文件缓存管理**: 磁盘空间管理
   - 缓解措施: 实现LRU清理、监控磁盘使用

---

## 开发规范

### 代码规范
- Python: 遵循PEP 8，使用black格式化
- TypeScript: 遵循Airbnb规范，使用prettier格式化
- 提交信息: 遵循Conventional Commits

### 分支策略
- `main`: 主分支，保护分支
- `develop`: 开发分支
- `feature/*`: 功能分支
- `fix/*`: 修复分支

### 代码审查
- 所有PR需要至少1人审查
- 必须通过CI测试
- 代码覆盖率 > 70%

---

## 每周检查清单

### 周一
- [ ] 回顾上周进度
- [ ] 确定本周目标
- [ ] 更新TODO状态

### 周五
- [ ] 总结本周完成情况
- [ ] 识别阻塞问题
- [ ] 规划下周任务

---

## 快速链接

- [需求文档](./requirements.md)
- [架构设计](./architecture.md)
- [数据库设计](./database.md)
- [API文档](./api-overview.md)
- [错误处理](./error-handling.md)

---

## 更新日志

### 2025-01-20
- 初始化TODO文档
- 完成Phase 1-5规划
- 定义各阶段目标和产出
