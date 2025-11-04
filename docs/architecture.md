# AKS-PRD 架构设计文档

> 版本：v1.0
> 更新时间：2025-01-20

---

## 一、系统架构概览

### 1.1 整体架构

AKS-PRD 采用前后端分离架构，主要分为两大子系统：

1. **KnowledgeBase Builder**（知识库构建系统）
   - 负责PDF文档解析
   - 图片理解和描述生成
   - 文本分块和向量化
   - 数据存储

2. **Agentic Robot**（智能问答系统）
   - 用户查询理解和重写
   - 向量检索
   - Multi-Agent文档阅读
   - 答案生成和引用提取

```
┌─────────────────────────────────────────────────────────────┐
│                         用户界面 (Next.js)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  知识库管理  │  │  文档管理    │  │  检索问答    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼ (REST API / SSE)
┌─────────────────────────────────────────────────────────────┐
│                    后端服务 (FastAPI)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  知识库服务  │  │  文档服务    │  │  问答服务    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │  同步任务引擎│  │  Agent引擎   │                        │
│  └──────────────┘  └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
         │              │              │               │
         ▼              ▼              ▼               ▼
┌──────────────┐ ┌───────────┐ ┌────────────┐ ┌──────────────┐
│   SQLite     │ │    S3     │ │ OpenSearch │ │   Bedrock    │
│  (元数据)     │ │  (文件)   │ │  (向量)    │ │  (AI模型)    │
└──────────────┘ └───────────┘ └────────────┘ └──────────────┘
```

### 1.2 技术栈

**前端**
- Framework: Next.js 14
- UI Library: AWS Cloudscape Design System
- 状态管理: React Hooks + Context
- HTTP Client: Fetch API
- SSE: EventSource

**后端**
- Framework: FastAPI (Python 3.11+)
- 异步任务: Celery + Redis（或简化版：Threading + Queue）
- ORM: SQLAlchemy
- 数据验证: Pydantic
- 日志: Python logging + structlog

**基础设施**
- 计算: AWS EC2 (带GPU，用于Marker)
- 存储: AWS S3
- 向量数据库: Amazon OpenSearch Serverless
- AI服务: AWS Bedrock (Claude Sonnet, Embedding模型)
- 元数据库: SQLite 3

**第三方工具**
- PDF转换: marker (datalab-to/marker)
- 文本分块: langchain.text_splitter

---

## 二、核心流程设计

### 2.1 知识库构建流程（KnowledgeBase Builder）

```
┌─────────────┐
│ 1. 上传PDF  │
│    到 S3    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ 2. 创建同步任务 (异步)                   │
└──────┬──────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│ 3. 后台Worker处理                         │
│    ┌─────────────────────────────────┐   │
│    │ 3.1 从S3下载PDF到本地          │   │
│    └─────────────┬───────────────────┘   │
│                  ▼                        │
│    ┌─────────────────────────────────┐   │
│    │ 3.2 使用Marker转换              │   │
│    │     PDF → Markdown + Images     │   │
│    └─────────────┬───────────────────┘   │
│                  ▼                        │
│    ┌─────────────────────────────────┐   │
│    │ 3.3 图片理解                    │   │
│    │  - 提取图片上下文               │   │
│    │  - 调用Bedrock Claude生成描述   │   │
│    │  - 创建图片chunk                │   │
│    └─────────────┬───────────────────┘   │
│                  ▼                        │
│    ┌─────────────────────────────────┐   │
│    │ 3.4 文本分块                    │   │
│    │  - Markdown按语义分块           │   │
│    │  - 包含图片描述的上下文         │   │
│    │  - 创建文本chunk                │   │
│    └─────────────┬───────────────────┘   │
│                  ▼                        │
│    ┌─────────────────────────────────┐   │
│    │ 3.5 向量化                      │   │
│    │  - 调用Bedrock Embedding        │   │
│    │  - 批量生成向量                 │   │
│    └─────────────┬───────────────────┘   │
│                  ▼                        │
│    ┌─────────────────────────────────┐   │
│    │ 3.6 存储                        │   │
│    │  - 向量存入OpenSearch           │   │
│    │  - 元数据存入SQLite             │   │
│    │  - Markdown+图片缓存本地        │   │
│    └─────────────────────────────────┘   │
└──────────────────────────────────────────┘
       │
       ▼
┌─────────────┐
│ 4. 任务完成 │
└─────────────┘
```

