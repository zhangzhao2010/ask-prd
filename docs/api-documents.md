# API 文档 - 文档管理

> 版本：v1.0
> 更新时间：2025-01-20

---

## 1. 获取文档列表

### 接口信息
- **路径**: `GET /knowledge-bases/{kb_id}/documents`
- **描述**: 获取指定知识库的文档列表

### 请求参数

| 参数 | 类型 | 位置 | 必填 | 说明 |
|------|------|------|------|------|
| kb_id | string | path | 是 | 知识库ID |
| status | string | query | 否 | 过滤状态：uploaded/processing/completed/failed |
| page | integer | query | 否 | 页码，默认1 |
| page_size | integer | query | 否 | 每页数量，默认20，最大100 |

### 响应示例

```json
{
  "data": [
    {
      "id": "doc-660e8400-e29b-41d4-a716-446655440001",
      "kb_id": "kb-550e8400-e29b-41d4-a716-446655440000",
      "filename": "PRD_登录注册_v1.2.pdf",
      "s3_key": "prds/product-a/PRD_登录注册_v1.2.pdf",
      "file_size": 2048576,
      "page_count": 15,
      "chunk_count": 45,
      "status": "completed",
      "error_message": null,
      "created_at": "2025-01-10T10:00:00Z",
      "updated_at": "2025-01-10T10:05:00Z"
    },
    {
      "id": "doc-770e8400-e29b-41d4-a716-446655440002",
      "kb_id": "kb-550e8400-e29b-41d4-a716-446655440000",
      "filename": "PRD_支付模块_v2.0.pdf",
      "s3_key": "prds/product-a/PRD_支付模块_v2.0.pdf",
      "file_size": 3145728,
      "page_count": 22,
      "chunk_count": 68,
      "status": "completed",
      "error_message": null,
      "created_at": "2025-01-12T14:30:00Z",
      "updated_at": "2025-01-12T14:38:00Z"
    },
    {
      "id": "doc-880e8400-e29b-41d4-a716-446655440003",
      "kb_id": "kb-550e8400-e29b-41d4-a716-446655440000",
      "filename": "PRD_订单系统_v1.0.pdf",
      "s3_key": "prds/product-a/PRD_订单系统_v1.0.pdf",
      "file_size": 5242880,
      "page_count": 35,
      "chunk_count": 0,
      "status": "failed",
      "error_message": "PDF转换失败: 文件损坏",
      "created_at": "2025-01-15T09:20:00Z",
      "updated_at": "2025-01-15T09:25:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 45,
    "total_pages": 3
  }
}
```

### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 文档ID（UUID） |
| kb_id | string | 所属知识库ID |
| filename | string | 原始文件名 |
| s3_key | string | S3完整路径 |
| file_size | integer | 文件大小（字节） |
| page_count | integer | PDF页数 |
| chunk_count | integer | chunk数量 |
| status | string | 状态：uploaded/processing/completed/failed |
| error_message | string | 错误信息（失败时） |
| created_at | string | 创建时间 |
| updated_at | string | 更新时间 |

---

## 2. 上传文档

### 接口信息
- **路径**: `POST /knowledge-bases/{kb_id}/documents/upload`
- **描述**: 上传PDF文档到指定知识库
- **Content-Type**: `multipart/form-data`

### 请求参数

| 参数 | 类型 | 位置 | 必填 | 说明 |
|------|------|------|------|------|
| kb_id | string | path | 是 | 知识库ID |
| file | file | form | 是 | PDF文件 |

### 文件要求

- 格式：仅支持PDF
- 大小：最大100MB
- 命名：建议使用有意义的文件名，如"PRD_功能名称_版本号.pdf"

### 响应示例（成功）

```json
{
  "data": {
    "id": "doc-990e8400-e29b-41d4-a716-446655440004",
    "kb_id": "kb-550e8400-e29b-41d4-a716-446655440000",
    "filename": "PRD_购物车_v1.5.pdf",
    "s3_key": "prds/product-a/PRD_购物车_v1.5.pdf",
    "file_size": 1536000,
    "status": "uploaded",
    "created_at": "2025-01-20T10:00:00Z"
  }
}
```

