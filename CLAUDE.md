# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

ASK-PRD 是一个基于PRD文档的智能检索问答系统（Demo项目），使用Multi-Agent架构实现图文混排文档的深度理解和智能问答。

**当前状态**：✅ Phase 1-4已完成并通过测试，系统已具备生产级别的功能完整性

**技术栈核心**：
- 后端：Python 3.12 + FastAPI + SQLAlchemy + SQLite
- Agent框架：Strands Agents SDK 1.14.0（用于Multi-Agent实现）
- 前端：Next.js 15.1.4 + AWS Cloudscape Design System + TypeScript + React 19
- AI服务：AWS Bedrock
  - Region: us-west-2（已配置所需权限）
  - Model: Claude Sonnet 4.5 (global.anthropic.claude-sonnet-4-5-20250929-v1:0)
  - Embeddings: Titan Embeddings V2 (amazon.titan-embed-text-v2:0, 1024维)
  - 通过Strands BedrockModel集成
- 向量数据库：Amazon OpenSearch Serverless
- PDF转换：marker 1.10.0+（需要GPU支持）

## 系统架构要点

### 两大核心子系统

1. **KnowledgeBase Builder（知识库构建）**
   - PDF通过marker转换为Markdown + 图片
   - 使用Bedrock Claude Vision API理解图片内容并生成描述
   - 文本和图片都作为独立的chunk向量化
   - 数据存储：SQLite（元数据）+ S3（文件）+ OpenSearch（向量）

2. **Agentic Robot（智能问答 - 基于Strands Agents）**
   - Query Rewrite：使用Strands Agent将用户问题重写为多个检索查询
   - Hybrid Search：向量检索（kNN）+ BM25关键词检索，使用RRF合并
   - Multi-Agent协作（使用Strands框架实现）：
     - Sub-Agent：每个Strands Agent实例负责深度阅读一个完整文档（Markdown+图片）
       - 使用`@tool`装饰器定义文档读取工具
       - 使用`structured_output`确保输出格式
       - 支持多模态输入（文本+图片）
     - Main Agent：另一个Strands Agent实例，综合所有Sub-Agent的结果生成最终答案
       - 使用BedrockModel的流式API
   - 自定义Orchestration：使用asyncio并发执行Sub-Agents，通过Semaphore限制并发数
   - 流式输出：通过SSE推送答案和引用

### 关键设计决策

1. **图片作为独立chunk**：图片生成描述后作为独立chunk向量化，与文本chunk在同一向量空间检索，便于精准引用

2. **Multi-Agent而非单次RAG**：因为单个chunk信息不完整，需要阅读整个文档（包括图片）才能准确回答，尤其是演进历史类跨文档问题

3. **SQLite而非RDS**：Demo阶段使用SQLite简化部署，但预留了迁移到RDS的路径（需要时修改Schema中的SQLite特有语法）

4. **本地文件缓存策略**：
   - **S3是唯一真实数据源**：所有Marker转换结果（Markdown+图片）必须上传S3持久化
   - **本地缓存加速访问**：从S3下载后缓存到`/data/cache/`，使用LRU策略，可以安全清理
   - **文件获取逻辑**：先检查本地缓存 → 不存在则从S3下载 → 下载后更新本地缓存
   - **为什么必须上传S3**：
     - 避免重复运行Marker（很耗时且需要GPU）
     - 本地缓存可能清理或丢失，S3保证数据持久化
     - 支持将来多实例部署（共享S3数据）
     - 灾难恢复能力

## Strands Agents框架使用要点

### 核心组件

1. **BedrockModel集成**
   ```python
   from strands.models import BedrockModel

   model = BedrockModel(
       model_id="global.anthropic.claude-sonnet-4-5-20250929-v1:0",
       region_name="us-west-2",
       temperature=0.3,
       streaming=True,
       max_tokens=4096
   )
   ```

2. **Agent创建和使用**
   ```python
   from strands import Agent, tool

   @tool
   def your_tool(param: str) -> str:
       """工具描述"""
       return "result"

   agent = Agent(
       model=model,
       tools=[your_tool],
       system_prompt="系统提示词"
   )

   # 同步调用
   result = agent("用户输入")

   # 流式调用
   async for event in agent.stream_async("用户输入"):
       if event.type == "text_delta":
           print(event.data)

   # 结构化输出
   from pydantic import BaseModel
   class Output(BaseModel):
       answer: str

   result = agent.structured_output(Output, "用户输入")
   ```