#### 2.1.1 图片处理详细流程

```python
# 伪代码
for image in extracted_images:
    # 1. 从markdown中找到图片的上下文
    context = extract_context_from_markdown(markdown, image)

    # 2. 调用Bedrock Claude Vision
    prompt = f"""
    这是一张来自PRD文档的图片。

    图片上下文：
    {context}

    请详细描述这张图片的内容，包括：
    1. 图片类型（流程图/原型图/架构图/其他）
    2. 核心内容
    3. 关键元素和关系
    """

    description = bedrock_claude_vision(image, prompt)

    # 3. 创建图片chunk
    chunk = Chunk(
        chunk_type='image',
        image_filename=image.name,
        image_description=description,
        content_with_context=f"{context}\n\n图片描述：{description}"
    )

    # 4. 生成embedding（基于描述）
    chunk.embedding = bedrock_embedding(chunk.content_with_context)
```

#### 2.1.2 文本分块策略

```python
# 分块参数
CHUNK_SIZE = 1000  # 字符数
CHUNK_OVERLAP = 200  # 重叠字符数

# 使用LangChain的RecursiveCharacterTextSplitter
splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", "。", "！", "？", " ", ""]
)

chunks = splitter.split_text(markdown_content)

# 为每个chunk增强上下文
for i, chunk_text in enumerate(chunks):
    # 查找chunk中引用的图片
    referenced_images = find_images_in_chunk(chunk_text)

    # 将图片描述添加到content_with_context
    enhanced_content = chunk_text
    for img in referenced_images:
        enhanced_content += f"\n\n[图片: {img.description}]"

    # 创建chunk记录
    chunk = Chunk(
        chunk_type='text',
        content=chunk_text,
        content_with_context=enhanced_content,
        chunk_index=i
    )
```

### 2.2 检索问答流程（Agentic Robot）

```
┌─────────────┐
│ 1. 用户提问 │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────┐
│ 2. Query Rewrite (Bedrock)       │
│    原始: "登录方式的演进"         │
│    重写: ["登录功能迭代历史"      │
│          "认证方式变更记录"       │
│          "用户登录模块演进"]      │
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ 3. Hybrid Search (OpenSearch)    │
│    - 向量检索 (语义相似)          │
│    - BM25检索 (关键词匹配)        │
│    - 结果合并和去重               │
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ 4. 按文档聚合chunk               │
│    Document1: [chunk1, chunk3]   │
│    Document2: [chunk5, chunk8]   │
│    Document3: [chunk2, chunk9]   │
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│ 5. Multi-Agent并发处理                   │
│   ┌─────────────────────────────────┐    │
│   │ Sub-Agent 1 (Document1)         │    │
│   │  - 下载markdown+图片到本地      │    │
│   │  - 读取完整文档                 │    │
│   │  - 提取与问题相关的信息         │    │
│   │  - 标记引用的chunk              │    │
│   └─────────────────────────────────┘    │
│   ┌─────────────────────────────────┐    │
│   │ Sub-Agent 2 (Document2)         │    │
│   └─────────────────────────────────┘    │
│   ┌─────────────────────────────────┐    │
│   │ Sub-Agent 3 (Document3)         │    │
│   └─────────────────────────────────┘    │
└──────┬───────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ 6. Main Agent综合生成            │
│    - 汇总sub-agent结果           │
│    - 调用Bedrock生成最终答案     │
│    - 合并引用列表                │
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ 7. 流式输出                      │
│    - SSE推送答案片段             │
│    - 推送引用信息                │
│    - 推送Token统计               │
└──────────────────────────────────┘
```

#### 2.2.1 Sub-Agent处理逻辑