### 错误响应

**文件格式无效**（400）：
```json
{
  "error": {
    "code": "3004",
    "message": "文档格式无效，仅支持PDF",
    "details": {
      "filename": "document.docx",
      "detected_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }
  }
}
```

**文件过大**（400）：
```json
{
  "error": {
    "code": "3003",
    "message": "文档大小超过限制",
    "details": {
      "file_size": 157286400,
      "max_size": 104857600
    }
  }
}
```

**S3上传失败**（500）：
```json
{
  "error": {
    "code": "4002",
    "message": "S3上传失败",
    "details": {
      "reason": "Access denied"
    }
  }
}
```

---

## 3. 批量删除文档

### 接口信息
- **路径**: `DELETE /knowledge-bases/{kb_id}/documents`
- **描述**: 批量删除文档及相关数据

### 请求参数

```json
{
  "document_ids": [
    "doc-660e8400-e29b-41d4-a716-446655440001",
    "doc-770e8400-e29b-41d4-a716-446655440002"
  ]
}
```

### 请求字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| document_ids | array | 是 | 文档ID数组，最多100个 |

### 删除范围

删除操作将清理：
1. SQLite中的文档记录和chunks记录
2. OpenSearch中的向量数据
3. S3中的PDF、Markdown和图片文件
4. 本地缓存文件

### 响应示例（成功）

```json
{
  "message": "文档删除成功",
  "data": {
    "deleted_count": 2,
    "deleted_document_ids": [
      "doc-660e8400-e29b-41d4-a716-446655440001",
      "doc-770e8400-e29b-41d4-a716-446655440002"
    ],
    "deleted_chunks": 113,
    "deleted_s3_objects": 25
  }
}
```

### 错误响应

**文档不存在**（404）：
```json
{
  "error": {
    "code": "3001",
    "message": "部分文档不存在",
    "details": {
      "not_found": ["doc-invalid-id"]
    }
  }
}
```

---

## 4. 获取文档详情

### 接口信息
- **路径**: `GET /documents/{doc_id}`
- **描述**: 获取文档详细信息

### 请求参数

| 参数 | 类型 | 位置 | 必填 | 说明 |
|------|------|------|------|------|
| doc_id | string | path | 是 | 文档ID |

### 响应示例

```json
{
  "data": {
    "id": "doc-660e8400-e29b-41d4-a716-446655440001",
    "kb_id": "kb-550e8400-e29b-41d4-a716-446655440000",
    "kb_name": "产品PRD知识库",
    "filename": "PRD_登录注册_v1.2.pdf",
    "s3_key": "prds/product-a/PRD_登录注册_v1.2.pdf",
    "s3_key_markdown": "prds/product-a/converted/PRD_登录注册_v1.2/content.md",
    "file_size": 2048576,
    "page_count": 15,
    "status": "completed",
    "chunks": {
      "total": 45,
      "text_chunks": 38,
      "image_chunks": 7
    },
    "processing_info": {
      "conversion_time_ms": 45000,
      "vectorization_time_ms": 12000,
      "total_time_ms": 57000
    },
    "created_at": "2025-01-10T10:00:00Z",
    "updated_at": "2025-01-10T10:05:00Z"
  }
}
```

---

## 5. 获取文档的Chunks

### 接口信息
- **路径**: `GET /documents/{doc_id}/chunks`
- **描述**: 获取文档的所有chunks

### 请求参数

| 参数 | 类型 | 位置 | 必填 | 说明 |
|------|------|------|------|------|
| doc_id | string | path | 是 | 文档ID |
| chunk_type | string | query | 否 | 过滤类型：text/image |

### 响应示例

