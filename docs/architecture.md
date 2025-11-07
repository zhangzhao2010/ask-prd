# ASK-PRD 架构设计文档

> 版本：v1.0
> 更新时间：2025-01-20

---

## 一、系统架构概览

### 1.1 整体架构

ASK-PRD 采用前后端分离架构，主要分为两大子系统：

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
- Framework: Next.js 16
- UI Library: AWS Cloudscape Design System
- 状态管理: React Hooks + Context
- HTTP Client: Fetch API
- SSE: EventSource

**后端**
- Framework: FastAPI (Python 3.12)
- Agent框架: Strands Agents SDK
- Multi-Agent模式: 自定义Orchestration（基于Strands Agent）
- 异步任务: Celery + Redis（或简化版：Threading + Queue）
- ORM: SQLAlchemy
- 数据验证: Pydantic
- 日志: Python logging + structlog

**基础设施**
- 计算: AWS EC2 (带GPU，用于Marker)
- 存储: AWS S3
- 向量数据库: Amazon OpenSearch Serverless
- AI服务: AWS Bedrock (Claude Sonnet 4.5, Titan Embeddings V2)
  - Region: us-west-2
  - Model ID: global.anthropic.claude-sonnet-4-5-20250929-v1:0
  - 已配置所需权限
- 元数据库: SQLite 3

**第三方工具**
- PDF转换: marker (datalab-to/marker)
- 文本分块: langchain.text_splitter

---

## 二、核心流程设计

### 2.1 知识库构建流程（KnowledgeBase Builder）

```
┌─────────────────────────────┐
│ 1. 用户上传PDF              │
│    - 前端调用upload接口     │
│    - PDF上传到S3            │
│    - 文档状态设为uploaded   │
└──────┬──────────────────────┘
       │
       │ (用户操作分界线 - 需要手动触发下一步)
       │
       ▼
┌─────────────────────────────────────────┐
│ 2. 用户点击"同步数据"按钮                │
│    - 前端调用sync接口                    │
│    - 创建同步任务 (异步)                 │
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
│    │ 3.3 上传转换结果到S3            │   │
│    │  - 上传Markdown文件到S3         │   │
│    │  - 上传所有图片到S3             │   │
│    │  - 记录S3路径到数据库           │   │
│    │  - 同时缓存到本地               │   │
│    └─────────────┬───────────────────┘   │
│                  ▼                        │
│    ┌─────────────────────────────────┐   │
│    │ 3.4 图片理解                    │   │
│    │  - 提取图片上下文               │   │
│    │  - 调用Bedrock Claude生成描述   │   │
│    │  - 创建图片chunk                │   │
│    └─────────────┬───────────────────┘   │
│                  ▼                        │
│    ┌─────────────────────────────────┐   │
│    │ 3.5 文本分块                    │   │
│    │  - Markdown按语义分块           │   │
│    │  - 包含图片描述的上下文         │   │
│    │  - 创建文本chunk                │   │
│    └─────────────┬───────────────────┘   │
│                  ▼                        │
│    ┌─────────────────────────────────┐   │
│    │ 3.6 向量化                      │   │
│    │  - 调用Bedrock Embedding        │   │
│    │  - 批量生成向量                 │   │
│    └─────────────┬───────────────────┘   │
│                  ▼                        │
│    ┌─────────────────────────────────┐   │
│    │ 3.7 存储                        │   │
│    │  - 向量存入OpenSearch           │   │
│    │  - 元数据存入SQLite             │   │
│    │  (Markdown+图片已在3.3上传S3)  │   │
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

### 2.2 检索问答流程（Agentic Robot - 基于Strands Agent框架）

```
┌─────────────┐
│ 1. 用户提问 │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────┐
│ 2. Query Rewrite Agent           │
│    使用Strands Agent + Tool      │
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
│    使用Strands Swarm模式                 │
│   ┌─────────────────────────────────┐    │
│   │ Sub-Agent 1 (Document1)         │    │
│   │  Strands Agent实例              │    │
│   │  - 使用Tool下载markdown+图片    │    │
│   │  - 读取完整文档                 │    │
│   │  - 提取与问题相关的信息         │    │
│   │  - 返回structured output        │    │
│   └─────────────────────────────────┘    │
│   ┌─────────────────────────────────┐    │
│   │ Sub-Agent 2 (Document2)         │    │
│   │  独立的Strands Agent实例        │    │
│   └─────────────────────────────────┘    │
│   ┌─────────────────────────────────┐    │
│   │ Sub-Agent 3 (Document3)         │    │
│   │  独立的Strands Agent实例        │    │
│   └─────────────────────────────────┘    │
└──────┬───────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ 6. Main Agent综合生成            │
│    Strands Agent + Tools         │
│    - 汇总sub-agent结果           │
│    - 使用BedrockModel流式生成    │
│    - 合并引用列表                │
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ 7. 流式输出                      │
│    - Strands原生streaming支持    │
│    - SSE推送答案片段             │
│    - 推送引用信息                │
│    - 自动收集Token统计           │
└──────────────────────────────────┘
```

#### 2.2.1 Sub-Agent处理逻辑（使用Strands Agent框架）

```python
from strands import Agent, tool
from strands.models import BedrockModel
from pydantic import BaseModel, Field
from typing import List

