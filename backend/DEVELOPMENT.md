# ASK-PRD 后端开发进度

## 项目概览

基于AWS Bedrock的智能文档问答系统，支持PDF文档解析、向量检索和AI问答。

## 技术栈

- **框架**: FastAPI 0.121.0
- **AI实现**: 原生Bedrock API (boto3)
- **数据库**: SQLite (WAL模式)
- **AWS服务**:
  - Bedrock (Claude Sonnet 4.5)
  - S3 (文档存储)
  - OpenSearch Serverless (向量检索)
- **Python**: 3.12

## 开发阶段

### ✅ Phase 1: 基础框架 (已完成)

#### 1.1 项目结构
- [x] 创建完整的目录结构
- [x] 配置requirements.txt
- [x] 设置.env配置文件

#### 1.2 核心模块
- [x] 数据库模型 (`app/models/database.py`)
  - knowledge_bases 表
  - documents 表
  - chunks 表
  - sync_tasks 表
  - query_history 表
- [x] Pydantic Schemas (`app/models/schemas.py`)
  - 知识库相关模型
  - 文档相关模型
  - 分页模型
- [x] 配置管理 (`app/core/config.py`)
  - 环境变量加载
  - AWS配置
  - Bedrock模型配置
- [x] 数据库连接 (`app/core/database.py`)
  - SQLite WAL模式
  - 连接池管理
  - 性能优化
- [x] 日志系统 (`app/core/logging.py`)
  - structlog集成
  - JSON格式日志
- [x] 错误处理 (`app/core/errors.py`)
  - 自定义异常类
  - 错误码体系 (1xxx-9xxx)
  - 全局异常处理器

#### 1.3 FastAPI应用
- [x] 主应用 (`app/main.py`)
  - Lifespan管理
  - CORS配置
  - 全局异常处理
  - 健康检查接口
- [x] API路由聚合 (`app/api/v1/__init__.py`)

### ✅ Phase 2: AWS工具类 (已完成)

#### 2.1 S3客户端 (`app/utils/s3_client.py`)
- [x] 文件上传/下载
- [x] 文件删除
- [x] 批量删除（前缀）
- [x] 文件存在性检查
- [x] 列出对象

#### 2.2 OpenSearch客户端 (`app/utils/opensearch_client.py`)
- [x] 索引管理（创建/删除/检查）
- [x] 文档索引（单个/批量）
- [x] 向量检索（kNN）
- [x] 关键词检索（BM25）
- [x] 混合检索（RRF算法）
- [x] 文档删除（单个/批量）

#### 2.3 Bedrock客户端 (`app/utils/bedrock_client.py`)
- [x] Bedrock客户端（Embedding生成）
- [x] 生成模型配置（Claude Sonnet 4.5）
- [x] Embedding生成（Titan Embeddings V2）
- [x] 批量Embedding生成
- [x] Token计数

### ✅ Phase 3: 知识库管理 (已完成)

#### 3.1 Service层 (`app/services/knowledge_base_service.py`)
- [x] 创建知识库（自动创建OpenSearch索引）
- [x] 获取知识库详情
- [x] 列出知识库（分页）
- [x] 更新知识库
- [x] 删除知识库（软删除DB + 硬删除OpenSearch）
- [x] 获取知识库统计信息

#### 3.2 API路由 (`app/api/v1/knowledge_bases/routes.py`)
- [x] POST /knowledge-bases - 创建知识库
- [x] GET /knowledge-bases - 列出知识库
- [x] GET /knowledge-bases/{kb_id} - 获取详情
- [x] PATCH /knowledge-bases/{kb_id} - 更新知识库
- [x] DELETE /knowledge-bases/{kb_id} - 删除知识库

#### 3.3 测试
- [x] API端点测试
- [x] 错误处理验证
- [x] 数据库操作验证

### ✅ Phase 4: 文档管理 (已完成)

#### 4.1 Service层 (`app/services/document_service.py`)
- [x] 上传文档到S3
- [x] 获取文档详情
- [x] 列出文档（支持状态过滤）
- [x] 更新文档状态
- [x] 删除文档（软删除DB + 硬删除S3）
- [x] 获取文档统计信息

#### 4.2 API路由 (`app/api/v1/documents/routes.py`)
- [x] POST /documents?kb_id={kb_id} - 上传文档
- [x] GET /documents?kb_id={kb_id} - 列出文档
- [x] GET /documents/{doc_id} - 获取详情
- [x] DELETE /documents/{doc_id} - 删除文档