3. **Multi-Agent Orchestration**
   - 使用asyncio并发执行多个Agent实例
   - 通过Semaphore控制并发数（避免Bedrock限流）
   - 每个Sub-Agent是独立的Strands Agent实例
   - Main-Agent综合所有结果

4. **Metrics收集**
   ```python
   result = agent("query")
   metrics = result.metrics.accumulated_usage
   # 包含：inputTokens, outputTokens, totalTokens
   # 如果启用caching：cacheReadInputTokens, cacheWriteInputTokens
   ```

### Strands框架文档

项目使用Strands Agents SDK的MCP工具可以查询文档：
- `mcp__strands__search_docs`：搜索文档
- `mcp__strands__fetch_doc`：获取完整文档内容

常用查询：
- "agent basic usage"
- "bedrock model configuration"
- "python tools define"
- "multi-agent patterns"
- "streaming output"

## 开发命令

### 后端开发（backend/目录）

```bash
# 环境准备
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 数据库初始化
python scripts/init_db.py

# 运行开发服务器（推荐方式）
python -m app.main

# 或使用uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 调试模式
LOG_LEVEL=DEBUG python -m app.main

# 查看API文档（开发模式）
# 访问 http://localhost:8000/docs (Swagger UI)
# 访问 http://localhost:8000/redoc (ReDoc)
# 访问 http://localhost:8000/health (健康检查)

# 测试脚本（scripts/目录下）
python scripts/test_agents.py              # Agent系统测试
python scripts/test_chunking.py            # 分块服务测试
python scripts/test_conversion.py          # PDF转换测试
python scripts/test_sync_system.py         # 同步系统测试
python scripts/test_query_system.py        # 完整查询系统测试
python scripts/test_embedding_performance.py  # Embedding性能测试

# 单个文档同步测试
python test_sync_single.py

# 单元测试
pytest
pytest tests/test_specific.py  # 运行单个测试文件
pytest -v -s                   # 详细输出

# 代码格式化和检查
black app/ tests/ scripts/
isort app/ tests/ scripts/
mypy app/

# 数据库操作
# 查看数据库
sqlite3 data/aks-prd.db ".tables"
sqlite3 data/aks-prd.db ".schema knowledge_bases"

# 数据库迁移（如果使用alembic）
alembic revision --autogenerate -m "description"  # 创建迁移
alembic upgrade head                              # 执行迁移
alembic downgrade -1                              # 回滚迁移
```

### 前端开发（frontend/目录）

```bash
# 安装依赖
cd frontend
npm install

# 开发服务器（带启动脚本）
./start-dev.sh

# 或直接运行
npm run dev

# 访问前端
# http://localhost:3000

# 构建生产版本
npm run build
npm run start

# Lint和类型检查
npm run lint
```

### AWS服务配置

```bash
# 配置AWS CLI（Region: us-west-2）
aws configure
# Default region name: us-west-2

# 当前开发服务器已具备的AWS权限：
# - S3: 读写权限
# - OpenSearch Serverless: 创建Collection和Index
# - Bedrock: 调用模型权限
#   - Claude Sonnet 4.5 (global.anthropic.claude-sonnet-4-5-20250929-v1:0)
#   - Titan Embeddings V2 (amazon.titan-embed-text-v2:0)

# 测试AWS连接
aws s3 ls s3://your-bucket/
aws bedrock list-foundation-models --region us-west-2
```

## 项目结构

### 后端结构

