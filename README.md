# ASK-PRD - 基于PRD的智能检索问答系统

> 为产品经理提供基于PRD文档的智能检索和问答能力

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Node](https://img.shields.io/badge/node-20+-green.svg)](https://nodejs.org/)

---

## 项目简介

ASK-PRD 是一个为产品经理打造的智能文档检索和问答系统。通过AI技术，帮助团队快速检索和理解大量的PRD（产品需求文档）历史信息。

### 核心功能

- **智能检索**：基于向量检索和关键词检索的混合检索，准确找到相关文档
- **图文理解**：支持流程图、原型图、脑图等图片的理解和描述
- **Multi-Agent问答**：使用多Agent协作，深度阅读文档并生成准确答案
- **溯源引用**：提供文本和图片引用，答案可追溯到原文档
- **流式输出**：实时展示答案生成过程，提升用户体验

### 典型使用场景

**场景1**: 产品经理问："登录注册模块的演进历史是怎样的？"
- 系统自动检索所有相关版本的PRD
- 理解文档中的文字和流程图
- 按时间顺序总结演进历程
- 提供引用来源（文本+图片）

---

## 技术架构

### 技术栈

**前端**
- Next.js 16
- AWS Cloudscape Design System
- TypeScript

**后端**
- Python 3.12
- FastAPI
- SQLAlchemy
- Strands Agents SDK（Multi-Agent框架）

**基础设施**
- AWS EC2（带GPU）
- Amazon S3（对象存储）
- Amazon OpenSearch Serverless（向量数据库）
- AWS Bedrock（AI服务，通过Strands集成）
- SQLite（元数据库）

**核心依赖**
- strands-agents（Agent框架）
- marker（PDF转Markdown）
- langchain（文本处理）

### 系统架构

```
┌─────────────────────────────────────────────┐
│            前端 (Next.js)                    │
│   知识库管理 | 文档管理 | 检索问答          │
└─────────────────┬───────────────────────────┘
                  │ REST API / SSE
┌─────────────────┴───────────────────────────┐
│            后端 (FastAPI)                    │
│   KnowledgeBase Builder | Agentic Robot     │
└───┬─────────┬──────────┬───────────┬────────┘
    │         │          │           │
    ▼         ▼          ▼           ▼
┌────────┐ ┌───┐  ┌──────────┐  ┌────────┐
│SQLite  │ │S3 │  │OpenSearch│  │Bedrock │
└────────┘ └───┘  └──────────┘  └────────┘
```

---

## 项目结构

```
ask-prd/
├── docs/                       # 项目文档
│   ├── requirements.md         # 需求文档
│   ├── architecture.md         # 架构设计
│   ├── database.md             # 数据库设计
│   ├── api-overview.md         # API总览
│   ├── api-knowledge-base.md   # 知识库API
│   ├── api-documents.md        # 文档API
│   ├── api-sync-tasks.md       # 同步任务API
│   ├── api-query.md            # 问答API
│   ├── api-utilities.md        # 工具API
│   └── error-handling.md       # 错误处理
├── backend/                    # 后端代码（待创建）
│   ├── app/
│   │   ├── api/               # API接口
│   │   ├── models/            # 数据模型
│   │   ├── services/          # 业务逻辑
│   │   ├── agents/            # Agent实现
│   │   └── utils/             # 工具函数
│   ├── tests/                 # 测试代码
│   ├── requirements.txt       # Python依赖
│   └── main.py                # 入口文件
├── frontend/                   # 前端代码（待创建）
│   ├── src/
│   │   ├── pages/             # 页面
│   │   ├── components/        # 组件
│   │   └── services/          # API调用
│   ├── package.json           # Node依赖
│   └── next.config.js         # Next.js配置
├── scripts/                    # 脚本
├── .env.example               # 环境变量示例
└── README.md                  # 本文件
```

---

## 快速开始

### 环境要求

- Python 3.12
- Node.js 20+
- AWS账号（用于S3、OpenSearch、Bedrock）
  - Region: us-west-2（已配置所需权限）
- GPU（用于Marker PDF转换，推荐NVIDIA T4或更好）

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/your-org/ask-prd.git
cd ask-prd
```

#### 2. 配置AWS

```bash
# 配置AWS CLI (Region: us-west-2)
aws configure
# Default region name: us-west-2

# 当前开发服务器已具备以下权限：
# - S3: 读写权限
# - OpenSearch Serverless: 创建Collection权限
# - Bedrock: 调用模型权限（Claude Sonnet 4.5）
```

#### 3. 后端安装

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入AWS配置

# 初始化数据库
python scripts/init_db.py

# 启动服务
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### 4. 前端安装

```bash
cd frontend

# 安装依赖
npm install

# 配置环境变量
cp .env.example .env.local
# 编辑 .env.local 文件

# 启动开发服务器
npm run dev
```

#### 5. 访问应用

- 前端：http://localhost:3000
- 后端API：http://localhost:8000
- API文档：http://localhost:8000/docs

---

## 使用指南

### 1. 创建知识库

```bash
curl -X POST http://localhost:8000/api/v1/knowledge-bases \
  -H "Content-Type: application/json" \
  -d '{
    "name": "产品PRD知识库",
    "description": "产品迭代的所有PRD文档",
    "s3_bucket": "my-bucket",
    "s3_prefix": "prds/"
  }'
