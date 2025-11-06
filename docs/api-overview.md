# ASK-PRD API 接口文档 - 总览

> 版本：v1.0
> 更新时间：2025-01-20

---

## 一、API基础信息

### 1.1 Base URL

```
开发环境: http://localhost:8000/api/v1
生产环境: http://<ec2-ip>:8000/api/v1
```

### 1.2 认证方式

Demo版本暂不需要认证，未来可扩展：
- API Key认证
- JWT Token认证
- AWS Signature V4

### 1.3 请求格式

- Content-Type: `application/json`
- 字符编码: UTF-8
- 时间格式: ISO 8601 (如 `2025-01-20T10:00:00Z`)

### 1.4 响应格式

**成功响应**：
```json
{
  "data": {
    // 响应数据
  }
}
```

**错误响应**：
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": {}
  }
}
```

### 1.5 HTTP状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 204 | 删除成功（无返回内容） |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
| 503 | 服务暂时不可用 |

---

## 二、API模块列表

### 2.1 知识库管理 (Knowledge Base)
详见：[api-knowledge-base.md](./api-knowledge-base.md)

- `GET /knowledge-bases` - 获取知识库列表
- `POST /knowledge-bases` - 创建知识库
- `GET /knowledge-bases/{kb_id}` - 获取知识库详情
- `DELETE /knowledge-bases/{kb_id}` - 删除知识库

### 2.2 文档管理 (Documents)
详见：[api-documents.md](./api-documents.md)

- `GET /knowledge-bases/{kb_id}/documents` - 获取文档列表
- `POST /knowledge-bases/{kb_id}/documents/upload` - 上传文档
- `DELETE /knowledge-bases/{kb_id}/documents` - 批量删除文档
- `GET /documents/{doc_id}` - 获取文档详情

### 2.3 同步任务 (Sync Tasks)
详见：[api-sync-tasks.md](./api-sync-tasks.md)

- `POST /knowledge-bases/{kb_id}/sync` - 创建同步任务
- `GET /knowledge-bases/{kb_id}/sync-tasks` - 获取任务列表
- `GET /sync-tasks/{task_id}` - 获取任务详情
- `POST /sync-tasks/{task_id}/cancel` - 取消任务

### 2.4 检索问答 (Query)
详见：[api-query.md](./api-query.md)

- `POST /knowledge-bases/{kb_id}/query/stream` - 流式问答（SSE）
- `GET /knowledge-bases/{kb_id}/query-history` - 查询历史列表
- `GET /query-history/{query_id}` - 查询详情

### 2.5 辅助接口 (Utilities)
详见：[api-utilities.md](./api-utilities.md)

- `GET /chunks/{chunk_id}/image` - 获取图片
- `GET /health` - 健康检查
- `GET /stats` - 系统统计信息

---

## 三、通用错误码

| 错误码 | 说明 | HTTP状态码 |
|--------|------|-----------|
| 1000 | 内部服务器错误 | 500 |
| 1001 | 数据库错误 | 500 |
| 1002 | 请求参数无效 | 400 |
| 2001 | 知识库不存在 | 404 |
| 2002 | 知识库名称已存在 | 400 |
| 3001 | 文档不存在 | 404 |
| 3002 | 文档上传失败 | 500 |
| 3003 | 文档过大 | 400 |
| 3004 | 文档格式无效 | 400 |
| 4001 | S3连接失败 | 500 |
| 4002 | S3上传失败 | 500 |
| 4003 | S3下载失败 | 500 |
| 6001 | Bedrock连接失败 | 500 |
| 6002 | Bedrock限流 | 503 |
| 6003 | Bedrock超时 | 504 |
| 7001 | 同步任务不存在 | 404 |
| 7002 | 同步任务已在运行 | 400 |
| 8001 | 查询失败 | 500 |
| 8002 | 检索失败 | 500 |
| 8004 | 未找到相关文档 | 404 |

完整错误码列表见：[error-handling.md](./error-handling.md)

---

## 四、分页规范

所有列表接口统一使用以下分页参数：

**请求参数**：
```
page: 页码，从1开始，默认1
page_size: 每页数量，默认20，最大100
```

**响应格式**：
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 150,
    "total_pages": 8
  }
}
```