```
backend/
├── app/
│   ├── api/v1/          # API路由
│   │   ├── knowledge_bases/  # 知识库管理
│   │   ├── documents/        # 文档管理
│   │   ├── sync_tasks/       # 同步任务
│   │   ├── query/            # 检索问答
│   │   └── chunks/           # Chunks管理
│   ├── models/          # SQLAlchemy模型和Pydantic schemas
│   │   ├── database.py       # ORM模型
│   │   └── schemas.py        # API数据模型
│   ├── services/        # 业务逻辑层
│   │   ├── knowledge_base_service.py
│   │   ├── document_service.py
│   │   ├── conversion_service.py    # PDF转换（Marker）
│   │   ├── chunking_service.py      # 文本分块
│   │   ├── embedding_service.py     # 向量化
│   │   ├── task_service.py          # 任务管理
│   │   ├── query_service.py         # 查询服务
│   │   ├── document_loader.py       # 文档加载
│   │   ├── document_processor.py    # 文档处理
│   │   ├── reference_extractor.py   # 引用提取
│   │   └── agentic_robot/           # Agent系统目录
│   ├── agents/          # Strands Agent实现
│   │   ├── tools/
│   │   │   └── document_tools.py    # 文档读取工具
│   │   ├── sub_agent.py             # Sub-Agent
│   │   └── main_agent.py            # Main-Agent
│   ├── workers/         # 后台任务
│   │   └── sync_worker.py           # 同步Worker（异步处理PDF转换和索引）
│   ├── utils/           # 工具函数
│   │   ├── s3_client.py             # S3客户端
│   │   ├── opensearch_client.py     # OpenSearch客户端
│   │   └── bedrock_client.py        # Bedrock客户端（Strands集成）
│   ├── core/            # 核心配置
│   │   ├── config.py                # 配置管理
│   │   ├── database.py              # 数据库连接
│   │   ├── logging.py               # 日志配置
│   │   └── errors.py                # 异常定义
│   └── main.py          # FastAPI应用入口
├── scripts/             # 测试和工具脚本
│   ├── init_db.py                   # 数据库初始化
│   ├── test_agents.py               # Agent测试
│   ├── test_chunking.py             # 分块测试
│   ├── test_conversion.py           # 转换测试
│   ├── test_sync_system.py          # 同步测试
│   ├── test_query_system.py         # 查询测试
│   └── test_embedding_performance.py # 性能测试
├── tests/               # 单元测试
├── data/                # 数据目录
│   ├── aks-prd.db       # SQLite数据库
│   └── cache/           # 本地文件缓存
│       ├── documents/   # 文档缓存
│       └── temp/        # 临时文件
├── requirements.txt     # Python依赖
├── .env                 # 环境变量
└── README.md            # 项目说明
```

### 前端结构

```
frontend/
├── app/                 # Next.js App Router
│   ├── layout.tsx       # 根布局
│   ├── page.tsx         # 首页
│   └── knowledge-bases/ # 知识库页面
├── components/          # React组件
│   ├── common/          # 通用组件
│   ├── documents/       # 文档管理组件
│   ├── knowledge-bases/ # 知识库管理组件
│   └── query/           # 查询组件
├── services/            # API服务
│   └── api.ts           # 后端API调用
├── types/               # TypeScript类型定义
├── lib/                 # 工具函数
└── public/              # 静态资源
```

## 数据库架构

### SQLite表结构（5张核心表）

- `knowledge_bases`: 知识库元数据，关联S3和OpenSearch
- `documents`: 文档元数据，记录PDF和转换后的Markdown路径
  - **不存储图片目录路径**：每个图片在chunks表有完整路径
- `chunks`: 统一的文本/图片块表，通过`chunk_type`字段区分（'text' | 'image'）
  - 图片chunk包含：`image_s3_key`（S3路径）和`image_local_path`（本地缓存路径）
- `sync_tasks`: 异步同步任务，管理PDF处理流程
- `query_history`: 查询历史记录（包含Token统计）

**路径管理原则**：
- **S3路径**：必须存储，是唯一真实数据源
  - documents.s3_key_markdown: Markdown的S3路径
  - chunks.image_s3_key: 每个图片的S3路径
- **本地缓存路径**：可选，可以从document_id推导
  - 路径规则：`/data/cache/documents/{document_id}/content.md`
  - 路径规则：`/data/cache/documents/{document_id}/images/{image_filename}`
- **为什么不存储图片目录**：每个图片chunk已有完整路径，目录路径冗余

### OpenSearch Index

- 每个知识库对应一个独立Index，命名格式：`kb_{kb_id}_index`
- embedding向量维度：1024（Titan Embeddings V2）
- 同时支持向量检索（kNN）和BM25关键词检索

## 关键注意事项

### PDF转换（marker）

- marker依赖GPU（推荐NVIDIA T4或更好）
- 转换速度受GPU性能限制，单机建议串行处理（任务队列）
- 转换失败需要清晰的错误提示和重试机制

### Bedrock API限流

- 高并发时需要实现重试机制（指数退避）
- Sub-Agent并发数建议限制为5，避免触发限流
- Embedding API支持批量调用（batch_size=25），减少调用次数

### 文件缓存管理

**S3路径规划**：
```
s3://bucket/prds/product-a/           # S3 prefix (知识库配置)
├── doc.pdf                           # 原始PDF
└── converted/                        # 转换结果目录
    └── doc-{uuid}/                   # 按document_id组织
        ├── content.md                # Markdown文件
        └── images/                   # 图片目录
            ├── img_001.png
            └── img_002.png
```

