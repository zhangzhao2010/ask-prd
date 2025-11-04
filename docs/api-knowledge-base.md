# API 文档 - 知识库管理

> 版本：v1.0
> 更新时间：2025-01-20

---

## 1. 获取知识库列表

### 接口信息
- **路径**: `GET /knowledge-bases`
- **描述**: 获取所有知识库列表

### 请求参数

无

### 响应示例

```json
{
  "data": [
    {
      "id": "kb-550e8400-e29b-41d4-a716-446655440000",
      "name": "产品PRD知识库",
      "description": "包含所有产品迭代的PRD文档",
      "s3_bucket": "my-prd-bucket",
      "s3_prefix": "prds/product-a/",
      "opensearch_collection_id": "abc123xyz",
      "opensearch_index_name": "kb_550e8400_index",
      "document_count": 45,
      "status": "active",
      "created_at": "2025-01-01T10:00:00Z",
      "updated_at": "2025-01-15T14:30:00Z"
    },
    {
      "id": "kb-660e8400-e29b-41d4-a716-446655440001",
      "name": "技术文档知识库",
      "description": "技术设计文档",
      "s3_bucket": "my-prd-bucket",
      "s3_prefix": "tech-docs/",
      "opensearch_collection_id": "def456uvw",
      "opensearch_index_name": "kb_660e8400_index",
      "document_count": 23,
      "status": "active",
      "created_at": "2025-01-10T08:00:00Z",
      "updated_at": "2025-01-18T16:20:00Z"
    }
  ]
}
```

### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 知识库ID（UUID） |
| name | string | 知识库名称 |
| description | string | 描述信息 |
| s3_bucket | string | S3桶名 |
| s3_prefix | string | S3路径前缀 |
| opensearch_collection_id | string | OpenSearch Collection ID |
| opensearch_index_name | string | OpenSearch Index名称 |
| document_count | integer | 文档数量 |
| status | string | 状态：active/deleted |
| created_at | string | 创建时间（ISO 8601） |
| updated_at | string | 更新时间（ISO 8601） |

---

## 2. 创建知识库

### 接口信息
- **路径**: `POST /knowledge-bases`
- **描述**: 创建新的知识库

### 请求参数

```json
{
  "name": "新产品知识库",
  "description": "用于存储新产品的PRD文档",
  "s3_bucket": "my-bucket",
  "s3_prefix": "prds/new-product/"
}
```

### 请求字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 知识库名称，2-50字符，不能重复 |
| description | string | 否 | 描述信息，最多500字符 |
| s3_bucket | string | 是 | S3桶名，必须已存在且有权限访问 |
| s3_prefix | string | 是 | S3路径前缀，必须以`/`结尾 |

### 处理流程

1. 验证参数有效性
2. 检查知识库名称是否重复
3. 验证S3桶和路径是否可访问
4. 在OpenSearch创建Collection和Index
5. 在SQLite创建知识库记录
6. 返回创建结果

### 响应示例（成功）

```json
{
  "data": {
    "id": "kb-770e8400-e29b-41d4-a716-446655440002",
    "name": "新产品知识库",
    "description": "用于存储新产品的PRD文档",
    "s3_bucket": "my-bucket",
    "s3_prefix": "prds/new-product/",
    "opensearch_collection_id": "ghi789rst",
    "opensearch_index_name": "kb_770e8400_index",
    "status": "active",
    "created_at": "2025-01-20T10:00:00Z",
    "updated_at": "2025-01-20T10:00:00Z"
  }
}
```

### 错误响应

**知识库名称已存在**（400）：
```json
{
  "error": {
    "code": "2002",
    "message": "知识库名称已存在",
    "details": {
      "name": "新产品知识库"
    }
  }
}
```

**S3桶不存在或无权限**（400）：
```json
{
  "error": {
    "code": "4004",
    "message": "S3桶不存在或无访问权限",
    "details": {
      "s3_bucket": "my-bucket"
    }
  }
}
```

**OpenSearch创建失败**（500）：
```json
{
  "error": {
    "code": "2011",
    "message": "OpenSearch索引创建失败",
    "details": {
      "reason": "Connection timeout"
    }
  }
}
```

---

## 3. 获取知识库详情

### 接口信息
- **路径**: `GET /knowledge-bases/{kb_id}`
- **描述**: 获取指定知识库的详细信息

### 请求参数

| 参数 | 类型 | 位置 | 必填 | 说明 |
|------|------|------|------|------|
| kb_id | string | path | 是 | 知识库ID |

### 响应示例

