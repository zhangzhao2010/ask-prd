# API 文档 - 同步任务

> 版本：v1.0
> 更新时间：2025-01-20

---

## 1. 创建同步任务

### 接口信息
- **路径**: `POST /knowledge-bases/{kb_id}/sync`
- **描述**: 创建数据同步任务，异步处理文档转换和向量化

### 请求参数

```json
{
  "task_type": "full_sync",
  "document_ids": []
}
```

### 请求字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_type | string | 是 | 任务类型：full_sync（全量）/ incremental（增量） |
| document_ids | array | 否 | 文档ID数组，空数组表示全量同步 |

### 任务类型说明

- **full_sync**: 同步所有`uploaded`状态的文档
- **incremental**: 仅同步指定的文档（通过document_ids指定）

### 响应示例（成功）

```json
{
  "data": {
    "task_id": "task-dd0e8400-e29b-41d4-a716-446655440008",
    "kb_id": "kb-550e8400-e29b-41d4-a716-446655440000",
    "task_type": "full_sync",
    "status": "pending",
    "total_documents": 3,
    "created_at": "2025-01-20T10:00:00Z"
  }
}
```

### 错误响应

**已有任务在运行**（400）：
```json
{
  "error": {
    "code": "7002",
    "message": "该知识库已有同步任务在运行",
    "details": {
      "running_task_id": "task-ee0e8400-e29b-41d4-a716-446655440009"
    }
  }
}
```

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

## 2. 获取同步任务列表

### 接口信息
- **路径**: `GET /knowledge-bases/{kb_id}/sync-tasks`
- **描述**: 获取指定知识库的同步任务列表

### 请求参数

| 参数 | 类型 | 位置 | 必填 | 说明 |
|------|------|------|------|------|
| kb_id | string | path | 是 | 知识库ID |
| status | string | query | 否 | 过滤状态：pending/running/completed/failed/partial_success |
| limit | integer | query | 否 | 返回数量，默认10，最大50 |

### 响应示例

```json
{
  "data": [
    {
      "id": "task-dd0e8400-e29b-41d4-a716-446655440008",
      "kb_id": "kb-550e8400-e29b-41d4-a716-446655440000",
      "task_type": "full_sync",
      "status": "running",
      "progress": 65,
      "current_step": "正在向量化文档 PRD_v2.0.pdf (2/3)",
      "total_documents": 3,
      "processed_documents": 2,
      "failed_documents": 0,
      "started_at": "2025-01-20T10:00:00Z",
      "created_at": "2025-01-20T09:59:00Z"
    },
    {
      "id": "task-ee0e8400-e29b-41d4-a716-446655440009",
      "kb_id": "kb-550e8400-e29b-41d4-a716-446655440000",
      "task_type": "incremental",
      "status": "completed",
      "progress": 100,
      "current_step": "完成",
      "total_documents": 5,
      "processed_documents": 5,
      "failed_documents": 0,
      "started_at": "2025-01-19T14:00:00Z",
      "completed_at": "2025-01-19T14:12:00Z",
      "created_at": "2025-01-19T13:59:00Z"
    },
    {
      "id": "task-ff0e8400-e29b-41d4-a716-446655440010",
      "kb_id": "kb-550e8400-e29b-41d4-a716-446655440000",
      "task_type": "full_sync",
      "status": "partial_success",
      "progress": 100,
      "current_step": "完成（部分失败）",
      "total_documents": 10,
      "processed_documents": 8,
      "failed_documents": 2,
      "started_at": "2025-01-18T09:00:00Z",
      "completed_at": "2025-01-18T09:25:00Z",
      "created_at": "2025-01-18T08:59:00Z"
    }
  ]
}
```

---

## 3. 获取任务详情

### 接口信息
- **路径**: `GET /sync-tasks/{task_id}`
- **描述**: 获取同步任务的详细信息和实时进度

### 请求参数

| 参数 | 类型 | 位置 | 必填 | 说明 |
|------|------|------|------|------|
| task_id | string | path | 是 | 任务ID |