```json
{
  "data": [
    {
      "id": "chunk-aa0e8400-e29b-41d4-a716-446655440005",
      "document_id": "doc-660e8400-e29b-41d4-a716-446655440001",
      "chunk_type": "text",
      "chunk_index": 0,
      "content": "# 登录注册模块 PRD\n\n## 1. 背景\n\nv1.2版本的登录注册模块...",
      "token_count": 85,
      "created_at": "2025-01-10T10:05:00Z"
    },
    {
      "id": "chunk-bb0e8400-e29b-41d4-a716-446655440006",
      "document_id": "doc-660e8400-e29b-41d4-a716-446655440001",
      "chunk_type": "image",
      "chunk_index": 5,
      "image_filename": "login_flow.png",
      "image_description": "登录流程图，包含用户输入、验证、跳转三个步骤",
      "image_type": "flowchart",
      "token_count": 120,
      "created_at": "2025-01-10T10:05:00Z"
    }
  ]
}
```

---

## 6. 重新处理文档（重试）

### 接口信息
- **路径**: `POST /documents/{doc_id}/retry`
- **描述**: 重新处理失败的文档

### 请求参数

| 参数 | 类型 | 位置 | 必填 | 说明 |
|------|------|------|------|------|
| doc_id | string | path | 是 | 文档ID |

### 响应示例

```json
{
  "message": "重新处理任务已创建",
  "data": {
    "document_id": "doc-880e8400-e29b-41d4-a716-446655440003",
    "status": "processing",
    "task_id": "task-cc0e8400-e29b-41d4-a716-446655440007"
  }
}
```

---

## 使用示例

### Python

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"
KB_ID = "kb-550e8400-e29b-41d4-a716-446655440000"

# 1. 获取文档列表
response = requests.get(f"{BASE_URL}/knowledge-bases/{KB_ID}/documents")
docs = response.json()['data']
print(f"共有 {len(docs)} 个文档")

# 2. 上传文档
with open('/path/to/prd.pdf', 'rb') as f:
    files = {'file': f}
    response = requests.post(
        f"{BASE_URL}/knowledge-bases/{KB_ID}/documents/upload",
        files=files
    )
doc_id = response.json()['data']['id']
print(f"上传成功，文档ID: {doc_id}")

# 3. 获取文档详情
response = requests.get(f"{BASE_URL}/documents/{doc_id}")
doc_detail = response.json()['data']
print(f"文档状态: {doc_detail['status']}")

# 4. 删除文档
response = requests.delete(
    f"{BASE_URL}/knowledge-bases/{KB_ID}/documents",
    json={"document_ids": [doc_id]}
)
print(f"删除成功: {response.json()['message']}")
```

### cURL

```bash
# 获取文档列表
curl "http://localhost:8000/api/v1/knowledge-bases/{kb_id}/documents?status=completed&page=1&page_size=20"

# 上传文档
curl -X POST "http://localhost:8000/api/v1/knowledge-bases/{kb_id}/documents/upload" \
  -F "file=@/path/to/prd.pdf"

# 获取文档详情
curl "http://localhost:8000/api/v1/documents/{doc_id}"

# 删除文档
curl -X DELETE "http://localhost:8000/api/v1/knowledge-bases/{kb_id}/documents" \
  -H "Content-Type: application/json" \
  -d '{"document_ids": ["doc-id-1", "doc-id-2"]}'

# 重试失败文档
curl -X POST "http://localhost:8000/api/v1/documents/{doc_id}/retry"
```

### JavaScript

```javascript
const BASE_URL = 'http://localhost:8000/api/v1';
const KB_ID = 'kb-550e8400-e29b-41d4-a716-446655440000';

// 上传文档
const uploadDocument = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(
    `${BASE_URL}/knowledge-bases/${KB_ID}/documents/upload`,
    {
      method: 'POST',
      body: formData
    }
  );

  return await response.json();
};

// 获取文档列表
const getDocuments = async (status = null, page = 1) => {
  let url = `${BASE_URL}/knowledge-bases/${KB_ID}/documents?page=${page}`;
  if (status) url += `&status=${status}`;

  const response = await fetch(url);
  return await response.json();
};

// 删除文档
const deleteDocuments = async (documentIds) => {
  const response = await fetch(
    `${BASE_URL}/knowledge-bases/${KB_ID}/documents`,
    {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document_ids: documentIds })
    }
  );

  return await response.json();
};
```
