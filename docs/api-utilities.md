# API 文档 - 辅助接口

> 版本：v1.0
> 更新时间：2025-01-20

---

## 1. 获取Chunk图片

### 接口信息
- **路径**: `GET /chunks/{chunk_id}/image`
- **描述**: 获取图片chunk的图片文件
- **Content-Type**: `image/*`（根据图片格式）

### 请求参数

| 参数 | 类型 | 位置 | 必填 | 说明 |
|------|------|------|------|------|
| chunk_id | string | path | 是 | 图片chunk的ID |

### 响应

- 成功：返回图片二进制数据
- 失败：返回JSON错误信息

### 响应头

```
Content-Type: image/png (或 image/jpeg, image/webp等)
Content-Length: 文件大小（字节）
Cache-Control: public, max-age=86400 (缓存24小时)
```

### 错误响应

**Chunk不存在**（404）：
```json
{
  "error": {
    "code": "3001",
    "message": "Chunk不存在"
  }
}
```

**Chunk不是图片类型**（400）：
```json
{
  "error": {
    "code": "1002",
    "message": "该Chunk不是图片类型",
    "details": {
      "chunk_id": "chunk-xxx",
      "chunk_type": "text"
    }
  }
}
```

**图片文件不存在**（404）：
```json
{
  "error": {
    "code": "4003",
    "message": "图片文件不存在或下载失败"
  }
}
```

### 使用示例

```html
<!-- HTML中直接使用 -->
<img src="http://localhost:8000/api/v1/chunks/chunk-dd0e8400/image"
     alt="登录流程图" />
```

```python
# Python下载图片
import requests

chunk_id = "chunk-dd0e8400"
response = requests.get(f"{BASE_URL}/chunks/{chunk_id}/image")

if response.status_code == 200:
    with open('image.png', 'wb') as f:
        f.write(response.content)
    print("图片下载成功")
```

```javascript
// JavaScript获取图片
const getChunkImage = async (chunkId) => {
  const response = await fetch(`${BASE_URL}/chunks/${chunkId}/image`);
  const blob = await response.blob();
  const imageUrl = URL.createObjectURL(blob);
  return imageUrl;
};

// 使用
const imageUrl = await getChunkImage('chunk-dd0e8400');
document.getElementById('img').src = imageUrl;
```

---

## 2. 健康检查

### 接口信息
- **路径**: `GET /health`
- **描述**: 检查系统健康状态

### 请求参数

无

### 响应示例（健康）

```json
{
  "status": "healthy",
  "timestamp": "2025-01-20T11:00:00Z",
  "services": {
    "database": {
      "status": "ok",
      "response_time_ms": 2
    },
    "opensearch": {
      "status": "ok",
      "response_time_ms": 45
    },
    "s3": {
      "status": "ok",
      "response_time_ms": 120
    },
    "bedrock": {
      "status": "ok",
      "response_time_ms": 350
    }
  },
  "version": "1.0.0"
}
```

### 响应示例（不健康）

```json
{
  "status": "unhealthy",
  "timestamp": "2025-01-20T11:00:00Z",
  "services": {
    "database": {
      "status": "ok",
      "response_time_ms": 2
    },
    "opensearch": {
      "status": "error",
      "error": "Connection timeout",
      "response_time_ms": 5000
    },
    "s3": {
      "status": "ok",
      "response_time_ms": 120
    },
    "bedrock": {
      "status": "degraded",
      "error": "Rate limiting",
      "response_time_ms": 1200
    }
  },
  "version": "1.0.0"
}
```

### 状态码

- 200: 所有服务正常
- 503: 一个或多个服务不可用

### 使用场景

- 负载均衡器健康检查
- 监控系统探测
- 部署前验证

---

## 3. 系统统计信息

### 接口信息
- **路径**: `GET /stats`
- **描述**: 获取系统统计信息

### 请求参数

| 参数 | 类型 | 位置 | 必填 | 说明 |
|------|------|------|------|------|
| kb_id | string | query | 否 | 知识库ID，不传则返回全局统计 |

### 响应示例（全局统计）