### 响应示例（运行中）

```json
{
  "data": {
    "id": "task-dd0e8400-e29b-41d4-a716-446655440008",
    "kb_id": "kb-550e8400-e29b-41d4-a716-446655440000",
    "task_type": "full_sync",
    "status": "running",
    "progress": 65,
    "current_step": "正在向量化文档 PRD_v2.0.pdf",
    "total_documents": 3,
    "processed_documents": 2,
    "failed_documents": 0,
    "documents": [
      {
        "document_id": "doc-aa0e8400",
        "filename": "PRD_v1.0.pdf",
        "status": "completed",
        "chunks_created": 35,
        "processing_time_ms": 45000
      },
      {
        "document_id": "doc-bb0e8400",
        "filename": "PRD_v1.5.pdf",
        "status": "completed",
        "chunks_created": 42,
        "processing_time_ms": 52000
      },
      {
        "document_id": "doc-cc0e8400",
        "filename": "PRD_v2.0.pdf",
        "status": "processing",
        "chunks_created": 0,
        "processing_time_ms": 0
      }
    ],
    "started_at": "2025-01-20T10:00:00Z",
    "created_at": "2025-01-20T09:59:00Z"
  }
}
```

### 响应示例（部分失败）

```json
{
  "data": {
    "id": "task-ff0e8400-e29b-41d4-a716-446655440010",
    "kb_id": "kb-550e8400-e29b-41d4-a716-446655440000",
    "task_type": "full_sync",
    "status": "partial_success",
    "progress": 100,
    "current_step": "完成（部分失败）",
    "total_documents": 10,
    "processed_documents": 8,
    "failed_documents": 2,
    "documents": [
      {
        "document_id": "doc-gg0e8400",
        "filename": "PRD_broken.pdf",
        "status": "failed",
        "error_message": "PDF转换失败: 文件损坏",
        "chunks_created": 0
      },
      {
        "document_id": "doc-hh0e8400",
        "filename": "PRD_large.pdf",
        "status": "failed",
        "error_message": "向量化失败: Bedrock限流",
        "chunks_created": 25
      }
    ],
    "started_at": "2025-01-18T09:00:00Z",
    "completed_at": "2025-01-18T09:25:00Z",
    "created_at": "2025-01-18T08:59:00Z"
  }
}
```

---

## 4. 取消任务

### 接口信息
- **路径**: `POST /sync-tasks/{task_id}/cancel`
- **描述**: 取消正在运行的同步任务

### 请求参数

| 参数 | 类型 | 位置 | 必填 | 说明 |
|------|------|------|------|------|
| task_id | string | path | 是 | 任务ID |

### 响应示例

```json
{
  "message": "任务取消成功",
  "data": {
    "task_id": "task-dd0e8400-e29b-41d4-a716-446655440008",
    "status": "cancelled",
    "processed_documents": 2,
    "cancelled_at": "2025-01-20T10:05:00Z"
  }
}
```

### 错误响应

**任务不在运行中**（400）：
```json
{
  "error": {
    "code": "7003",
    "message": "任务不在运行中，无法取消",
    "details": {
      "task_id": "task-dd0e8400",
      "current_status": "completed"
    }
  }
}
```

---

## 5. 重试失败文档

### 接口信息
- **路径**: `POST /sync-tasks/{task_id}/retry-failed`
- **描述**: 重新处理任务中失败的文档

### 请求参数

| 参数 | 类型 | 位置 | 必填 | 说明 |
|------|------|------|------|------|
| task_id | string | path | 是 | 任务ID |

### 响应示例

```json
{
  "message": "重试任务已创建",
  "data": {
    "new_task_id": "task-ii0e8400-e29b-41d4-a716-446655440011",
    "retry_document_count": 2,
    "document_ids": ["doc-gg0e8400", "doc-hh0e8400"]
  }
}
```

---

## 任务状态流转

```
pending (待执行)
    ↓
running (执行中)
    ↓
    ├─→ completed (全部成功)
    ├─→ partial_success (部分成功)
    ├─→ failed (全部失败)
    └─→ cancelled (已取消)
```