# 定义Sub-Agent的输出结构
class DocumentAnalysisResult(BaseModel):
    """文档分析结果"""
    answer: str = Field(description="针对用户问题的回答")
    citations: List[dict] = Field(description="引用的具体段落或图片")

# 定义Sub-Agent使用的工具
@tool
def get_document_content(document_id: str) -> dict:
    """
    获取文档内容（Markdown+图片）

    Args:
        document_id: 文档ID

    Returns:
        包含markdown内容和图片路径列表的字典
    """
    # 1. 优先从本地缓存获取
    markdown_path = get_cached_document(document_id)
    if not markdown_path:
        markdown_path = download_from_s3(document_id)

    # 2. 读取文档内容
    markdown_content = read_file(markdown_path)

    # 3. 获取图片路径
    images_dir = get_document_images_dir(document_id)
    image_paths = list_files(images_dir)

    return {
        "markdown_content": markdown_content,
        "image_paths": image_paths
    }

@tool
def read_image_file(image_path: str) -> bytes:
    """
    读取图片文件

    Args:
        image_path: 图片文件路径

    Returns:
        图片二进制数据
    """
    with open(image_path, 'rb') as f:
        return f.read()

# 创建Sub-Agent
class DocumentSubAgent:
    def __init__(self):
        # 使用BedrockModel配置Sub-Agent
        self.model = BedrockModel(
            model_id="global.anthropic.claude-sonnet-4-5-20250929-v1:0",
            region_name="us-west-2",
            temperature=0.3,
            streaming=True,
        )

        # 创建Strands Agent，配置工具和系统提示词
        self.agent = Agent(
            model=self.model,
            tools=[get_document_content, read_image_file],
            system_prompt="""你是一个专业的产品文档分析助手。

            你的任务是：
            1. 使用get_document_content工具获取文档内容
            2. 仔细阅读文档的Markdown文本
            3. 如果需要，使用read_image_file工具查看图片
            4. 针对用户问题提取相关信息
            5. 标记引用的具体位置（chunk_id）

            注意：
            - 确保引用准确，每个引用必须对应实际存在的chunk
            - 如果文档中没有相关信息，明确说明
            - 优先引用原文，而不是自己编造
            """
        )

    def process(self, document_id: str, query: str, relevant_chunks: List[dict]) -> dict:
        """
        处理单个文档

        Args:
            document_id: 文档ID
            query: 用户问题
            relevant_chunks: 检索到的相关chunk列表

        Returns:
            分析结果（包含答案和引用）
        """
        # 构建查询prompt，包含上下文信息
        prompt = f"""
        用户问题：{query}

        文档ID：{document_id}

        重点关注的片段：
        {self._format_relevant_chunks(relevant_chunks)}

        请使用get_document_content工具获取完整文档，然后回答用户问题。
        """

        # 使用structured_output确保输出格式
        result = self.agent.structured_output(
            DocumentAnalysisResult,
            prompt
        )

        return {
            "answer": result.answer,
            "citations": result.citations
        }

    def _format_relevant_chunks(self, chunks: List[dict]) -> str:
        """格式化相关chunk信息"""
        formatted = []
        for chunk in chunks:
            if chunk['chunk_type'] == 'text':
                formatted.append(f"[Chunk {chunk['chunk_id']}] {chunk['content'][:200]}...")
            else:
                formatted.append(f"[Image Chunk {chunk['chunk_id']}] {chunk['image_description']}")
        return "\n\n".join(formatted)
```

#### 2.2.2 Main Agent综合逻辑（使用Strands Agent框架）

```python
from strands import Agent
from strands.models import BedrockModel
from typing import List, AsyncGenerator
import asyncio

