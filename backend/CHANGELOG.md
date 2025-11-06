# 更新日志

所有重要的更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

## [未发布]

### 计划
- 单元测试和集成测试
- 性能优化和监控
- 前端开发

## [1.0.1] - 2025-11-05

### 改进
- **Query API增强**
  - SSE事件类型符合docs规范（chunk替代text_delta）
  - 添加tokens事件（单独发送Token统计）
  - 添加done事件（包含query_id）
  - 添加citation事件（引用信息流式推送）
- **新增接口**
  - GET /api/v1/chunks/{chunk_id}/image - 图片URL接口
  - DELETE /api/v1/query/history/{query_id} - 删除查询历史
- **Citation支持**
  - 自动提取相关chunks作为引用
  - 支持文本和图片引用
  - 包含document_name、chunk_index等元数据

### 修复
- 规范化SSE事件格式，更好支持前端集成

## [1.0.0] - 2025-11-05

🎉 **重要里程碑：后端核心功能全部完成！**

### 新增
- **智能问答API**（完整实现）
  - query_service.py - 查询服务（480行）
  - query/routes.py - 查询API路由（175行）
  - 完整的6步查询流程：
    1. Query Rewrite（查询优化）
    2. Hybrid Search（向量 + BM25 + RRF混合检索）
    3. 文档聚合（按document_id分组chunks）
    4. Sub-Agents并发执行（深度阅读文档）
    5. Main-Agent综合（流式输出答案）
    6. 保存查询历史（Token统计和响应时间）
  - Semaphore并发控制（最多5个Sub-Agent并发）
  - 本地缓存优先策略（性能优化）
- **Query API端点**
  - POST /api/v1/query/stream - 流式问答接口（SSE）
  - GET /api/v1/query/history - 查询历史列表（分页）
  - GET /api/v1/query/history/{query_id} - 查询详情
- **SSE事件类型**
  - status: 状态更新
  - retrieved_documents: 检索到的文档信息
  - text_delta: 答案文本增量
  - complete: 完成事件（含Token统计）
  - error: 错误事件

### 改进
- API版本号更新为v1.0.0
- 集成query router到API聚合
- 完整的端到端流程（上传→处理→索引→问答）

### 测试
- 查询系统集成测试（test_query_system.py）
- 完整流程验证

## [0.6.0] - 2025-11-05

### 新增
- **Multi-Agent系统**（完整实现）
  - document_tools.py - Agent工具（100行）
    - create_document_reader_tool() - 文档内容读取
    - create_image_reader_tool() - 图片信息读取
    - create_search_context_tool() - 检索上下文提供
    - 使用Strands @tool装饰器
  - sub_agent.py - Sub-Agent实现（230行）
    - create_sub_agent() - 创建Sub-Agent实例
    - invoke_sub_agent() - 异步调用Sub-Agent
    - 深度文档阅读和理解
    - 结构化输出（answer, has_relevant_info, confidence）
  - main_agent.py - Main-Agent实现（220行）
    - create_main_agent() - 创建Main-Agent实例
    - invoke_main_agent() - 非流式调用
    - invoke_main_agent_stream() - 流式调用（SSE）
    - 多文档结果综合
    - 识别共同点和差异
    - 时间顺序组织演进历史
    - 标注引用来源
    - Token统计自动收集
- **Strands框架集成**
  - BedrockModel配置（Claude Sonnet 4.5）
  - Agent工具系统（@tool装饰器）
  - 流式输出支持（stream_async）
  - Metrics自动收集

### 改进
- 完善Agent系统架构
- 优化Sub-Agent并发执行策略
- 添加详细的Agent日志

### 测试
- Agent系统集成测试（test_agents.py）
- Sub-Agent功能测试
- Main-Agent综合测试

## [0.5.0] - 2025-11-05

### 新增
- **同步任务系统**（完整实现）
  - task_service.py - 任务管理（创建、查询、更新、取消）
  - sync_worker.py - 后台异步Worker
  - 完整9步处理流程（PDF→Markdown→分块→向量化→索引）
  - 任务冲突检测（防止重复任务）
  - 进度跟踪和实时更新
  - 错误处理和失败重试
  - 临时文件自动清理
- **同步任务API**
  - POST /api/v1/sync-tasks - 创建任务（后台执行）
  - GET /api/v1/sync-tasks?kb_id=xxx - 列出任务
  - GET /api/v1/sync-tasks/{task_id} - 查询状态
  - DELETE /api/v1/sync-tasks/{task_id} - 取消任务
- **完整数据流程打通**
  - 用户上传PDF → 创建任务 → 后台处理 → 索引完成
  - 支持full_sync和incremental两种任务类型

### 改进
- API路由整合（知识库、文档、同步任务）
- 异步任务使用FastAPI BackgroundTasks
- 添加任务状态机（pending → running → completed/failed/partial_success）

### 测试
- 同步任务系统集成测试
- 完整流程组件测试
- 所有AWS客户端就绪测试