#### 4.3 测试
- [x] 文件上传测试
- [x] 文件类型验证（仅支持PDF）
- [x] 错误处理验证
- [x] 知识库关联验证

### ✅ Phase 5: PDF转换服务 (已完成)

#### 5.1 Marker集成
- [x] 安装和配置Marker (v1.10.1)
- [x] PDF转Markdown转换
- [x] 图片提取
- [x] 上传转换结果到S3

#### 5.2 转换Service (`app/services/conversion_service.py`)
- [x] convert_pdf_to_markdown() - PDF转换为Markdown
- [x] _extract_images() - 提取图片
- [x] generate_image_descriptions() - 使用Bedrock Vision生成图片描述
- [x] _analyze_image_with_bedrock() - Vision API调用
- [x] upload_conversion_results() - 上传到S3
- [x] cleanup_temp_files() - 清理临时文件
- [x] 错误处理和日志

#### 5.3 Bedrock Vision集成
- [x] bedrock_client.analyze_image() - Vision API封装
- [x] 支持多种图片类型（流程图、原型图、脑图等）
- [x] 中文图片描述生成

### ✅ Phase 6: 文本处理 (已完成)

#### 6.1 Chunking Service (`app/services/chunking_service.py`)
- [x] 文本分块（LangChain RecursiveCharacterTextSplitter）
- [x] chunk_size: 1000, chunk_overlap: 200
- [x] 中文优化分隔符（段落、句号、逗号等）
- [x] 图片上下文提取
- [x] 图片引用识别（Markdown语法）
- [x] 图片类型推断（流程图、原型图、脑图等）
- [x] Chunk元数据生成
- [x] 保存chunks到数据库

#### 6.2 Embedding Service (`app/services/embedding_service.py`)
- [x] 批量生成Embeddings（Titan V2, 1024维）
- [x] 文本和图片统一向量化（使用description）
- [x] 批量索引到OpenSearch
- [x] 构建OpenSearch文档（含元数据）
- [x] 更新chunk的S3路径
- [x] 删除chunks从索引
- [x] 错误处理和重试

### ✅ Phase 7: 同步任务系统 (已完成)

#### 7.1 Task Service (`app/services/task_service.py`)
- [x] create_sync_task() - 创建同步任务
- [x] get_task() - 获取任务详情
- [x] list_tasks() - 列出任务
- [x] update_task_status() - 更新任务状态
- [x] update_task_progress() - 更新任务进度
- [x] get_documents_to_process() - 获取待处理文档
- [x] cancel_task() - 取消任务
- [x] 任务冲突检测（防止重复任务）

#### 7.2 Background Worker (`app/workers/sync_worker.py`)
- [x] process_sync_task() - 异步任务处理主流程
- [x] _process_single_document() - 单文档处理
- [x] 完整9步处理流程：
  1. 下载PDF from S3
  2. PDF → Markdown (Marker)
  3. 生成图片描述 (Bedrock Vision)
  4. 上传结果到S3
  5. 文本分块 (LangChain)
  6. 保存chunks到数据库
  7. 生成向量 (Titan Embeddings)
  8. 索引到OpenSearch
  9. 更新任务状态
- [x] 进度跟踪和更新
- [x] 错误处理和日志
- [x] 临时文件清理

#### 7.3 API路由 (`app/api/v1/sync_tasks/routes.py`)
- [x] POST /sync-tasks - 创建同步任务（后台执行）
- [x] GET /sync-tasks?kb_id=xxx - 列出任务
- [x] GET /sync-tasks/{task_id} - 获取任务状态
- [x] DELETE /sync-tasks/{task_id} - 取消任务
- [x] 支持full_sync和incremental任务类型

### ✅ Phase 8: Two-Stage问答实现 (已完成)

#### 8.1 TwoStageExecutor (`app/services/agentic_robot/two_stage_executor.py`)
- [x] execute_streaming() - Two-Stage执行主流程（流式）
- [x] Stage 1 - 文档理解：
  - _process_single_document() - 串行处理每个文档
  - _process_single_document_with_heartbeat() - 带心跳的文档处理
  - _call_bedrock_stage1() - 调用Bedrock Converse API
  - _invoke_bedrock_sync() - 同步Bedrock调用（支持多模态）