```python
class SubAgent:
    def process(self, document_id: str, query: str, relevant_chunks: List[Chunk]):
        # 1. 获取文档内容（优先本地缓存）
        markdown_path = get_cached_document(document_id)
        if not markdown_path:
            markdown_path = download_from_s3(document_id)

        # 2. 读取文档内容
        markdown_content = read_file(markdown_path)

        # 3. 加载相关图片
        images = []
        for chunk in relevant_chunks:
            if chunk.chunk_type == 'image':
                image_path = get_cached_image(chunk.image_filename)
                images.append(image_path)

        # 4. 构建Prompt
        prompt = f"""
        你是一个专业的产品文档分析助手。请仔细阅读以下PRD文档，回答用户的问题。

        用户问题：{query}

        文档内容：
        {markdown_content}

        重点关注的片段：
        {format_relevant_chunks(relevant_chunks)}

        请输出：
        1. 针对用户问题的回答
        2. 引用的具体段落或图片（使用chunk_id标识）

        输出格式：
        {{
            "answer": "回答内容",
            "citations": [
                {{"chunk_id": "xxx", "reason": "引用原因"}},
                ...
            ]
        }}
        """

        # 5. 调用Bedrock（多模态输入）
        response = bedrock_claude(
            text=prompt,
            images=images
        )

        return response
```

#### 2.2.2 Main Agent综合逻辑

```python
class MainAgent:
    def synthesize(self, query: str, sub_agent_results: List[dict]):
        prompt = f"""
        你是一个产品知识问答助手。现在有多个文档的分析结果，请综合回答用户的问题。

        用户问题：{query}

        各文档的分析结果：
        {format_sub_results(sub_agent_results)}

        请综合以上信息，生成一个完整、准确、结构化的回答。
        如果不同文档有演进关系，请按时间顺序组织答案。

        输出要求：
        1. 使用Markdown格式
        2. 在相关段落后标注引用[^1][^2]
        3. 在回答末尾列出所有引用的chunk_id
        """

        # 流式生成
        for chunk in bedrock_claude_stream(prompt):
            yield chunk
```

### 2.3 Hybrid Search实现

```python
def hybrid_search(index_name: str, queries: List[str], top_k: int = 20):
    """
    混合检索：向量检索 + BM25关键词检索
    """
    all_results = []

    for query in queries:
        # 1. 向量检索
        query_embedding = bedrock_embedding(query)
        vector_results = opensearch_client.search(
            index=index_name,
            body={
                "query": {
                    "knn": {
                        "embedding": {
                            "vector": query_embedding,
                            "k": top_k
                        }
                    }
                }
            }
        )

        # 2. BM25关键词检索
        bm25_results = opensearch_client.search(
            index=index_name,
            body={
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["content^2", "content_with_context"],
                        "type": "best_fields"
                    }
                }
            }
        )

        # 3. 合并结果 (Reciprocal Rank Fusion)
        merged = reciprocal_rank_fusion(
            [vector_results, bm25_results],
            k=60  # RRF参数
        )

        all_results.extend(merged)

    # 4. 去重和排序
    deduplicated = deduplicate_by_chunk_id(all_results)
    sorted_results = sorted(deduplicated, key=lambda x: x['score'], reverse=True)

    return sorted_results[:top_k]
```

---

## 三、数据流设计

### 3.1 文档数据流

```
PDF (S3)
  │
  ├─→ 原始文件 (保留)
  │
  └─→ Marker转换
       │
       ├─→ Markdown文件 (S3 + 本地缓存)
       │
       └─→ 图片文件 (S3 + 本地缓存)
            │
            ├─→ 图片Chunk (SQLite + OpenSearch向量)
            │
            └─→ 文本Chunk (SQLite + OpenSearch向量)
```

### 3.2 元数据流

```
SQLite (本地数据库)
  │
  ├─→ knowledge_bases (知识库元数据)
  │
  ├─→ documents (文档元数据 + 文件路径)
  │
  ├─→ chunks (chunk元数据)
  │    │
  │    └─→ chunk_type = 'text' | 'image'
  │
  ├─→ sync_tasks (同步任务状态)
  │
  └─→ query_history (查询历史 + Token统计)
```

