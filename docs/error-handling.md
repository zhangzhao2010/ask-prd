# ASK-PRD 错误处理文档

> 版本：v1.0
> 更新时间：2025-01-20

---

## 一、错误分类

### 1.1 错误级别

| 级别 | 说明 | 处理策略 |
|------|------|---------|
| Critical | 系统级错误，需要立即人工介入 | 中断操作，记录日志，告警 |
| Error | 业务错误，影响当前操作 | 终止当前操作，返回错误信息 |
| Warning | 部分失败，不影响主流程 | 记录日志，继续执行，标记警告 |
| Retryable | 可重试错误 | 自动重试（指数退避），超过次数后失败 |

---

## 二、错误码体系

### 2.1 通用错误 (1xxx)

| 错误码 | 错误名称 | HTTP状态码 | 说明 |
|--------|---------|-----------|------|
| 1000 | INTERNAL_SERVER_ERROR | 500 | 内部服务器错误 |
| 1001 | DATABASE_ERROR | 500 | 数据库操作失败 |
| 1002 | INVALID_REQUEST | 400 | 请求参数无效 |
| 1003 | RESOURCE_NOT_FOUND | 404 | 资源不存在 |

### 2.2 知识库错误 (2xxx)

| 错误码 | 错误名称 | HTTP状态码 | 说明 |
|--------|---------|-----------|------|
| 2001 | KB_NOT_FOUND | 404 | 知识库不存在 |
| 2002 | KB_ALREADY_EXISTS | 400 | 知识库名称已存在 |
| 2003 | KB_CREATE_FAILED | 500 | 知识库创建失败 |
| 2004 | KB_DELETE_FAILED | 500 | 知识库删除失败 |
| 2010 | OPENSEARCH_CONNECTION_FAILED | 500 | OpenSearch连接失败 |
| 2011 | OPENSEARCH_INDEX_CREATE_FAILED | 500 | OpenSearch索引创建失败 |
| 2012 | OPENSEARCH_SEARCH_FAILED | 500 | OpenSearch检索失败 |

### 2.3 文档错误 (3xxx)

| 错误码 | 错误名称 | HTTP状态码 | 说明 |
|--------|---------|-----------|------|
| 3001 | DOCUMENT_NOT_FOUND | 404 | 文档不存在 |
| 3002 | DOCUMENT_UPLOAD_FAILED | 500 | 文档上传失败 |
| 3003 | DOCUMENT_TOO_LARGE | 400 | 文档大小超过限制（>100MB） |
| 3004 | DOCUMENT_INVALID_FORMAT | 400 | 文档格式无效（非PDF） |
| 3010 | PDF_PARSE_FAILED | 500 | PDF解析失败（Marker转换错误） |
| 3011 | MARKDOWN_GENERATE_FAILED | 500 | Markdown生成失败 |
| 3012 | IMAGE_EXTRACT_FAILED | 500 | 图片提取失败 |

### 2.4 S3错误 (4xxx)

| 错误码 | 错误名称 | HTTP状态码 | 说明 |
|--------|---------|-----------|------|
| 4001 | S3_CONNECTION_FAILED | 500 | S3连接失败 |
| 4002 | S3_UPLOAD_FAILED | 500 | S3上传失败 |
| 4003 | S3_DOWNLOAD_FAILED | 500 | S3下载失败 |
| 4004 | S3_BUCKET_NOT_FOUND | 404 | S3桶不存在 |
| 4005 | S3_PERMISSION_DENIED | 403 | S3权限不足 |

### 2.5 向量化错误 (5xxx)

| 错误码 | 错误名称 | HTTP状态码 | 说明 |
|--------|---------|-----------|------|
| 5001 | EMBEDDING_FAILED | 500 | 向量化失败 |
| 5002 | CHUNK_SPLIT_FAILED | 500 | 文本分块失败 |
| 5003 | VECTOR_STORE_FAILED | 500 | 向量存储失败 |

### 2.6 Bedrock错误 (6xxx)