```json
{
  "data": {
    "knowledge_bases": {
      "total": 5,
      "active": 5
    },
    "documents": {
      "total": 230,
      "uploaded": 15,
      "processing": 2,
      "completed": 210,
      "failed": 3
    },
    "chunks": {
      "total": 8450,
      "text_chunks": 7200,
      "image_chunks": 1250
    },
    "queries": {
      "total": 1580,
      "last_24h": 85,
      "success_rate": 0.96
    },
    "tokens": {
      "total": 25480000,
      "last_24h": 350000,
      "avg_per_query": 16000
    },
    "storage": {
      "s3_size_bytes": 5368709120,
      "local_cache_size_bytes": 2147483648
    },
    "sync_tasks": {
      "total": 45,
      "running": 1,
      "completed": 40,
      "failed": 4
    }
  }
}
```

### 响应示例（知识库统计）

```json
{
  "data": {
    "kb_id": "kb-550e8400-e29b-41d4-a716-446655440000",
    "kb_name": "产品PRD知识库",
    "documents": {
      "total": 45,
      "completed": 43,
      "failed": 2
    },
    "chunks": {
      "total": 1250,
      "text_chunks": 1100,
      "image_chunks": 150
    },
    "queries": {
      "total": 230,
      "last_7d": 45,
      "success_rate": 0.98
    },
    "tokens": {
      "total": 3680000,
      "last_7d": 156000,
      "avg_per_query": 16000
    },
    "top_queries": [
      {
        "query_text": "登录注册模块的演进历史",
        "count": 12
      },
      {
        "query_text": "支付模块功能设计",
        "count": 8
      }
    ],
    "recent_documents": [
      {
        "filename": "PRD_v3.0.pdf",
        "uploaded_at": "2025-01-20T10:00:00Z"
      }
    ]
  }
}
```

---

## 4. 导出数据（未来扩展）

### 接口信息
- **路径**: `POST /export`
- **描述**: 导出知识库数据

### 请求参数

```json
{
  "kb_id": "kb-550e8400",
  "export_type": "full",
  "format": "json"
}
```

### 请求字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kb_id | string | 是 | 知识库ID |
| export_type | string | 是 | full（完整）/ metadata（仅元数据） |
| format | string | 是 | json / csv |

### 响应示例

```json
{
  "data": {
    "export_id": "export-aa0e8400",
    "status": "processing",
    "download_url": null,
    "created_at": "2025-01-20T11:00:00Z"
  }
}
```

### 导出完成后

```json
{
  "data": {
    "export_id": "export-aa0e8400",
    "status": "completed",
    "download_url": "/api/v1/exports/export-aa0e8400/download",
    "file_size": 52428800,
    "expires_at": "2025-01-21T11:00:00Z",
    "completed_at": "2025-01-20T11:05:00Z"
  }
}
```

---

## 5. 批量操作（未来扩展）

### 接口信息
- **路径**: `POST /batch`
- **描述**: 批量执行操作

### 请求参数

```json
{
  "operations": [
    {
      "op": "delete_document",
      "params": {"doc_id": "doc-xxx"}
    },
    {
      "op": "delete_document",
      "params": {"doc_id": "doc-yyy"}
    }
  ]
}
```

### 响应示例

```json
{
  "data": {
    "results": [
      {"op": "delete_document", "doc_id": "doc-xxx", "success": true},
      {"op": "delete_document", "doc_id": "doc-yyy", "success": false, "error": "文档不存在"}
    ],
    "success_count": 1,
    "failure_count": 1
  }
}
```

---

## 6. 清理缓存

### 接口信息
- **路径**: `POST /cache/clear`
- **描述**: 清理本地文件缓存

### 请求参数

```json
{
  "type": "lru",
  "target_size_mb": 1024
}
```

### 请求字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | string | 是 | lru（最近最少使用）/ all（全部） |
| target_size_mb | integer | 否 | 目标缓存大小（MB） |

### 响应示例

```json
{
  "message": "缓存清理完成",
  "data": {
    "before_size_mb": 2048,
    "after_size_mb": 1024,
    "freed_size_mb": 1024,
    "deleted_files": 125
  }
}
```