class MainAgent:
    def __init__(self):
        # 使用BedrockModel配置Main Agent，启用流式输出
        self.model = BedrockModel(
            model_id="global.anthropic.claude-sonnet-4-5-20250929-v1:0",
            region_name="us-west-2",
            temperature=0.7,
            streaming=True,
            max_tokens=4096,
        )

        # 创建Main Agent
        self.agent = Agent(
            model=self.model,
            system_prompt="""你是一个产品知识问答助手。

            你的任务是综合多个文档分析结果，生成完整、准确的回答。

            要求：
            1. 综合所有sub-agent的分析结果
            2. 如果不同文档描述了演进历史，按时间顺序组织
            3. 使用Markdown格式
            4. 在相关段落后标注引用 [^1][^2]
            5. 在回答末尾列出所有引用的详细信息
            6. 如果信息不足，明确说明
            """
        )

    async def synthesize_streaming(
        self,
        query: str,
        sub_agent_results: List[dict]
    ) -> AsyncGenerator[str, None]:
        """
        综合多个sub-agent结果，流式生成答案

        Args:
            query: 用户问题
            sub_agent_results: 所有sub-agent的分析结果

        Yields:
            答案文本片段
        """
        # 构建综合prompt
        prompt = f"""
        用户问题：{query}

        各文档的分析结果：
        {self._format_sub_results(sub_agent_results)}

        请综合以上信息，生成完整答案。
        """

        # 使用Strands Agent的流式API
        async for event in self.agent.stream_async(prompt):
            # 处理不同类型的事件
            if event.type == "text_delta":
                # 文本增量事件
                yield event.data
            elif event.type == "tool_use":
                # 如果agent需要使用工具（未来扩展）
                pass
            elif event.type == "complete":
                # 完成事件，可以获取完整的metrics
                self._save_metrics(event.metrics)

    def synthesize(self, query: str, sub_agent_results: List[dict]) -> dict:
        """
        同步版本的综合方法（非流式）

        Args:
            query: 用户问题
            sub_agent_results: 所有sub-agent的分析结果

        Returns:
            完整答案和引用信息
        """
        prompt = f"""
        用户问题：{query}

        各文档的分析结果：
        {self._format_sub_results(sub_agent_results)}

        请综合以上信息，生成完整答案。
        """

        # 使用Strands Agent调用（非流式）
        result = self.agent(prompt)

        # 提取引用信息
        citations = self._extract_citations(sub_agent_results)

        return {
            "answer": result.text,
            "citations": citations,
            "metrics": {
                "total_tokens": result.metrics.accumulated_usage.get("totalTokens", 0),
                "prompt_tokens": result.metrics.accumulated_usage.get("inputTokens", 0),
                "completion_tokens": result.metrics.accumulated_usage.get("outputTokens", 0),
            }
        }

    def _format_sub_results(self, results: List[dict]) -> str:
        """格式化sub-agent结果"""
        formatted = []
        for i, result in enumerate(results, 1):
            formatted.append(f"""
            === 文档 {i} ===
            回答：{result['answer']}

            引用：
            {self._format_citations(result['citations'])}
            """)
        return "\n\n".join(formatted)

    def _format_citations(self, citations: List[dict]) -> str:
        """格式化引用信息"""
        return "\n".join([
            f"- [{c['chunk_id']}] {c.get('reason', '')}"
            for c in citations
        ])

    def _extract_citations(self, results: List[dict]) -> List[dict]:
        """从所有sub-agent结果中提取并合并引用"""
        all_citations = []
        for result in results:
            all_citations.extend(result.get('citations', []))
        # 去重
        unique_citations = {c['chunk_id']: c for c in all_citations}
        return list(unique_citations.values())

    def _save_metrics(self, metrics):
        """保存metrics到数据库（用于成本跟踪）"""
        # TODO: 实现metrics存储
        pass
```

#### 2.2.3 Multi-Agent Orchestration实现（使用Strands框架）

```python
from strands import Agent
from strands.models import BedrockModel
from typing import List, Dict
import asyncio
from concurrent.futures import ThreadPoolExecutor