| 错误码 | 错误名称 | HTTP状态码 | 说明 |
|--------|---------|-----------|------|
| 6001 | BEDROCK_CONNECTION_FAILED | 500 | Bedrock连接失败 |
| 6002 | BEDROCK_RATE_LIMIT | 503 | Bedrock限流（超过调用频率） |
| 6003 | BEDROCK_TIMEOUT | 504 | Bedrock超时 |
| 6004 | BEDROCK_MODEL_ERROR | 500 | Bedrock模型错误 |
| 6005 | BEDROCK_THROTTLING | 503 | Bedrock节流 |
| 6006 | BEDROCK_TOKEN_LIMIT_EXCEEDED | 400 | Token数量超限 |

### 2.7 同步任务错误 (7xxx)

| 错误码 | 错误名称 | HTTP状态码 | 说明 |
|--------|---------|-----------|------|
| 7001 | SYNC_TASK_NOT_FOUND | 404 | 同步任务不存在 |
| 7002 | SYNC_TASK_ALREADY_RUNNING | 400 | 同步任务已在运行 |
| 7003 | SYNC_TASK_FAILED | 500 | 同步任务失败 |

### 2.8 查询错误 (8xxx)

| 错误码 | 错误名称 | HTTP状态码 | 说明 |
|--------|---------|-----------|------|
| 8001 | QUERY_FAILED | 500 | 查询失败 |
| 8002 | RETRIEVAL_FAILED | 500 | 检索失败 |
| 8003 | AGENT_EXECUTION_FAILED | 500 | Agent执行失败 |
| 8004 | NO_DOCUMENTS_FOUND | 404 | 未找到相关文档 |
| 8005 | QUERY_REWRITE_FAILED | 500 | 查询重写失败 |
| 8006 | ANSWER_GENERATION_FAILED | 500 | 答案生成失败 |

---

## 三、各环节错误处理策略

### 3.1 PDF转换（Marker）失败

**可能原因**：
- PDF文件损坏或加密
- Marker进程崩溃
- 磁盘空间不足
- GPU内存不足

**处理策略**：
```python
try:
    markdown, images = marker.convert_pdf(pdf_path)
except MarkerProcessError as e:
    logger.error(f"Marker conversion failed", extra={
        "document_id": doc_id,
        "error": str(e)
    })
    # 更新文档状态为failed
    update_document_status(doc_id, status='failed',
                          error_message=f"PDF转换失败: {str(e)}")
    # 同步任务继续处理其他文档
    continue

except DiskSpaceError:
    logger.critical("Disk space insufficient")
    # Critical错误，中断整个任务
    update_sync_task(task_id, status='failed',
                    error_message='磁盘空间不足')
    raise
```

**用户提示**：
- "文档转换失败，可能是PDF损坏或格式不支持，请检查文件后重试"
- 提供"重试"按钮

---

### 3.2 图片描述生成（Bedrock）失败

**可能原因**：
- Bedrock限流/节流
- 网络超时
- 图片格式不支持
- Token超限

**处理策略**：
```python
def generate_image_description(image_path, context, max_retries=3):
    """生成图片描述，带重试和降级"""
    for attempt in range(max_retries):
        try:
            description = bedrock_claude_vision(image_path, context)
            return description

        except BedrockRateLimitError:
            # 限流：指数退避
            wait_time = 2 ** attempt
            logger.warning(f"Bedrock rate limit, retry in {wait_time}s")
            time.sleep(wait_time)

        except BedrockTimeoutError:
            # 超时：重试
            if attempt < max_retries - 1:
                logger.warning(f"Bedrock timeout, retry {attempt + 1}")
                continue
            else:
                # 降级：使用默认描述
                logger.error(f"Bedrock timeout after {max_retries} retries")
                return f"[图片描述生成失败: {os.path.basename(image_path)}]"

        except BedrockModelError as e:
            # 模型错误：不重试，使用降级
            logger.error(f"Bedrock model error: {e}")
            return f"[图片: {os.path.basename(image_path)}]"

    # 所有重试失败，返回降级描述
    return f"[图片描述生成失败: {os.path.basename(image_path)}]"
```

**降级策略**：
- 图片描述失败不阻断文档处理
- 使用占位文本替代
- 记录Warning日志

**用户提示**：
- "部分图片处理失败，但不影响文档使用"

---

### 3.3 向量化（Embedding）失败

**可能原因**：
- Bedrock限流
- 文本过长
- 网络问题