**本地缓存路径**：
```
/data/cache/documents/{document_id}/
├── content.md                        # Markdown缓存
└── images/                           # 图片缓存
    ├── img_001.png
    └── img_002.png
```

**文件获取策略**：
- 检查逻辑：SQLite记录路径 → 检查本地文件存在 → 不存在则从S3下载 → 更新本地缓存
- LRU策略：保留最近使用的1000个文档，超出则清理
- **关键**：本地缓存丢失不影响系统运行，会自动从S3恢复

**删除文档时的清理顺序**：
1. 从OpenSearch删除向量
2. 从SQLite删除元数据
3. 从S3删除原始PDF和转换结果（`s3://bucket/prds/.../doc.pdf` 和 `s3://bucket/prds/.../converted/doc-xxx/`）
4. 从本地删除缓存（`/data/cache/documents/doc-xxx/`）

### 数据一致性

- 删除操作使用事务确保多个数据源的一致性
- 外键级联删除：删除知识库自动删除关联的documents和chunks
- SQLite配置已启用WAL模式提升并发性能

### 流式输出

- 使用FastAPI的StreamingResponse和SSE
- 前端使用EventSource接收
- 推送内容包括：答案片段、引用信息、Token统计、处理状态

### 前端交互设计

**上传和同步分离**：
- 上传文档：仅上传PDF到S3，文档状态设为`uploaded`
- 同步数据：用户手动点击"同步数据"按钮触发处理（Marker转换、向量化等）
- **不自动触发**：上传后不会自动创建同步任务

**进度查询**：
- **不使用自动轮询**：避免不必要的API请求和服务器负载
- **手动刷新**：用户点击"刷新"按钮查询同步任务进度
- 长时间运行的任务不会造成大量轮询请求

## 文本分块策略

- 使用LangChain的`RecursiveCharacterTextSplitter`
- chunk_size: 1000字符
- chunk_overlap: 200字符
- 分隔符优先级：`["\n\n", "\n", "。", "！", "？", " ", ""]`
- 文本chunk的`content_with_context`包含引用图片的描述

## API设计规范

- RESTful风格，路径格式：`/api/v1/{resource}`
- 统一错误响应格式（见docs/error-handling.md）
- 流式接口使用SSE（text/event-stream）
- 分页参数：`page`（从1开始）和`page_size`

## 项目文档位置

完整的设计文档在`docs/`目录：
- `requirements.md`: 功能需求和验收标准
- `architecture.md`: 详细架构设计和实现伪代码
- `database.md`: 完整的Schema和示例数据
- `api-*.md`: 各模块的API接口设计
- `error-handling.md`: 错误码规范
- `TODO.md` + `todo-phase*.md`: 开发任务清单
- `design-*.md`: 设计文档（本地存储、两阶段查询等）

## Python依赖（requirements.txt）

核心依赖包括：

```txt
# Web框架
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
python-multipart>=0.0.9

# Strands Agent框架
strands-agents>=0.1.0

# 数据库
sqlalchemy>=2.0.35
alembic>=1.13.0

# AWS SDK
boto3>=1.35.0
opensearch-py>=2.7.0
requests-aws4auth>=1.2.0

# PDF处理（需要GPU支持）
marker-pdf>=1.10.0

# 文本处理
langchain>=0.3.0
langchain-text-splitters>=0.3.0
tiktoken>=0.7.0

# 数据验证
pydantic>=2.9.0
pydantic-settings>=2.5.0

# 日志
structlog>=24.4.0

# 工具库
python-dotenv>=1.0.0
httpx>=0.27.0

# 开发依赖
pytest>=8.3.0
pytest-asyncio>=0.24.0
black>=24.8.0
isort>=5.13.0
mypy>=1.11.0
```

## 环境变量配置

```bash
# AWS配置
AWS_REGION=us-west-2
S3_BUCKET=your-bucket
S3_PREFIX=aks-prd/

# OpenSearch配置
OPENSEARCH_ENDPOINT=your-opensearch-endpoint

# Bedrock配置（Strands会自动使用这些配置）
BEDROCK_REGION=us-west-2
EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
GENERATION_MODEL_ID=global.anthropic.claude-sonnet-4-5-20250929-v1:0

# 数据库配置
DATABASE_PATH=./data/aks-prd.db

# 缓存配置
CACHE_DIR=./data/cache
MAX_CACHE_SIZE_MB=2048

# 服务配置
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true
LOG_LEVEL=INFO

# 注意：当前开发服务器已配置所需的AWS权限，无需手动设置AccessKey
```

## 已完成功能