class MultiAgentOrchestrator:
    """
    Multi-Agent协调器
    负责协调Sub-Agent和Main-Agent的执行
    """

    def __init__(self, max_concurrent_agents: int = 5):
        self.max_concurrent_agents = max_concurrent_agents
        self.main_agent = MainAgent()

    async def process_query(
        self,
        query: str,
        documents_with_chunks: Dict[str, List[dict]]
    ) -> dict:
        """
        处理用户查询的完整流程

        Args:
            query: 用户问题
            documents_with_chunks: {document_id: [chunks]} 文档和相关chunk的映射

        Returns:
            包含答案、引用和metrics的结果
        """
        # 1. 并发执行所有Sub-Agent
        sub_agent_results = await self._execute_sub_agents(
            query,
            documents_with_chunks
        )

        # 2. Main Agent综合生成答案（流式）
        final_result = await self._synthesize_with_main_agent(
            query,
            sub_agent_results
        )

        return final_result

    async def _execute_sub_agents(
        self,
        query: str,
        documents_with_chunks: Dict[str, List[dict]]
    ) -> List[dict]:
        """
        并发执行所有Sub-Agent

        Args:
            query: 用户问题
            documents_with_chunks: 文档和chunk的映射

        Returns:
            所有Sub-Agent的结果列表
        """
        tasks = []

        for document_id, chunks in documents_with_chunks.items():
            # 为每个文档创建一个Sub-Agent任务
            task = self._execute_single_sub_agent(
                document_id,
                query,
                chunks
            )
            tasks.append(task)

        # 使用asyncio.Semaphore限制并发数
        semaphore = asyncio.Semaphore(self.max_concurrent_agents)

        async def limited_task(task):
            async with semaphore:
                return await task

        # 并发执行，但限制并发数
        results = await asyncio.gather(
            *[limited_task(task) for task in tasks],
            return_exceptions=True
        )

        # 过滤掉失败的结果
        successful_results = [
            r for r in results
            if not isinstance(r, Exception)
        ]

        return successful_results

    async def _execute_single_sub_agent(
        self,
        document_id: str,
        query: str,
        chunks: List[dict]
    ) -> dict:
        """
        执行单个Sub-Agent

        Args:
            document_id: 文档ID
            query: 用户问题
            chunks: 相关chunk列表

        Returns:
            Sub-Agent的分析结果
        """
        # 创建Sub-Agent实例
        sub_agent = DocumentSubAgent()

        # 在线程池中执行（因为Sub-Agent可能有同步操作）
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(
                executor,
                sub_agent.process,
                document_id,
                query,
                chunks
            )

        return {
            "document_id": document_id,
            "result": result
        }

    async def _synthesize_with_main_agent(
        self,
        query: str,
        sub_agent_results: List[dict]
    ) -> dict:
        """
        使用Main Agent综合所有Sub-Agent的结果

        Args:
            query: 用户问题
            sub_agent_results: 所有Sub-Agent的结果

        Returns:
            最终答案和引用
        """
        # 提取所有sub-agent的结果
        results = [r['result'] for r in sub_agent_results]

        # 调用Main Agent综合
        final_result = self.main_agent.synthesize(query, results)

        return final_result

    async def process_query_streaming(
        self,
        query: str,
        documents_with_chunks: Dict[str, List[dict]]
    ):
        """
        流式处理用户查询

        Args:
            query: 用户问题
            documents_with_chunks: 文档和chunk的映射

        Yields:
            流式事件（文本片段、状态更新等）
        """
        # 1. 发送状态：开始处理sub-agents
        yield {
            "type": "status",
            "message": f"正在分析 {len(documents_with_chunks)} 个文档..."
        }

        # 2. 并发执行Sub-Agents
        sub_agent_results = await self._execute_sub_agents(
            query,
            documents_with_chunks
        )

        # 3. 发送状态：开始综合答案
        yield {
            "type": "status",
            "message": "正在生成答案..."
        }

        # 4. 流式生成最终答案
        results = [r['result'] for r in sub_agent_results]
        async for text_chunk in self.main_agent.synthesize_streaming(query, results):
            yield {
                "type": "text_delta",
                "text": text_chunk
            }

        # 5. 发送完成事件（包含引用和metrics）
        citations = self.main_agent._extract_citations(results)
        yield {
            "type": "complete",
            "citations": citations
        }
```

**使用示例**：

```python
# 在FastAPI中使用Multi-Agent Orchestrator
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()
orchestrator = MultiAgentOrchestrator(max_concurrent_agents=5)