**处理策略**：
```python
def embed_chunks(chunks, max_retries=3):
    """向量化chunks，带重试和降级"""
    failed_chunks = []

    for chunk in chunks:
        for attempt in range(max_retries):
            try:
                # 批量embedding（提高效率）
                embedding = bedrock_embedding(chunk.content_with_context)
                chunk.embedding = embedding
                break

            except BedrockRateLimitError:
                # 限流：等待后重试
                time.sleep(2 ** attempt)

            except BedrockTokenLimitError:
                # Token超限：截断文本
                logger.warning(f"Chunk too long, truncating: {chunk.id}")
                chunk.content_with_context = truncate_text(
                    chunk.content_with_context,
                    max_tokens=8000
                )
                # 继续重试

            except Exception as e:
                if attempt == max_retries - 1:
                    # 最终失败：记录但不阻断
                    logger.error(f"Embedding failed: {chunk.id}, error: {e}")
                    failed_chunks.append(chunk.id)
                    break

    # 记录失败的chunk数量
    if failed_chunks:
        logger.warning(f"{len(failed_chunks)} chunks failed to embed")

    return failed_chunks
```

**处理原则**：
- 向量化失败的chunk不存入OpenSearch
- 在数据库中标记这些chunk
- 同步任务标记为`partial_success`
- 提供"重试失败chunk"功能

**用户提示**：
- "部分内容向量化失败（3/50），可重试失败内容"

---

### 3.4 OpenSearch操作失败

**可能原因**：
- 连接断开
- Index不存在
- 容量限制

**处理策略**：
```python
def store_to_opensearch(chunks, index_name, max_retries=3):
    """存储到OpenSearch，带重试"""
    # 连接检查
    if not opensearch_client.ping():
        logger.critical("OpenSearch connection failed")
        raise OpenSearchConnectionError("无法连接到OpenSearch")

    # 批量插入（提高效率）
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]

        for attempt in range(max_retries):
            try:
                # bulk insert
                response = opensearch_client.bulk(
                    index=index_name,
                    body=prepare_bulk_body(batch)
                )

                # 检查是否有部分失败
                if response['errors']:
                    failed_ids = extract_failed_ids(response)
                    logger.error(f"Bulk insert partial failure: {failed_ids}")

                break

            except ConnectionError:
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    # Critical错误，中断任务
                    raise OpenSearchConnectionError("OpenSearch连接失败")

            except RequestError as e:
                # 请求错误（如mapping不匹配），不重试
                logger.error(f"OpenSearch request error: {e}")
                raise
```

**处理原则**：
- 连接失败：中断同步任务，标记为failed
- 部分失败：记录失败ID，任务标记为partial_success

**用户提示**：
- "向量存储失败，请检查OpenSearch服务状态后重试"

---

### 3.5 检索问答流程错误处理

#### 3.5.1 检索失败

```python
def retrieve_documents(kb_id, query):
    """检索文档"""
    try:
        # Query Rewrite
        rewritten_queries = rewrite_query(query)

        # Hybrid Search
        results = hybrid_search(kb_id, rewritten_queries)

        if not results:
            # 没有检索到结果
            return {
                "error_code": "8004",
                "message": "未找到相关文档，请尝试换个问法或检查知识库内容"
            }

        return results

    except OpenSearchSearchError as e:
        logger.error(f"Search failed: {e}")
        return {
            "error_code": "8002",
            "message": "检索失败，请稍后重试"
        }
```

**用户提示**：
- "未找到相关文档，试试换个问法？"
- "检索服务暂时不可用，请稍后重试"

#### 3.5.2 Sub-Agent失败

```python
def process_with_sub_agents(documents, query):
    """使用多个sub-agent处理文档"""
    results = []
    failed_docs = []

    # 并发执行sub-agent
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(sub_agent_process, doc, query): doc
            for doc in documents
        }

        for future in as_completed(futures):
            doc = futures[future]
            try:
                result = future.result(timeout=60)  # 60秒超时
                results.append(result)

            except TimeoutError:
                logger.error(f"Sub-agent timeout: {doc.id}")
                failed_docs.append(doc.id)

            except BedrockError as e:
                logger.error(f"Sub-agent Bedrock error: {doc.id}, {e}")
                failed_docs.append(doc.id)

            except Exception as e:
                logger.error(f"Sub-agent unexpected error: {doc.id}, {e}")
                failed_docs.append(doc.id)

    # 至少要有一个成功的结果
    if not results:
        raise AgentExecutionError("所有文档处理都失败了")

    # 记录部分失败
    if failed_docs:
        logger.warning(f"Sub-agents partial failure: {failed_docs}")

    return results
```