---

## 进度说明

### progress 计算方式

```
progress = (processed_documents / total_documents) * 100
```

### current_step 示例

- `"正在下载文档 PRD_v1.0.pdf (1/10)"`
- `"正在转换PDF PRD_v1.0.pdf (1/10)"`
- `"正在处理图片 3/8"`
- `"正在分块 PRD_v1.0.pdf (1/10)"`
- `"正在向量化 PRD_v1.0.pdf (1/10)"`
- `"正在存储向量数据 (1/10)"`
- `"完成"`
- `"完成（部分失败）"`

---

## 使用示例

### Python - 创建任务并轮询进度

```python
import requests
import time

BASE_URL = "http://localhost:8000/api/v1"
KB_ID = "kb-550e8400-e29b-41d4-a716-446655440000"

# 1. 创建同步任务
response = requests.post(
    f"{BASE_URL}/knowledge-bases/{KB_ID}/sync",
    json={"task_type": "full_sync", "document_ids": []}
)
task_id = response.json()['data']['task_id']
print(f"任务创建成功: {task_id}")

# 2. 轮询任务进度
while True:
    response = requests.get(f"{BASE_URL}/sync-tasks/{task_id}")
    task = response.json()['data']

    status = task['status']
    progress = task['progress']
    current_step = task['current_step']

    print(f"进度: {progress}% - {current_step}")

    if status in ['completed', 'failed', 'partial_success', 'cancelled']:
        print(f"任务结束，状态: {status}")
        if task['failed_documents'] > 0:
            print(f"失败文档数: {task['failed_documents']}")
        break

    time.sleep(2)  # 每2秒查询一次

# 3. 如果有失败文档，重试
if task['failed_documents'] > 0:
    response = requests.post(f"{BASE_URL}/sync-tasks/{task_id}/retry-failed")
    new_task_id = response.json()['data']['new_task_id']
    print(f"重试任务已创建: {new_task_id}")
```

### JavaScript - WebSocket实时进度（未来扩展）

```javascript
// 当前版本使用轮询，未来可扩展为WebSocket
const pollTaskProgress = async (taskId) => {
  const response = await fetch(`${BASE_URL}/sync-tasks/${taskId}`);
  const data = await response.json();
  return data.data;
};

const monitorTask = async (taskId) => {
  const interval = setInterval(async () => {
    const task = await pollTaskProgress(taskId);

    console.log(`进度: ${task.progress}% - ${task.current_step}`);

    if (['completed', 'failed', 'partial_success', 'cancelled'].includes(task.status)) {
      clearInterval(interval);
      console.log(`任务完成，状态: ${task.status}`);
    }
  }, 2000);
};

// 使用
const response = await fetch(`${BASE_URL}/knowledge-bases/${kbId}/sync`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ task_type: 'full_sync', document_ids: [] })
});

const { task_id } = (await response.json()).data;
monitorTask(task_id);
```

### cURL

```bash
# 创建同步任务
curl -X POST "http://localhost:8000/api/v1/knowledge-bases/{kb_id}/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "full_sync",
    "document_ids": []
  }'

# 获取任务列表
curl "http://localhost:8000/api/v1/knowledge-bases/{kb_id}/sync-tasks?status=running"

# 获取任务详情
curl "http://localhost:8000/api/v1/sync-tasks/{task_id}"

# 取消任务
curl -X POST "http://localhost:8000/api/v1/sync-tasks/{task_id}/cancel"

# 重试失败文档
curl -X POST "http://localhost:8000/api/v1/sync-tasks/{task_id}/retry-failed"
```

---

## 注意事项

1. **并发限制**: 同一知识库同时只能运行一个同步任务
2. **任务时长**: 大文档处理可能需要数分钟，建议前端轮询间隔2-5秒
3. **失败重试**: 部分失败时可使用retry-failed接口重试失败文档
4. **任务取消**: 取消任务会停止后续文档处理，已处理的文档不会回滚
5. **进度精度**: progress是估算值，可能不完全线性增长