---

## 五、流式输出规范（SSE）

问答接口使用Server-Sent Events实现流式输出。

### 5.1 连接建立

```javascript
const eventSource = new EventSource('/api/v1/knowledge-bases/{kb_id}/query/stream', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ query: "用户问题" })
});
```

### 5.2 事件类型

| 事件类型 | 说明 | 数据格式 |
|---------|------|---------|
| status | 处理状态更新 | `{"status": "searching", "message": "正在检索..."}` |
| retrieved_documents | 检索到的文档 | `{"document_ids": [...], "document_names": [...]}` |
| chunk | 答案文本片段 | `{"content": "答案片段"}` |
| citation | 引用信息 | `{"chunk_id": "...", "chunk_type": "text", ...}` |
| tokens | Token统计 | `{"prompt_tokens": 1000, "completion_tokens": 500}` |
| done | 生成完成 | `{"query_id": "..."}` |
| error | 错误 | `{"code": "8001", "message": "..."}` |

### 5.3 示例

```
event: status
data: {"status": "searching", "message": "正在检索文档..."}

event: retrieved_documents
data: {"document_ids": ["doc-1", "doc-2"], "document_names": ["PRD_v1.0.pdf", "PRD_v2.0.pdf"]}

event: chunk
data: {"content": "根据检索到的文档，"}

event: chunk
data: {"content": "登录模块经历了以下演进：\n\n"}

event: citation
data: {"chunk_id": "chunk-xxx", "chunk_type": "text", "document_name": "PRD_v1.0.pdf", "content": "...", "chunk_index": 5}

event: tokens
data: {"prompt_tokens": 15000, "completion_tokens": 800, "total_tokens": 15800}

event: done
data: {"query_id": "query-abc-123"}
```

---

## 六、测试示例

### 6.1 使用cURL

```bash
# 获取知识库列表
curl http://localhost:8000/api/v1/knowledge-bases

# 创建知识库
curl -X POST http://localhost:8000/api/v1/knowledge-bases \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试知识库",
    "description": "这是一个测试",
    "s3_bucket": "my-bucket",
    "s3_prefix": "test/"
  }'

# 上传文档
curl -X POST http://localhost:8000/api/v1/knowledge-bases/{kb_id}/documents/upload \
  -F "file=@/path/to/prd.pdf"
```

### 6.2 使用Python

```python
import requests

# 获取知识库列表
response = requests.get('http://localhost:8000/api/v1/knowledge-bases')
print(response.json())

# 创建知识库
response = requests.post(
    'http://localhost:8000/api/v1/knowledge-bases',
    json={
        'name': '测试知识库',
        's3_bucket': 'my-bucket',
        's3_prefix': 'test/'
    }
)
print(response.json())
```

### 6.3 使用JavaScript

```javascript
// 获取知识库列表
fetch('http://localhost:8000/api/v1/knowledge-bases')
  .then(res => res.json())
  .then(data => console.log(data));

// 流式问答
const eventSource = new EventSource(
  'http://localhost:8000/api/v1/knowledge-bases/{kb_id}/query/stream'
);

eventSource.addEventListener('chunk', (e) => {
  const data = JSON.parse(e.data);
  console.log('答案片段:', data.content);
});

eventSource.addEventListener('done', (e) => {
  const data = JSON.parse(e.data);
  console.log('生成完成:', data.query_id);
  eventSource.close();
});
```

---

## 七、限流策略

Demo版本暂不实施限流，未来可考虑：
- 每个IP每分钟最多10次查询请求
- 每个IP每小时最多100次API调用
- 文档上传每天最多50个文件

---

## 八、版本管理

API采用URL路径版本管理：`/api/v1/...`

未来版本变更：
- 不兼容变更：发布新版本 `/api/v2/...`
- 向后兼容变更：在现有版本上扩展
- 旧版本保留至少6个月