@app.post("/api/v1/query")
async def query_streaming(request: QueryRequest):
    """
    流式问答API
    """
    # 1. Query Rewrite
    rewritten_queries = await query_rewriter.rewrite(request.query)

    # 2. Hybrid Search
    search_results = hybrid_search(
        index_name=f"kb_{request.kb_id}_index",
        queries=rewritten_queries
    )

    # 3. 按文档聚合chunks
    documents_with_chunks = group_chunks_by_document(search_results)

    # 4. Multi-Agent处理
    async def event_generator():
        async for event in orchestrator.process_query_streaming(
            request.query,
            documents_with_chunks
        ):
            # 转换为SSE格式
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
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
PDF (S3原始文件)
  │ s3://bucket/prds/product-a/doc.pdf
  │
  ├─→ 原始文件 (永久保留在S3)
  │
  └─→ Marker转换
       │
       ├─→ Markdown文件
       │    ├─→ S3持久化存储: s3://bucket/prds/product-a/converted/doc-xxx/content.md
       │    └─→ 本地缓存: /data/cache/documents/doc-xxx/content.md
       │
       └─→ 图片文件
            ├─→ S3持久化存储: s3://bucket/prds/product-a/converted/doc-xxx/images/*.png
            ├─→ 本地缓存: /data/cache/documents/doc-xxx/images/*.png
            │
            ├─→ 图片Chunk (SQLite元数据 + OpenSearch向量 + S3图片文件)
            │    - chunk.image_s3_key: S3路径 (必须)
            │    - chunk.image_local_path: 本地缓存路径 (可选)
            │
            └─→ 文本Chunk (SQLite元数据 + OpenSearch向量)
```

**数据持久化策略**：
- **S3**: 所有转换后的文件（Markdown + 图片）永久存储，作为唯一真实数据源
- **本地缓存**: 加速访问，可以清理，丢失后可从S3恢复
- **获取逻辑**: 先检查本地缓存 → 不存在则从S3下载 → 下载后更新本地缓存

**S3路径规划**：
```
s3://your-bucket/
├── prds/product-a/                    # S3 prefix (知识库配置)
│   ├── doc1.pdf                       # 原始PDF
│   ├── doc2.pdf
│   └── converted/                     # 转换后的文件目录
│       ├── doc-660e8400/              # 按document_id组织
│       │   ├── content.md             # Markdown文件
│       │   └── images/                # 图片目录
│       │       ├── img_001.png
│       │       ├── img_002.png
│       │       └── img_003.png
│       └── doc-770e8400/
│           ├── content.md
│           └── images/
│               └── img_001.png
```

**文件获取逻辑伪代码**：
```python
def get_document_content(document_id: str) -> str:
    """获取文档Markdown内容（优先本地缓存）"""
    # 1. 检查本地缓存
    local_path = f"/data/cache/documents/{document_id}/content.md"
    if os.path.exists(local_path):
        return read_file(local_path)

    # 2. 从S3下载
    doc = db.get_document(document_id)
    s3_key = doc.s3_key_markdown  # 例如: prds/product-a/converted/doc-xxx/content.md
    content = s3_client.download_file(s3_key)

    # 3. 更新本地缓存
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    write_file(local_path, content)

    # 4. 更新数据库记录
    db.update_document(document_id, local_markdown_path=local_path)

    return content

def get_image_file(chunk_id: str) -> bytes:
    """获取图片文件（优先本地缓存）"""
    chunk = db.get_chunk(chunk_id)

    # 1. 检查本地缓存
    if chunk.image_local_path and os.path.exists(chunk.image_local_path):
        return read_binary_file(chunk.image_local_path)

    # 2. 从S3下载
    image_data = s3_client.download_file(chunk.image_s3_key)

    # 3. 更新本地缓存
    local_path = f"/data/cache/documents/{chunk.document_id}/images/{chunk.image_filename}"
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    write_binary_file(local_path, image_data)

    # 4. 更新数据库记录
    db.update_chunk(chunk_id, image_local_path=local_path)

    return image_data
```
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

### 4.1.1 为什么转换结果要上传S3？

**核心原因**：
1. **数据持久化**：本地缓存可能被清理或丢失，S3是唯一可靠数据源
2. **避免重复转换**：Marker转换耗时（需要GPU），转换一次永久保存
3. **多实例支持**：将来多实例部署时，所有实例共享S3的转换结果
4. **灾难恢复**：服务器故障时，可从S3完全恢复

**成本考虑**：
- S3存储成本很低（约$0.023/GB/月）
- 相比重复运行Marker（GPU成本），S3存储更经济
- 一次转换，永久受益

**实现策略**：
- Marker转换完成后**立即上传S3**
- 同时缓存到本地（加速访问）
- 本地缓存采用LRU策略，可以安全清理
- 访问时优先本地缓存，缺失则从S3下载

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

## 八、前端交互设计

### 8.1 文档管理页面工作流程

#### 8.1.1 上传和同步流程

**设计原则**：上传和同步是两个独立的手动操作，用户完全控制处理时机。

```
用户操作流程：

1. 选择知识库
   ↓
2. 点击"上传文档"按钮
   ↓
3. 选择PDF文件并上传
   ↓
4. 前端调用 POST /knowledge-bases/{kb_id}/documents/upload
   ↓
5. 文档上传到S3，状态为"uploaded"
   ↓
6. 文档列表显示新文档（状态：已上传）

   --- 用户需要手动触发下一步 ---

7. 用户点击"同步数据"按钮
   ↓
8. 显示同步确认Modal（说明处理流程）
   ↓
9. 用户确认，前端调用 POST /knowledge-bases/{kb_id}/sync
   ↓
10. 同步任务创建成功
   ↓
11. "同步任务"区域显示任务进度
   ↓
12. 用户点击"刷新"按钮查看进度更新
   ↓
13. 任务完成后，文档状态变为"completed"
```

#### 8.1.2 进度查询机制

**设计原则**：不使用自动轮询，避免不必要的API请求。

```
手动刷新机制：

1. 同步任务区域显示任务列表
2. 用户点击"刷新"按钮
   ↓
3. 调用 GET /knowledge-bases/{kb_id}/sync-tasks
   ↓
4. 更新任务状态和进度
5. 如果任务running，显示进度条
6. 如果任务completed/failed，显示最终状态
```

**为什么不自动轮询**：
- 减少服务器负载
- 避免无效API请求
- 用户按需查询，更灵活
- 长时间运行的任务不会造成大量请求

#### 8.1.3 页面状态管理

```typescript
// 关键状态
const [documents, setDocuments] = useState<Document[]>([]);
const [syncTasks, setSyncTasks] = useState<SyncTask[]>([]);
const [uploadModalVisible, setUploadModalVisible] = useState(false);
const [syncModalVisible, setSyncModalVisible] = useState(false);

// 不使用定时器
// ❌ 错误做法：
// useEffect(() => {
//   const interval = setInterval(loadSyncTasks, 3000);
//   return () => clearInterval(interval);
// }, [kbId]);

// ✅ 正确做法：只在用户触发时刷新
const handleRefresh = () => {
  loadSyncTasks();
  loadDocuments();
};
```

### 8.2 按钮和操作说明

| 按钮 | 位置 | 功能 | API调用 |
|------|------|------|---------|
| 上传文档 | 页面右上角 | 打开上传Modal | - |
| 上传（Modal内） | 上传Modal | 上传文件到S3 | POST /documents/upload |
| 同步数据 | 同步任务区域 | 打开同步确认Modal | - |
| 开始同步（Modal内） | 同步Modal | 创建同步任务 | POST /sync |
| 刷新（同步任务区域） | 同步任务区域 | 刷新任务状态 | GET /sync-tasks |
| 刷新（文档列表） | 文档列表 | 刷新文档列表 | GET /documents |
| 删除 | 文档列表 | 删除选中文档 | DELETE /documents |

### 8.3 用户提示信息

```typescript
// 上传Modal提示
"上传后文档将保存到S3，需要点击'同步数据'按钮触发转换和向量化处理。"

// 同步Modal说明
"将对知识库中状态为'已上传'的文档执行以下操作：
- 使用Marker将PDF转换为Markdown和图片
- 使用Claude Vision API理解图片内容
- 将文本和图片分块并向量化
- 上传转换结果到S3并存储向量到OpenSearch"

// 同步任务区域空状态
"暂无同步任务，点击'同步数据'按钮开始处理文档"
```

---

## 九、安全设计

### 9.1 AWS服务访问

- 使用IAM Role而非硬编码AccessKey
- 最小权限原则
- S3 Bucket启用版本控制

### 9.2 输入验证

- 文件类型检查（仅允许PDF）
- 文件大小限制（最大100MB）
- 路径穿越防护
- SQL注入防护（使用ORM参数化查询）

### 9.3 数据安全

- S3加密（SSE-S3或SSE-KMS）
- OpenSearch启用加密
- SQLite文件权限控制

---

## 十、未来优化方向

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