**用户提示**：
- "已基于部分文档生成答案（3/5个文档可用）"

#### 3.5.3 Main Agent失败

```python
def generate_final_answer(sub_agent_results, query):
    """生成最终答案"""
    max_retries = 2

    for attempt in range(max_retries):
        try:
            answer = bedrock_claude_generate(sub_agent_results, query)
            return answer

        except BedrockRateLimitError:
            time.sleep(2 ** attempt)

        except BedrockTimeoutError:
            if attempt == max_retries - 1:
                # 降级：返回简化答案
                return generate_fallback_answer(sub_agent_results)

        except BedrockModelError as e:
            logger.error(f"Main agent model error: {e}")
            raise AgentExecutionError("答案生成失败，请稍后重试")

    raise AgentExecutionError("答案生成失败，请稍后重试")

def generate_fallback_answer(sub_agent_results):
    """降级方案：直接拼接sub-agent的结果"""
    return "\n\n".join([r['answer'] for r in sub_agent_results])
```

---

### 3.6 文件缓存失败

**处理策略**：
```python
def get_document_local_path(doc_id):
    """获取文档本地路径，不存在则从S3下载"""
    doc = db.get_document(doc_id)

    # 检查本地缓存
    if doc.local_markdown_path and os.path.exists(doc.local_markdown_path):
        return doc.local_markdown_path

    # 从S3下载
    try:
        local_path = download_from_s3(doc.s3_key_markdown)

        # 更新数据库
        db.update_document(doc_id, local_markdown_path=local_path)

        return local_path

    except S3DownloadError as e:
        logger.error(f"S3 download failed: {doc.s3_key_markdown}, {e}")

        # 如果S3下载失败，尝试重新生成
        if os.path.exists(doc.s3_key):  # 假设也缓存了PDF
            logger.info(f"Regenerating markdown for {doc_id}")
            return regenerate_markdown(doc)

        raise DocumentNotAvailableError("文档暂时不可用，请稍后重试")
```

---

## 四、统一错误响应格式

### 4.1 FastAPI全局异常处理

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    error_code = getattr(exc, 'error_code', '1000')
    message = str(exc) or "Internal server error"
    status_code = getattr(exc, 'status_code', 500)

    # 记录日志
    logger.error(
        f"Request failed: {request.url}",
        extra={
            "error_code": error_code,
            "message": message,
            "request_id": request.state.request_id
        },
        exc_info=True
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": error_code,
                "message": message,
                "details": getattr(exc, 'details', {}),
                "request_id": request.state.request_id
            }
        }
    )
```

### 4.2 自定义异常类

```python
class ASKPRDException(Exception):
    """基础异常类"""
    def __init__(self, message, error_code, status_code=500, details=None):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

class DocumentNotFoundException(ASKPRDException):
    """文档不存在异常"""
    def __init__(self, doc_id):
        super().__init__(
            message="文档不存在",
            error_code="3001",
            status_code=404,
            details={"document_id": doc_id}
        )

class BedrockRateLimitError(ASKPRDException):
    """Bedrock限流异常"""
    def __init__(self):
        super().__init__(
            message="服务繁忙，请稍后重试",
            error_code="6002",
            status_code=503
        )