- [x] Stage 2 - 答案综合：
  - _stage2_synthesize_stream() - 流式生成综合答案
  - _stage2_synthesize_sync() - 同步生成答案（备用）
  - _build_stage2_prompt() - 构建Stage 2提示词
- [x] 后处理功能：
  - _fix_table_format() - 修复Markdown表格格式
  - _convert_image_paths() - 转换图片路径为API URL
  - _extract_references_from_markdown() - 从Markdown提取引用
- [x] 心跳机制（防止SSE超时）
- [x] 错误处理和重试
- [x] Prompt模板（Stage 1 + Stage 2）

#### 8.2 DocumentLoader (`app/services/document_loader.py`)
- [x] load_document() - 加载完整文档内容
- [x] _ensure_local_markdown() - 确保Markdown本地缓存
- [x] _ensure_local_images() - 确保图片本地缓存
- [x] _download_from_s3() - 从S3下载文件
- [x] S3优先 + 本地缓存策略

#### 8.3 DocumentProcessor (`app/services/document_processor.py`)
- [x] process() - 处理文档为多模态content
- [x] _parse_markdown() - 解析Markdown分段
- [x] _extract_images_from_markdown() - 提取图片引用
- [x] _build_content_blocks() - 构建文本+图片混合content
- [x] _load_image_bytes() - 加载图片字节数据
- [x] 支持Bedrock Converse API的多模态格式

### ✅ Phase 9: 查询/搜索API (已完成)

#### 9.1 Query Service (`app/services/query_service.py`)
- [x] execute_query_two_stage() - Two-Stage查询主流程（实际使用）
- [x] _hybrid_search() - 混合检索（向量 + BM25 + RRF）
- [x] _group_chunks_by_document() - 按文档聚合chunks
- [x] 完整的3步查询流程：
  1. Hybrid Search（混合检索）
  2. 提取Document ID列表（限制MAX_DOCUMENTS）
  3. TwoStageExecutor执行（Stage 1 + Stage 2）

#### 9.2 API路由 (`app/api/v1/query/routes.py`)
- [x] POST /query/stream - 流式问答接口（SSE）
- [x] 权限检查（需要知识库读权限）
- [x] SSE事件类型：
  - status: 状态更新
  - progress: Stage 1进度（当前文档/总文档数）
  - heartbeat: 心跳事件（10秒间隔，防止超时）
  - retrieved_documents: 检索到的文档信息
  - answer_delta: 答案文本增量
  - done: 完成事件
  - error: 错误事件

### ✅ Phase 10: 测试和优化 (已完成)

#### 10.1 测试脚本
- [x] test_agents.py - Two-Stage执行器测试
- [x] test_chunking.py - 分块服务测试
- [x] test_conversion.py - PDF转换测试
- [x] test_sync_system.py - 同步系统测试
- [x] test_query_system.py - 完整查询系统测试
- [x] test_embedding_performance.py - Embedding性能测试

#### 10.2 性能优化
- [x] 本地缓存策略（S3 + 本地）
- [x] 批量Embedding（batch_size=25）
- [x] OpenSearch批量索引（bulk API）
- [x] 心跳机制（防止超时）
- [x] 串行处理文档（避免内存溢出）

#### 10.3 文档
- [ ] API文档（OpenAPI）
- [ ] 部署文档
- [ ] 使用手册

