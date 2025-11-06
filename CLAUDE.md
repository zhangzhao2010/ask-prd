# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

ASK-PRD 是一个基于PRD文档的智能检索问答系统（Demo项目），使用Multi-Agent架构实现图文混排文档的深度理解和智能问答。

**当前状态**：Phase 1-4已完成，后端和前端核心功能已实现

**技术栈核心**：
- 后端：Python 3.12 + FastAPI + SQLAlchemy + SQLite
- Agent框架：Strands Agents SDK（用于Multi-Agent实现）
- 前端：Next.js 16 + AWS Cloudscape Design System + TypeScript
- AI服务：AWS Bedrock
  - Region: us-west-2（已配置所需权限）
  - Model: Claude Sonnet 4.5 (global.anthropic.claude-sonnet-4-5-20250929-v1:0)
  - Embeddings: Titan Embeddings V2 (amazon.titan-embed-text-v2:0)
  - 通过Strands BedrockModel集成
- 向量数据库：Amazon OpenSearch Serverless
- PDF转换：marker（需要GPU支持）

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
       - 自动收集Token统计（通过AgentResult.metrics）
   - 自定义Orchestration：使用asyncio并发执行Sub-Agents，通过Semaphore限制并发数
   - 流式输出：Strands原生支持streaming，通过SSE推送答案和引用

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
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 数据库初始化
python scripts/init_db.py

# 运行开发服务器
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 调试模式
uvicorn main:app --reload --log-level debug

# 测试
pytest
pytest tests/test_specific.py  # 运行单个测试文件
pytest -v -s  # 详细输出

# 代码格式化和检查
black .
isort .
mypy .

# 数据库迁移
alembic revision --autogenerate -m "description"  # 创建迁移
alembic upgrade head  # 执行迁移
alembic downgrade -1  # 回滚迁移
```

### 前端开发（frontend/目录）

```bash
# 安装依赖
npm install

# 开发服务器
npm run dev

# 构建生产版本
npm run build

# 代码格式化和类型检查
npm run format
npm run type-check
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
```

## 数据库架构

### SQLite表结构（5张核心表）

- `knowledge_bases`: 知识库元数据，关联S3和OpenSearch
- `documents`: 文档元数据，记录PDF和转换后的Markdown路径
  - **不存储图片目录路径**：每个图片在chunks表有完整路径
- `chunks`: 统一的文本/图片块表，通过`chunk_type`字段区分（'text' | 'image'）
  - 图片chunk包含：`image_s3_key`（S3路径）和`image_local_path`（本地缓存路径）
- `sync_tasks`: 异步同步任务，管理PDF处理流程
- `query_history`: 查询历史和Token统计

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
- SQLite配置建议启用WAL模式提升并发性能

### 流式输出

- 使用FastAPI的StreamingResponse和SSE
- 前端使用EventSource接收
- 推送内容包括：答案片段、引用信息、Token统计、处理状态

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

## Python依赖（requirements.txt）

核心依赖包括：

```txt
# Agent框架
strands-agents>=0.1.0

# Web框架
fastapi>=0.100.0
uvicorn[standard]>=0.23.0

# 数据库
sqlalchemy>=2.0.0
alembic>=1.11.0

# AWS SDK
boto3>=1.28.0
opensearch-py>=2.3.0

# PDF处理
marker-pdf>=0.1.0  # 需要GPU支持

# 文本处理
langchain>=0.1.0
langchain-text-splitters>=0.0.1

# 数据验证
pydantic>=2.0.0

# 日志
structlog>=23.1.0

# 异步任务（可选）
celery>=5.3.0
redis>=4.6.0
```

## 环境变量配置

```bash
# AWS配置
AWS_REGION=us-west-2
S3_BUCKET=your-bucket
OPENSEARCH_ENDPOINT=your-opensearch-endpoint

# Bedrock配置（Strands会自动使用这些配置）
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

# 注意：当前开发服务器已配置所需的AWS权限，无需手动设置AccessKey
```

## 开发优先级

项目按5个Phase开发（见docs/TODO.md）：
1. Phase 1: 项目初始化和基础框架（当前阶段）
2. Phase 2: 知识库构建系统
3. Phase 3: 检索问答系统
4. Phase 4: 前端开发
5. Phase 5: 测试和优化

**当前状态**：Phase 1未开始，需要先创建backend/和frontend/目录结构