## [0.4.0] - 2025-11-05

### 新增
- **文本分块服务**（完整实现）
  - LangChain RecursiveCharacterTextSplitter集成
  - 中文优化分隔符（支持段落、句号、逗号等）
  - 图片引用识别和上下文提取
  - 图片类型智能推断（流程图、原型图、脑图、截图、图表）
  - Chunk元数据生成
  - 保存chunks到数据库
- **向量化服务**（完整实现）
  - 批量生成Embeddings（Titan Embeddings V2, 1024维）
  - 文本和图片统一向量化
  - 批量索引到OpenSearch
  - OpenSearch文档构建（含完整元数据）
  - 更新chunk S3路径
  - 删除chunks从索引

### 改进
- 完善chunk数据模型
- 添加图片类型字段
- 优化分块策略（适配中文）
- 批量处理优化（batch_size: 25）

### 测试
- 文本分块功能测试
- 图片chunk创建测试
- 向量化准备测试

## [0.3.0] - 2025-11-05

### 新增
- **PDF转换服务**（完整实现）
  - Marker集成 (v1.10.1)
  - PDF转Markdown转换
  - 图片自动提取
  - 使用Bedrock Claude Vision生成图片描述
  - 支持多种图片类型识别（流程图、原型图、脑图、截图、图表等）
  - 转换结果上传到S3
  - 临时文件自动清理
- **Bedrock Vision API封装**
  - bedrock_client.analyze_image()
  - 支持base64图片输入
  - 中文描述生成

### 改进
- 更新requirements.txt添加marker-pdf依赖
- 完善错误处理（PDFConversionError）
- 添加详细的转换日志

### 测试
- PDF转换服务基础测试
- 依赖模块集成测试（Marker + Bedrock + S3）

## [0.2.0] - 2025-11-04

### 新增
- 文档管理完整功能
  - 文档上传API（支持PDF文件）
  - 文档列表API（支持分页和状态过滤）
  - 文档详情API（包含统计信息）
  - 文档删除API（软删除DB + 硬删除S3）
- 文档Service层业务逻辑
  - S3文件上传和管理
  - 文档状态管理
  - 文档统计信息
- 更新Schema定义
  - DocumentDetailResponse
  - DocumentCreate
  - DocumentUpdate

### 改进
- 完善错误处理（S3UploadError）
- 优化文件上传流程
- 添加文件类型验证

### 测试
- 文档上传测试
- 文件类型验证测试
- 错误处理测试
- 知识库关联验证

## [0.1.0] - 2025-11-04

### 新增
- 项目基础框架
  - FastAPI应用结构
  - SQLAlchemy数据库模型（5张表）
  - Pydantic Schema定义
  - 配置管理系统
  - 结构化日志（structlog）
  - 错误处理体系

- AWS工具类
  - S3Client - 文件上传/下载/删除
  - OpenSearchClient - 索引管理/向量检索/混合检索（RRF）
  - BedrockClient - Strands集成/Embedding生成

- 知识库管理完整功能
  - 创建知识库（自动创建OpenSearch索引）
  - 列出知识库（分页）
  - 获取知识库详情（包含统计信息）
  - 更新知识库
  - 删除知识库（软删除DB + 硬删除OpenSearch）

- API接口
  - GET /health - 健康检查
  - GET /api/v1/ - API根路径
  - POST /api/v1/knowledge-bases - 创建知识库
  - GET /api/v1/knowledge-bases - 列出知识库
  - GET /api/v1/knowledge-bases/{kb_id} - 获取详情
  - PATCH /api/v1/knowledge-bases/{kb_id} - 更新知识库
  - DELETE /api/v1/knowledge-bases/{kb_id} - 删除知识库

### 技术选型
- Python 3.12
- FastAPI 0.121.0
- Strands Agents 1.14.0
- SQLAlchemy 2.0.44
- boto3 1.40.65
- opensearch-py 3.0.0
- structlog 25.5.0

### 数据库
- SQLite with WAL mode
- 5张核心表：
  - knowledge_bases - 知识库
  - documents - 文档
  - chunks - 文本/图片块
  - sync_tasks - 同步任务
  - query_history - 查询历史

### 测试
- 知识库API完整测试
- 错误处理验证
- OpenSearch集成测试

## [0.0.1] - 2025-11-03

### 新增
- 初始项目结构
- 需求和设计文档
- 数据库设计文档
- 架构设计文档

---

## 版本规范

- **主版本号 (Major)**: 重大架构变更或不兼容的API变更
- **次版本号 (Minor)**: 新功能添加，向后兼容
- **修订号 (Patch)**: Bug修复和小改进

## 变更类型

- **新增 (Added)**: 新功能
- **改进 (Changed)**: 现有功能的改进
- **弃用 (Deprecated)**: 即将移除的功能
- **移除 (Removed)**: 已移除的功能
- **修复 (Fixed)**: Bug修复
- **安全 (Security)**: 安全相关的改进