### 3.3 向量数据流

```
OpenSearch Serverless
  │
  └─→ Index per Knowledge Base
       │
       ├─→ Document ID (chunk.id)
       ├─→ Embedding Vector (768维)
       ├─→ Content (用于BM25)
       ├─→ Metadata (document_id, kb_id, chunk_type, etc.)
       └─→ Timestamp
```

---

## 四、关键技术决策

### 4.1 为什么选择SQLite？

**优势**：
- 零配置，本地文件，简化部署
- 适合单机场景
- 事务支持
- 轻量级，性能足够

**劣势**：
- 并发写入能力弱
- 无法多实例共享
- 无内置备份机制

**应对**：
- Demo阶段可接受
- 预留迁移到RDS的路径
- 使用连接池和事务控制
- 定期手动备份

### 4.2 为什么使用Multi-Agent而不是单次RAG？

**原因**：
1. **文档完整性**：单个chunk信息不完整，需要阅读整个文档才能理解上下文
2. **图文理解**：Markdown+图片需要多模态模型同时处理
3. **跨文档综合**：演进历史类问题需要对比多个版本文档
4. **引用准确性**：Sub-agent可以精确标注引用位置

**权衡**：
- 成本更高（多次Bedrock调用）
- 延迟更长（但可并发）
- 答案质量更好

### 4.3 为什么图片也作为Chunk？

**原因**：
1. **统一检索**：图片描述生成embedding后，可与文本在同一向量空间检索
2. **精准引用**：图片作为独立chunk，可以精确引用
3. **灵活展示**：前端根据chunk_type决定展示文本还是图片

**实现**：
- 图片chunk的`content_with_context`包含图片描述
- 图片chunk的`image_local_path`存储图片路径
- 检索时图片和文本chunk同等对待

### 4.4 为什么使用Hybrid Search？

**原因**：
1. **向量检索**：擅长语义理解，但对专有名词、数字不敏感
2. **BM25检索**：擅长关键词匹配，但缺乏语义理解
3. **互补增强**：结合两者，提高召回率和准确率

**实现**：
- OpenSearch原生支持Hybrid Search
- 使用Reciprocal Rank Fusion合并结果

---

## 五、部署架构

### 5.1 单机部署（Phase 1）

```
┌────────────────────────────────────────────────┐
│           EC2 Instance (GPU-enabled)            │
│                                                 │
│  ┌──────────────┐       ┌──────────────┐      │
│  │   Next.js    │       │   FastAPI    │      │
│  │  (Port 3000) │       │  (Port 8000) │      │
│  └──────────────┘       └──────────────┘      │
│                                                 │
│  ┌──────────────┐       ┌──────────────┐      │
│  │   SQLite     │       │   Marker     │      │
│  │   (本地DB)   │       │  (PDF转换)   │      │
│  └──────────────┘       └──────────────┘      │
│                                                 │
│  ┌──────────────┐       ┌──────────────┐      │
│  │ Sync Worker  │       │ 文件缓存      │      │
│  │ (后台任务)   │       │ (/data/cache) │      │
│  └──────────────┘       └──────────────┘      │
└────────────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
    ┌────────┐    ┌──────────┐   ┌─────────┐
    │   S3   │    │OpenSearch│   │ Bedrock │
    └────────┘    └──────────┘   └─────────┘
```

**配置建议**：
- 实例类型：g4dn.xlarge 或 g4dn.2xlarge（带GPU）
- 存储：至少500GB EBS（用于文件缓存）
- Nginx作为反向代理
- Supervisor管理进程

### 5.2 扩展部署（未来）