```

---

## 五、用户提示文案

| 错误场景 | 用户提示 | 是否可重试 | 操作建议 |
|---------|---------|-----------|---------|
| PDF转换失败 | 文档转换失败，可能是PDF损坏或格式不支持 | ✅ | 检查文件后重新上传 |
| 图片描述失败 | 部分图片处理失败，但不影响文档使用 | ⚠️ 降级 | 无需操作 |
| 向量化失败 | 部分内容索引失败，可以重试 | ✅ | 点击"重试"按钮 |
| OpenSearch连接失败 | 搜索服务暂时不可用，请稍后重试 | ✅ | 稍后再试 |
| Bedrock限流 | 服务繁忙，请稍后重试 | ✅ 自动重试 | 稍后再试 |
| 检索无结果 | 未找到相关文档，试试换个问法？ | ❌ | 换个问法 |
| Sub-agent全部失败 | 文档处理失败，请稍后重试 | ✅ | 稍后再试 |
| Sub-agent部分失败 | 已基于部分文档生成答案（3/5个文档可用） | ⚠️ 降级 | 可接受结果或重试 |
| 文档过大 | 文档大小超过100MB限制 | ❌ | 压缩或分割文件 |
| 文档格式错误 | 仅支持PDF格式 | ❌ | 转换为PDF |

---

## 六、日志规范

### 6.1 结构化日志

```python
import structlog

logger = structlog.get_logger()

# 信息日志
logger.info(
    "sync_task_started",
    task_id=task_id,
    kb_id=kb_id,
    document_count=len(doc_ids)
)

# 错误日志
logger.error(
    "pdf_conversion_failed",
    task_id=task_id,
    document_id=doc_id,
    error_code="3010",
    error_message=str(e),
    exc_info=True
)

# 警告日志
logger.warning(
    "partial_embedding_failure",
    task_id=task_id,
    failed_chunk_count=len(failed_chunks),
    total_chunk_count=len(chunks)
)
```

### 6.2 日志级别使用

- **DEBUG**: 详细的调试信息
- **INFO**: 正常流程的关键步骤
- **WARNING**: 不影响主流程的异常
- **ERROR**: 影响当前操作的错误
- **CRITICAL**: 系统级错误，需要立即处理

---

## 七、监控和告警

### 7.1 关键指标

- **错误率**: 按错误码统计
- **重试次数**: Bedrock调用重试统计
- **降级次数**: 图片描述失败、答案降级等
- **响应时间**: P50, P95, P99
- **成功率**: 同步任务、查询请求

### 7.2 告警规则（未来）

- 错误率 > 5%：告警
- Bedrock连续失败 > 10次：告警
- OpenSearch不可用：Critical告警
- 磁盘空间 < 10%：告警

---

## 八、测试建议

### 8.1 单元测试

```python
def test_marker_failure_handling():
    """测试Marker转换失败处理"""
    with pytest.raises(MarkerProcessError):
        convert_pdf("corrupted.pdf")

    # 验证文档状态已更新为failed
    doc = db.get_document(doc_id)
    assert doc.status == "failed"
    assert "PDF转换失败" in doc.error_message
```

### 8.2 集成测试

```python
def test_sync_task_partial_failure():
    """测试同步任务部分失败"""
    # 上传3个文档，其中1个损坏
    doc_ids = upload_documents([
        "valid1.pdf",
        "corrupted.pdf",
        "valid2.pdf"
    ])

    # 创建同步任务
    task_id = create_sync_task(kb_id, doc_ids)

    # 等待任务完成
    wait_for_task_completion(task_id)

    # 验证任务状态为partial_success
    task = get_sync_task(task_id)
    assert task.status == "partial_success"
    assert task.processed_documents == 2
    assert task.failed_documents == 1
```

---

## 九、故障排查指南

### 9.1 常见问题

**问题1: PDF转换一直失败**
- 检查Marker服务是否正常运行
- 检查GPU内存是否充足
- 检查磁盘空间是否充足
- 尝试手动运行Marker测试

**问题2: Bedrock调用频繁限流**
- 检查调用频率是否过高
- 增加重试间隔
- 申请提升限额
- 考虑使用批量接口

**问题3: OpenSearch检索超时**
- 检查Index大小和分片配置
- 检查查询复杂度
- 优化向量维度
- 增加超时时间

**问题4: 本地缓存占用过多**
- 运行缓存清理接口
- 调整LRU策略
- 增加磁盘空间

---

## 十、核心原则

1. **不因局部失败影响全局**: 图片失败不阻断文档，文档失败不阻断任务
2. **可重试错误自动重试**: 网络、限流等临时性错误
3. **关键错误降级处理**: 提供备选方案，保证基本可用
4. **透明的错误提示**: 让用户知道发生了什么，是否可以重试
5. **详细的日志记录**: 便于问题排查和分析