```json
{
  "data": {
    "id": "kb-550e8400-e29b-41d4-a716-446655440000",
    "name": "产品PRD知识库",
    "description": "包含所有产品迭代的PRD文档",
    "s3_bucket": "my-prd-bucket",
    "s3_prefix": "prds/product-a/",
    "opensearch_collection_id": "abc123xyz",
    "opensearch_index_name": "kb_550e8400_index",
    "document_count": 45,
    "chunk_count": 1250,
    "total_tokens": 850000,
    "status": "active",
    "created_at": "2025-01-01T10:00:00Z",
    "updated_at": "2025-01-15T14:30:00Z",
    "stats": {
      "text_chunks": 1100,
      "image_chunks": 150,
      "total_queries": 230,
      "avg_response_time_ms": 8500
    }
  }
}
```

### 错误响应

**知识库不存在**（404）：
```json
{
  "error": {
    "code": "2001",
    "message": "知识库不存在",
    "details": {
      "kb_id": "kb-invalid-id"
    }
  }
}
```

---

## 4. 删除知识库

### 接口信息
- **路径**: `DELETE /knowledge-bases/{kb_id}`
- **描述**: 删除指定知识库及所有关联数据

### 请求参数

| 参数 | 类型 | 位置 | 必填 | 说明 |
|------|------|------|------|------|
| kb_id | string | path | 是 | 知识库ID |
| force | boolean | query | 否 | 是否强制删除（默认false） |

### 删除范围

删除操作将清理以下所有数据：
1. SQLite中的知识库记录、文档记录、chunk记录、查询历史
2. OpenSearch中的Index
3. S3中的所有文件（可选，通过force参数控制）
4. 本地缓存的所有文件

### 响应示例（成功）

```json
{
  "message": "知识库删除成功",
  "data": {
    "kb_id": "kb-550e8400-e29b-41d4-a716-446655440000",
    "deleted_documents": 45,
    "deleted_chunks": 1250,
    "deleted_s3_objects": 92
  }
}
```

### 错误响应

**知识库不存在**（404）：
```json
{
  "error": {
    "code": "2001",
    "message": "知识库不存在"
  }
}
```

**删除失败**（500）：
```json
{
  "error": {
    "code": "2003",
    "message": "知识库删除失败",
    "details": {
      "reason": "OpenSearch索引删除失败"
    }
  }
}
```

### 注意事项

- 删除操作不可逆
- 建议在删除前导出重要数据
- 如果有正在运行的同步任务，建议先取消任务
- `force=true`时会删除S3中的原始文件，请谨慎使用

---

## 5. 更新知识库（未来扩展）

### 接口信息
- **路径**: `PATCH /knowledge-bases/{kb_id}`
- **描述**: 更新知识库信息（仅名称和描述）

### 请求参数

```json
{
  "name": "更新后的名称",
  "description": "更新后的描述"
}
```

### 响应示例

```json
{
  "data": {
    "id": "kb-550e8400-e29b-41d4-a716-446655440000",
    "name": "更新后的名称",
    "description": "更新后的描述",
    "updated_at": "2025-01-20T11:00:00Z"
  }
}
```

---

## 使用示例

### Python

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# 1. 获取知识库列表
response = requests.get(f"{BASE_URL}/knowledge-bases")
kbs = response.json()['data']
print(f"共有 {len(kbs)} 个知识库")

# 2. 创建知识库
new_kb = {
    "name": "测试知识库",
    "description": "用于测试",
    "s3_bucket": "my-bucket",
    "s3_prefix": "test/"
}
response = requests.post(f"{BASE_URL}/knowledge-bases", json=new_kb)
kb_id = response.json()['data']['id']
print(f"创建成功，知识库ID: {kb_id}")

# 3. 获取知识库详情
response = requests.get(f"{BASE_URL}/knowledge-bases/{kb_id}")
kb_detail = response.json()['data']
print(f"文档数量: {kb_detail['document_count']}")

# 4. 删除知识库（谨慎）
# response = requests.delete(f"{BASE_URL}/knowledge-bases/{kb_id}")
# print("删除成功")
```

### cURL

```bash
# 获取知识库列表
curl http://localhost:8000/api/v1/knowledge-bases

# 创建知识库
curl -X POST http://localhost:8000/api/v1/knowledge-bases \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试知识库",
    "description": "用于测试",
    "s3_bucket": "my-bucket",
    "s3_prefix": "test/"
  }'

# 获取知识库详情
curl http://localhost:8000/api/v1/knowledge-bases/{kb_id}

# 删除知识库
curl -X DELETE http://localhost:8000/api/v1/knowledge-bases/{kb_id}
```