```
┌──────────────┐
│  CloudFront  │ (CDN)
└──────┬───────┘
       │
┌──────▼───────┐
│  ALB/NLB     │ (负载均衡)
└──────┬───────┘
       │
       ├─────────────────┬─────────────────┐
       ▼                 ▼                 ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   Web 1     │   │   Web 2     │   │   Web 3     │
│ (Next.js +  │   │ (Next.js +  │   │ (Next.js +  │
│  FastAPI)   │   │  FastAPI)   │   │  FastAPI)   │
└─────────────┘   └─────────────┘   └─────────────┘
       │                 │                 │
       └─────────────────┴─────────────────┘
                         │
       ┌─────────────────┼─────────────────┐
       ▼                 ▼                 ▼
┌─────────────┐   ┌──────────┐     ┌─────────┐
│  RDS (PG)   │   │ ElastiCache│   │   S3    │
│ (替代SQLite)│   │  (Redis)   │   └─────────┘
└─────────────┘   └──────────┘
                         │
       ┌─────────────────┴─────────────────┐
       ▼                                   ▼
┌──────────────┐                    ┌─────────┐
│  OpenSearch  │                    │ Bedrock │
└──────────────┘                    └─────────┘

┌─────────────────────────────────────────────┐
│         Marker Worker Pool (ECS/EC2)        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Worker 1 │  │ Worker 2 │  │ Worker 3 │  │
│  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────┘
```

---

## 六、性能优化策略

### 6.1 缓存策略

**文件缓存**：
- Markdown和图片下载后缓存到本地磁盘
- 使用LRU策略淘汰（保留最近使用的1000个文档）
- 检查逻辑：SQLite记录路径 → 检查文件是否存在 → 不存在则从S3下载

**Embedding缓存**：
- 相同文本的embedding结果缓存（使用Redis或内存）
- TTL: 24小时

**Query Rewrite缓存**：
- 相同问题的重写结果缓存
- TTL: 1小时

### 6.2 批处理

**Embedding批量化**：
```python
# 不推荐：逐个embedding
for chunk in chunks:
    chunk.embedding = bedrock_embedding(chunk.content)  # N次调用

# 推荐：批量embedding
texts = [chunk.content for chunk in chunks]
embeddings = bedrock_embedding_batch(texts, batch_size=25)  # 减少调用次数
```

**OpenSearch批量插入**：
```python
# 使用bulk API一次插入100条
opensearch_client.bulk(index=index_name, body=bulk_body)
```

### 6.3 并发控制

**Sub-Agent并发**：
```python
# 限制并发数为5，避免Bedrock限流
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(sub_agent.process, doc) for doc in documents]
```

**Marker处理并发**：
```python
# 单机只运行1个Marker进程（GPU资源限制）
# 任务队列排队处理
```

---

## 七、监控和日志

### 7.1 日志规范

```python
# 结构化日志
logger = structlog.get_logger()

logger.info(
    "sync_task_started",
    task_id=task_id,
    kb_id=kb_id,
    document_count=len(doc_ids)
)

logger.error(
    "pdf_conversion_failed",
    task_id=task_id,
    document_id=doc_id,
    error_code="3010",
    error=str(e),
    exc_info=True
)
```

### 7.2 关键指标（Phase 1）

- Token消耗记录（每次查询）
- 同步任务成功/失败率
- 查询响应时间

### 7.3 未来扩展

- CloudWatch Logs集成
- Prometheus + Grafana监控
- X-Ray分布式追踪

---

## 八、安全设计

### 8.1 AWS服务访问

- 使用IAM Role而非硬编码AccessKey
- 最小权限原则
- S3 Bucket启用版本控制

### 8.2 输入验证

- 文件类型检查（仅允许PDF）
- 文件大小限制（最大100MB）
- 路径穿越防护
- SQL注入防护（使用ORM参数化查询）

### 8.3 数据安全

- S3加密（SSE-S3或SSE-KMS）
- OpenSearch启用加密
- SQLite文件权限控制

---

## 九、未来优化方向

1. **成本优化**
   - 引入Reranker减少需要精读的文档数
   - 使用更小的模型处理简单问题
   - 向量维度降维

2. **性能优化**
   - 引入消息队列（SQS）解耦
   - Marker独立服务化
   - 分布式任务调度

3. **功能增强**
   - 多轮对话支持
   - 用户反馈机制
   - 答案质量评分

4. **架构演进**
   - 微服务化
   - 容器化部署（Docker + ECS）
   - 多租户支持