---

## 使用示例

### Python

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# 1. 健康检查
response = requests.get(f"{BASE_URL}/health")
if response.json()['status'] == 'healthy':
    print("系统正常")

# 2. 获取统计信息
response = requests.get(f"{BASE_URL}/stats")
stats = response.json()['data']
print(f"总文档数: {stats['documents']['total']}")
print(f"总查询数: {stats['queries']['total']}")
print(f"总Token消耗: {stats['tokens']['total']}")

# 3. 获取知识库统计
kb_id = "kb-550e8400"
response = requests.get(f"{BASE_URL}/stats?kb_id={kb_id}")
kb_stats = response.json()['data']
print(f"{kb_stats['kb_name']} - 文档数: {kb_stats['documents']['total']}")

# 4. 获取图片
chunk_id = "chunk-dd0e8400"
response = requests.get(f"{BASE_URL}/chunks/{chunk_id}/image")
with open('image.png', 'wb') as f:
    f.write(response.content)

# 5. 清理缓存
response = requests.post(
    f"{BASE_URL}/cache/clear",
    json={"type": "lru", "target_size_mb": 1024}
)
print(f"释放空间: {response.json()['data']['freed_size_mb']} MB")
```

### cURL

```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# 获取统计信息
curl http://localhost:8000/api/v1/stats

# 获取知识库统计
curl "http://localhost:8000/api/v1/stats?kb_id=kb-550e8400"

# 下载图片
curl "http://localhost:8000/api/v1/chunks/chunk-dd0e8400/image" \
  -o image.png

# 清理缓存
curl -X POST http://localhost:8000/api/v1/cache/clear \
  -H "Content-Type: application/json" \
  -d '{"type": "lru", "target_size_mb": 1024}'
```

### JavaScript

```javascript
const BASE_URL = 'http://localhost:8000/api/v1';

// 健康检查
const checkHealth = async () => {
  const response = await fetch(`${BASE_URL}/health`);
  const data = await response.json();
  return data.status === 'healthy';
};

// 获取统计信息
const getStats = async (kbId = null) => {
  const url = kbId
    ? `${BASE_URL}/stats?kb_id=${kbId}`
    : `${BASE_URL}/stats`;
  const response = await fetch(url);
  return await response.json();
};

// 获取图片
const getImage = async (chunkId) => {
  const response = await fetch(`${BASE_URL}/chunks/${chunkId}/image`);
  const blob = await response.blob();
  return URL.createObjectURL(blob);
};

// 使用
if (await checkHealth()) {
  const stats = await getStats();
  console.log('系统统计:', stats.data);

  const imageUrl = await getImage('chunk-dd0e8400');
  document.getElementById('img').src = imageUrl;
}
```

---

## 监控集成

### Prometheus Metrics（未来扩展）

```
# 暴露metrics端点
GET /metrics

# 示例输出
# HELP aks_prd_queries_total Total number of queries
# TYPE aks_prd_queries_total counter
aks_prd_queries_total{kb_id="kb-550e8400",status="success"} 1580

# HELP aks_prd_query_duration_seconds Query duration in seconds
# TYPE aks_prd_query_duration_seconds histogram
aks_prd_query_duration_seconds_bucket{le="5"} 1200
aks_prd_query_duration_seconds_bucket{le="10"} 1500
aks_prd_query_duration_seconds_bucket{le="+Inf"} 1580

# HELP aks_prd_tokens_total Total tokens consumed
# TYPE aks_prd_tokens_total counter
aks_prd_tokens_total{type="prompt"} 23800000
aks_prd_tokens_total{type="completion"} 1680000
```

---

## 注意事项

1. **图片缓存**: 图片接口返回Cache-Control头，浏览器会自动缓存24小时
2. **健康检查**: 健康检查端点响应时间应 < 1秒，超时视为不健康
3. **统计延迟**: 统计数据可能有1-2分钟延迟，非实时
4. **缓存清理**: 清理缓存不会影响正在运行的任务
5. **并发限制**: 统计接口有限流，建议前端缓存结果