### ✅ Phase 1-4: 核心功能（已完成并测试）

1. **文档管理系统**
   - PDF文档上传到S3
   - 文档列表、详情、删除
   - 文档状态管理（pending/processing/completed/failed）
   - 文档统计信息

2. **知识库管理**
   - 知识库CRUD操作
   - 自动创建OpenSearch索引
   - 知识库统计信息
   - 软删除DB + 硬删除OpenSearch

3. **PDF转换服务**
   - Marker集成（GPU加速）
   - PDF转Markdown（保留格式）
   - 图片自动提取
   - Bedrock Vision生成图片描述

4. **文本处理**
   - 智能分块（LangChain RecursiveCharacterTextSplitter）
   - 中文优化分隔符
   - 图片引用识别
   - 图片上下文提取

5. **向量化和索引**
   - 批量生成Embeddings（Titan V2, 1024维）
   - 文本和图片统一向量化
   - OpenSearch批量索引（bulk API）

6. **同步任务系统**
   - 异步任务管理（创建、查询、取消）
   - 完整9步处理流程
   - 任务冲突检测
   - 进度跟踪和错误处理

7. **Multi-Agent智能问答**
   - Sub-Agent（文档深度阅读）
   - Main-Agent（结果综合）
   - Strands框架集成
   - Agent工具系统（@tool装饰器）
   - 并发控制（Semaphore）

8. **智能检索和问答**
   - Hybrid Search（向量 + BM25 + RRF）
   - 流式问答（SSE）
   - 查询历史记录
   - Token统计和响应时间追踪

9. **前端界面**
   - Next.js + AWS Cloudscape Design System
   - 知识库管理界面
   - 文档上传和管理
   - 同步任务管理
   - 流式问答界面

## 测试状态

### 已测试模块
- ✅ 知识库API（完整测试）
- ✅ 文档API（完整测试）
- ✅ AWS工具类（S3/OpenSearch/Bedrock）
- ✅ PDF转换服务
- ✅ 文本分块服务
- ✅ 向量化服务
- ✅ 同步任务系统
- ✅ Agent系统
- ✅ 查询系统

### 测试脚本位置
- `backend/scripts/test_agents.py` - Agent系统测试
- `backend/scripts/test_chunking.py` - 分块服务测试
- `backend/scripts/test_conversion.py` - 转换服务测试
- `backend/scripts/test_sync_system.py` - 同步系统测试
- `backend/scripts/test_query_system.py` - 查询系统测试
- `backend/scripts/test_embedding_performance.py` - Embedding性能测试

## 性能优化要点

1. **本地缓存策略**：优先使用本地缓存，S3作为备份，LRU清理策略
2. **批量处理**：Embedding批量生成（batch_size: 25）、OpenSearch批量索引（bulk API）
3. **并发控制**：Sub-Agent并发执行（asyncio）、Semaphore限流（max: 5）
4. **数据库优化**：SQLite WAL模式、索引优化、连接池管理

## 已知限制

1. **Marker依赖GPU**：PDF转换需要GPU支持（推荐NVIDIA T4或更好）
2. **并发限制**：Sub-Agent并发数限制为5，避免Bedrock限流
3. **SQLite单机**：当前使用SQLite，不支持多实例部署（可迁移到RDS）
4. **无认证**：当前版本无用户认证和权限管理

## 常见问题排查

### 启动失败
```bash
# 检查Python版本
python --version  # 需要3.12+

# 检查依赖
pip list | grep -E "fastapi|strands|boto3"

# 检查数据库
ls -lh backend/data/aks-prd.db

# 重新初始化数据库
rm backend/data/aks-prd.db*
cd backend && python scripts/init_db.py
```

### AWS连接问题
```bash
# 检查AWS配置
aws configure list
aws sts get-caller-identity

# 测试S3访问
aws s3 ls s3://your-bucket/

# 测试Bedrock访问
aws bedrock list-foundation-models --region us-west-2
```

### OpenSearch连接失败
```bash
# 检查endpoint配置
echo $OPENSEARCH_ENDPOINT

# 测试连接
curl -X GET "https://$OPENSEARCH_ENDPOINT/_cluster/health"
```

## 下一步改进方向（可选）

- [ ] 用户认证和权限管理
- [ ] 多租户支持
- [ ] 缓存自动清理（LRU）
- [ ] 监控和告警
- [ ] Metrics收集
- [ ] 单元测试覆盖率提升
- [ ] 性能压力测试
- [ ] 迁移到RDS（生产环境）
