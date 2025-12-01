# ASK-PRD Backend

基于PRD的智能检索问答系统 - 后端服务

## 技术栈

- Python 3.12
- FastAPI
- SQLAlchemy + SQLite
- 原生Bedrock API (boto3)
- AWS Bedrock / S3 / OpenSearch

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入AWS配置
vim .env
```

### 3. 初始化数据库

```bash
python scripts/init_db.py
```

### 4. 启动服务

```bash
# 开发模式（热重载）
python -m app.main

# 或使用uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 访问API文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- 健康检查: http://localhost:8000/health

## 项目结构

```
backend/
├── app/
│   ├── api/
│   │   └── v1/          # API路由
│   │       ├── knowledge_bases/  # 知识库管理
│   │       ├── documents/        # 文档管理
│   │       ├── sync_tasks/       # 同步任务
│   │       └── query/            # 检索问答
│   ├── models/          # SQLAlchemy模型
│   ├── services/        # 业务逻辑层
│   │   └── agentic_robot/  # Two-Stage执行器
│   ├── utils/           # 工具函数
│   ├── core/            # 核心配置
│   │   ├── config.py    # 配置管理
│   │   ├── database.py  # 数据库连接
│   │   ├── logging.py   # 日志配置
│   │   └── errors.py    # 异常定义
│   └── main.py          # FastAPI应用入口
├── scripts/             # 脚本工具
│   └── init_db.py       # 数据库初始化
├── tests/               # 测试代码
├── data/                # 数据目录（自动创建）
│   ├── ask-prd.db       # SQLite数据库
│   └── cache/           # 文件缓存
├── requirements.txt     # Python依赖
├── .env.example         # 环境变量模板
└── README.md            # 本文件
```

## 开发指南

### 代码格式化

```bash
# 使用black格式化
black app tests scripts

# 使用isort整理导入
isort app tests scripts

# 类型检查
mypy app
```

### 测试

```bash
# 运行所有测试
pytest

# 运行单个测试文件
pytest tests/test_xxx.py

# 带覆盖率
pytest --cov=app tests/
```

### 数据库迁移

```bash
# 创建迁移
alembic revision --autogenerate -m "description"

# 执行迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

## API接口

### 知识库管理

- `POST /api/v1/knowledge-bases` - 创建知识库
- `GET /api/v1/knowledge-bases` - 列出知识库（分页）
- `GET /api/v1/knowledge-bases/{kb_id}` - 获取知识库详情
- `PATCH /api/v1/knowledge-bases/{kb_id}` - 更新知识库
- `DELETE /api/v1/knowledge-bases/{kb_id}` - 删除知识库

### 文档管理

- `POST /api/v1/documents?kb_id={kb_id}` - 上传文档
- `GET /api/v1/documents?kb_id={kb_id}` - 列出文档
- `GET /api/v1/documents/{doc_id}` - 获取文档详情
- `DELETE /api/v1/documents/{doc_id}` - 删除文档

### 同步任务

- `POST /api/v1/sync-tasks` - 创建同步任务
- `GET /api/v1/sync-tasks/{task_id}` - 查询任务状态

### 检索问答

- `POST /api/v1/query` - 提交问题（流式输出）
- `GET /api/v1/query/history` - 查询历史

## 环境变量说明

```bash
# AWS配置
AWS_REGION=us-west-2
S3_BUCKET=your-bucket

# Bedrock配置
BEDROCK_REGION=us-west-2
GENERATION_MODEL_ID=global.anthropic.claude-sonnet-4-5-20250929-v1:0
EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0

# 数据库
DATABASE_PATH=./data/ask-prd.db

# 缓存
CACHE_DIR=./data/cache
MAX_CACHE_SIZE_MB=2048

# 服务
API_PORT=8000
DEBUG=true
LOG_LEVEL=INFO
```

## 开发进度

### ✅ Phase 1: 基础框架 (已完成)

- [x] 项目目录结构创建
- [x] 依赖管理（requirements.txt）
- [x] 配置管理（config.py）
- [x] 数据库模型（database.py）
- [x] Pydantic schemas（schemas.py）
- [x] 数据库初始化脚本
- [x] FastAPI应用框架
- [x] 错误处理机制
- [x] 结构化日志
- [x] 健康检查接口

### ✅ Phase 2: AWS工具类 (已完成)

- [x] S3客户端（上传/下载/删除）
- [x] OpenSearch客户端（索引/搜索/混合检索）
- [x] Bedrock客户端（Embedding生成）

### ✅ Phase 3: 知识库管理 (已完成)

- [x] 知识库Service层
- [x] 知识库CRUD API
- [x] OpenSearch索引自动管理
- [x] API测试验证

### ✅ Phase 4: 文档管理 (已完成)

- [x] 文档Service层
- [x] 文档上传API（支持PDF）
- [x] 文档列表/详情/删除API
- [x] S3集成和文件管理
- [x] API测试验证

### ✅ Phase 5-10: 已完成

- [x] PDF转换服务（Marker集成）
- [x] 文本处理（Chunking & Embedding）
- [x] 同步任务系统
- [x] Two-Stage问答（原生Bedrock API）
- [x] 查询/搜索API（Hybrid Search + SSE）
- [x] 测试和优化

详细开发进度请查看 [DEVELOPMENT.md](./DEVELOPMENT.md)

## 许可证

MIT