```

### 2. 上传文档

```bash
curl -X POST http://localhost:8000/api/v1/knowledge-bases/{kb_id}/documents/upload \
  -F "file=@/path/to/prd.pdf"
```

### 3. 同步数据

```bash
curl -X POST http://localhost:8000/api/v1/knowledge-bases/{kb_id}/sync \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "full_sync",
    "document_ids": []
  }'
```

### 4. 提问

访问前端 http://localhost:3000，在检索问答页面输入问题即可。

---

## API文档

完整的API文档请查看：
- [API总览](./docs/api-overview.md)
- [知识库管理API](./docs/api-knowledge-base.md)
- [文档管理API](./docs/api-documents.md)
- [同步任务API](./docs/api-sync-tasks.md)
- [检索问答API](./docs/api-query.md)
- [工具类API](./docs/api-utilities.md)

在线API文档：http://localhost:8000/docs（启动后端后访问）

---

## 设计文档

- [需求文档](./docs/requirements.md)
- [架构设计](./docs/architecture.md)
- [数据库设计](./docs/database.md)
- [错误处理](./docs/error-handling.md)

---

## 开发指南

### 后端开发

```bash
cd backend

# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试
pytest

# 代码格式化
black .
isort .

# 类型检查
mypy .

# 启动调试模式
uvicorn main:app --reload --log-level debug
```

### 前端开发

```bash
cd frontend

# 安装开发依赖
npm install

# 启动开发服务器（热更新）
npm run dev

# 代码格式化
npm run format

# 类型检查
npm run type-check

# 构建生产版本
npm run build
```

### 数据库操作

```bash
# 创建迁移
alembic revision --autogenerate -m "description"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

---

## 配置说明

### 环境变量（.env）

```bash
# AWS配置
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
S3_BUCKET=your-bucket
OPENSEARCH_ENDPOINT=your-opensearch-endpoint

# Bedrock配置
BEDROCK_REGION=us-west-2
EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
GENERATION_MODEL_ID=global.anthropic.claude-sonnet-4-5-20250929-v1:0

# 数据库配置
DATABASE_PATH=/data/aks-prd.db

# 缓存配置
CACHE_DIR=/data/cache
MAX_CACHE_SIZE_MB=2048

# 服务配置
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
```

---

## 部署指南

### 单机部署（推荐用于Demo）

```bash
# 1. 准备EC2实例
# - 实例类型：g4dn.xlarge（带GPU）
# - 存储：至少500GB EBS
# - 操作系统：Ubuntu 22.04

# 2. 安装依赖
sudo apt update
sudo apt install python3.11 python3-pip nodejs npm nginx

# 3. 安装CUDA（用于Marker）
# 参考NVIDIA官方文档

# 4. 部署应用
cd /opt
git clone https://github.com/your-org/ask-prd.git
cd ask-prd

# 后端
cd backend
pip install -r requirements.txt
# 配置 .env
# 使用systemd或supervisor管理进程

# 前端
cd ../frontend
npm install
npm run build
# 使用nginx作为静态文件服务器和反向代理

# 5. 配置nginx
sudo cp nginx.conf /etc/nginx/sites-available/ask-prd
sudo ln -s /etc/nginx/sites-available/ask-prd /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 生产部署（未来）

参考 [架构设计文档](./docs/architecture.md) 中的"扩展部署"章节。

---

## 常见问题

### Q1: Marker转换失败？

**A**: 检查：
1. GPU驱动是否正确安装
2. CUDA版本是否匹配
3. 磁盘空间是否充足
4. PDF文件是否损坏

### Q2: Bedrock调用失败？

**A**: 检查：
1. AWS凭证是否正确
2. 是否有Bedrock访问权限
3. 是否启用了对应的模型
4. 是否触发了限流

### Q3: OpenSearch连接失败？

**A**: 检查：
1. Collection是否已创建
2. 网络是否可达
3. 访问策略是否正确配置

### Q4: 查询无结果？

**A**: 可能原因：
1. 文档未完成同步
2. 查询词与文档内容不匹配
3. 尝试换个问法

---

## 性能优化建议

1. **缓存优化**
   - 启用本地文件缓存，减少S3访问
   - 使用Redis缓存查询结果

2. **并发优化**
   - 调整Sub-Agent并发数
   - 使用连接池

3. **成本优化**
   - 使用Bedrock On-Demand Throughput
   - 定期清理无用缓存

---

## 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

---

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 联系方式

- 项目主页：https://github.com/your-org/ask-prd
- 问题反馈：https://github.com/your-org/ask-prd/issues
- 文档：https://docs.your-org.com/ask-prd

---

## 致谢

- [marker](https://github.com/VikParuchuri/marker) - PDF转Markdown工具
- [AWS Bedrock](https://aws.amazon.com/bedrock/) - AI服务
- [LangChain](https://github.com/langchain-ai/langchain) - 文本处理框架
- [FastAPI](https://fastapi.tiangolo.com/) - Web框架
- [Next.js](https://nextjs.org/) - React框架

---

## 更新日志

### v1.0.0 (2025-01-20)
- ✨ 初始版本
- ✅ 知识库管理功能
- ✅ 文档上传和同步
- ✅ 智能检索问答
- ✅ 图文混排理解
- ✅ Multi-Agent协作