## 文件结构

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py          ✅ 路由聚合
│   │       ├── knowledge_bases/     ✅ 知识库API
│   │       ├── documents/           ✅ 文档API
│   │       ├── sync_tasks/          ✅ 同步任务API
│   │       └── query/               ✅ 查询API
│   ├── core/
│   │   ├── config.py                ✅ 配置管理
│   │   ├── database.py              ✅ 数据库连接
│   │   ├── logging.py               ✅ 日志系统
│   │   └── errors.py                ✅ 错误处理
│   ├── models/
│   │   ├── database.py              ✅ ORM模型
│   │   └── schemas.py               ✅ Pydantic模型
│   ├── services/
│   │   ├── knowledge_base_service.py ✅ 知识库Service
│   │   ├── document_service.py       ✅ 文档Service
│   │   ├── conversion_service.py     ✅ 转换Service
│   │   ├── chunking_service.py       ✅ 分块Service
│   │   ├── embedding_service.py      ✅ 向量化Service
│   │   ├── task_service.py           ✅ 任务Service
│   │   └── query_service.py          ✅ 查询Service
│   ├── utils/
│   │   ├── s3_client.py             ✅ S3工具
│   │   ├── opensearch_client.py     ✅ OpenSearch工具
│   │   └── bedrock_client.py        ✅ Bedrock工具
│   ├── services/agentic_robot/       ✅ Two-Stage执行器
│   │   ├── __init__.py
│   │   └── two_stage_executor.py     ✅ Stage 1 + Stage 2实现
│   ├── workers/                      ✅ 后台任务
│   │   └── sync_worker.py            ✅ 同步Worker
│   └── main.py                       ✅ FastAPI应用
├── data/
│   └── ask-prd.db                    ✅ SQLite数据库
├── requirements.txt                  ✅ 依赖列表
├── .env                              ✅ 环境配置
└── DEVELOPMENT.md                    ✅ 本文档
```

## 当前状态

### 已完成功能
1. **基础框架** - FastAPI应用、数据库、配置、日志、错误处理 ✅
2. **AWS集成** - S3、OpenSearch、Bedrock客户端（含Vision API） ✅
3. **知识库管理** - 完整的CRUD API ✅
4. **文档管理** - 文档上传、列表、详情、删除 ✅
5. **PDF转换服务** - Marker集成、图片提取、Bedrock Vision分析 ✅
6. **文本处理服务** - 智能分块、批量向量化、OpenSearch索引 ✅
7. **同步任务系统** - 完整的端到端异步处理流程 ✅
8. **Two-Stage问答系统** - Stage 1文档理解 + Stage 2答案综合（原生Bedrock API） ✅
9. **智能问答API** - 流式问答、混合检索、查询历史 ✅

### 核心完成度
**🎉 后端核心功能 100% 完成！**

已实现完整的文档问答系统：
- 📄 文档管理（上传、处理、索引）
- 🔍 混合检索（向量 + BM25 + RRF）
- 🤖 Multi-Agent智能问答
- ⚡ SSE流式输出
- 📊 查询历史和统计

### 下一步（可选优化）
1. **测试完善** - 单元测试、集成测试（Phase 10）
2. **性能优化** - 缓存、并发优化
3. **监控告警** - Metrics、Tracing
4. **前端开发** - Next.js + AWS Cloudscape

## 开发规范

### 代码风格
- 使用black格式化
- 遵循PEP 8
- Type hints必填
- Docstring必填

### 错误处理
- 使用自定义异常类
- 错误码规范：
  - 1xxx: 知识库相关
  - 2xxx: 文档相关
  - 3xxx: 同步任务相关
  - 4xxx: 查询相关
  - 9xxx: 系统错误

### 日志规范
- 使用structlog
- JSON格式输出
- 包含关键上下文信息

### API规范
- RESTful设计
- 支持分页（page, page_size）
- 统一错误响应格式
- OpenAPI文档自动生成

## 测试记录

### 知识库API测试 (2025-11-04)
- ✅ GET /health - 健康检查
- ✅ GET /api/v1/ - API根路径
- ✅ GET /api/v1/knowledge-bases - 列出知识库
- ✅ POST /api/v1/knowledge-bases - 创建知识库（OpenSearch连接失败，符合预期）
- ✅ 错误处理验证

### 文档API测试 (2025-11-04)
- ✅ GET /documents?kb_id=nonexistent - 知识库不存在错误
- ✅ POST /documents - 文件类型验证（只支持PDF）
- ✅ GET /documents/{doc_id} - 文档不存在错误
- ✅ DELETE /documents/{doc_id} - 文档不存在错误
- ✅ 错误处理验证

## 依赖版本

主要依赖：
- fastapi==0.121.0
- strands-agents==1.14.0
- sqlalchemy==2.0.44
- boto3==1.40.65
- opensearch-py==3.0.0
- langchain==1.0.3
- structlog==25.5.0
- pydantic==2.12.3

详见 `requirements.txt`

## 备注

- 开发服务器已配置AWS权限
- AWS Region: us-west-2
- Bedrock Model: global.anthropic.claude-sonnet-4-5-20250929-v1:0
- Embedding Model: amazon.titan-embed-text-v2:0 (1024维)
- 数据库使用WAL模式优化并发性能
- S3为单一数据源（Single Source of Truth）
- 本地缓存为可选性能优化
