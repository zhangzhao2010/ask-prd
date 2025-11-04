# API 文档 - 检索问答

> 版本：v1.0
> 更新时间：2025-01-20

---

## 1. 流式问答（SSE）

### 接口信息
- **路径**: `POST /knowledge-bases/{kb_id}/query/stream`
- **描述**: 提交问题并以流式方式返回答案
- **协议**: Server-Sent Events (SSE)

### 请求参数

```json
{
  "query": "登录注册模块的演进历史是怎样的？"
}
```

### 请求字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | 是 | 用户问题，1-500字符 |

### SSE事件类型

| 事件类型 | 说明 | 触发时机 |
|---------|------|---------|
| status | 处理状态更新 | 每个处理步骤开始时 |
| retrieved_documents | 检索到的文档 | 检索完成后 |
| chunk | 答案文本片段 | 答案生成中（流式） |
| citation | 引用信息 | 发现引用时 |
| tokens | Token统计 | 生成完成后 |
| done | 生成完成 | 全部完成时 |
| error | 错误 | 发生错误时 |

### 响应示例（完整流程）

```
event: status
data: {"status": "rewriting_query", "message": "正在优化查询..."}

event: status
data: {"status": "searching", "message": "正在检索文档..."}

event: retrieved_documents
data: {"document_ids": ["doc-aa0e8400", "doc-bb0e8400"], "document_names": ["PRD_v1.0.pdf", "PRD_v2.0.pdf"], "chunk_count": 8}

event: status
data: {"status": "reading_documents", "message": "正在阅读文档 1/2"}

event: status
data: {"status": "reading_documents", "message": "正在阅读文档 2/2"}

event: status
data: {"status": "generating", "message": "正在生成答案..."}

event: chunk
data: {"content": "根据检索到的文档，"}

event: chunk
data: {"content": "登录注册模块经历了以下演进：\n\n"}

event: chunk
data: {"content": "## 第一阶段（v1.0，2023年1月）\n\n"}

event: chunk
data: {"content": "最初版本仅支持**手机号+短信验证码**登录方式。"}

event: citation
data: {"chunk_id": "chunk-cc0e8400", "chunk_type": "text", "document_id": "doc-aa0e8400", "document_name": "PRD_v1.0.pdf", "content": "v1.0版本支持手机号+短信验证码登录...", "chunk_index": 5}

event: chunk
data: {"content": "\n\n## 第二阶段（v1.5，2023年6月）\n\n"}

event: chunk
data: {"content": "新增了以下登录方式：\n- 微信一键登录\n- 邮箱+密码登录\n\n"}

event: chunk
data: {"content": "登录流程如下图所示："}

event: citation
data: {"chunk_id": "chunk-dd0e8400", "chunk_type": "image", "document_id": "doc-bb0e8400", "document_name": "PRD_v1.5.pdf", "image_url": "/api/chunks/chunk-dd0e8400/image", "image_description": "登录流程图，展示了用户输入、验证、跳转三个步骤", "chunk_index": 8}

event: chunk
data: {"content": "\n\n## 第三阶段（v2.0，2024年1月）\n\n"}

event: chunk
data: {"content": "进一步增强了安全性和便捷性：\n- 增加人脸识别登录\n- 支持第三方OAuth（Apple、Google）\n- 增加设备信任机制"}

event: citation
data: {"chunk_id": "chunk-ee0e8400", "chunk_type": "text", "document_id": "doc-cc0e8400", "document_name": "PRD_v2.0.pdf", "content": "v2.0新增人脸识别登录和第三方OAuth支持...", "chunk_index": 12}

event: tokens
data: {"prompt_tokens": 15230, "completion_tokens": 856, "total_tokens": 16086}

event: done
data: {"query_id": "query-ff0e8400-e29b-41d4-a716-446655440012", "created_at": "2025-01-20T11:00:00Z"}
```

### 错误事件

```
event: error
data: {"code": "8004", "message": "未找到相关文档，请尝试换个问法"}

event: done
data: {"query_id": null}
```

### Citation数据结构

**文本引用**：
```json
{
  "chunk_id": "chunk-cc0e8400",
  "chunk_type": "text",
  "document_id": "doc-aa0e8400",
  "document_name": "PRD_v1.0.pdf",
  "content": "v1.0版本支持手机号+短信验证码登录...",
  "chunk_index": 5
}
```

**图片引用**：
```json
{
  "chunk_id": "chunk-dd0e8400",
  "chunk_type": "image",
  "document_id": "doc-bb0e8400",
  "document_name": "PRD_v1.5.pdf",
  "image_url": "/api/chunks/chunk-dd0e8400/image",
  "image_description": "登录流程图，展示了用户输入、验证、跳转三个步骤",
  "chunk_index": 8
}
```

---

## 2. 获取查询历史列表

### 接口信息
- **路径**: `GET /knowledge-bases/{kb_id}/query-history`
- **描述**: 获取指定知识库的查询历史

### 请求参数

| 参数 | 类型 | 位置 | 必填 | 说明 |
|------|------|------|------|------|
| kb_id | string | path | 是 | 知识库ID |
| page | integer | query | 否 | 页码，默认1 |
| page_size | integer | query | 否 | 每页数量，默认20，最大100 |
| status | string | query | 否 | 过滤状态：completed/failed |

### 响应示例

```json
{
  "data": [
    {
      "id": "query-ff0e8400-e29b-41d4-a716-446655440012",
      "kb_id": "kb-550e8400-e29b-41d4-a716-446655440000",
      "query_text": "登录注册模块的演进历史是怎样的？",
      "answer_preview": "根据检索到的文档，登录注册模块经历了以下演进：\n\n第一阶段（v1.0，2023年1月）：最初版本仅支持手机号+短信验证码登录方式...",
      "total_tokens": 16086,
      "response_time_ms": 8500,
      "status": "completed",
      "created_at": "2025-01-20T11:00:00Z"
    },
    {
      "id": "query-gg0e8400-e29b-41d4-a716-446655440013",
      "kb_id": "kb-550e8400-e29b-41d4-a716-446655440000",
      "query_text": "支付模块有哪些功能？",
      "answer_preview": "支付模块主要包含以下功能：\n\n1. **多种支付方式**：支持微信支付、支付宝、银行卡...",
      "total_tokens": 12450,
      "response_time_ms": 7200,
      "status": "completed",
      "created_at": "2025-01-20T10:30:00Z"
    },
    {
      "id": "query-hh0e8400-e29b-41d4-a716-446655440014",
      "kb_id": "kb-550e8400-e29b-41d4-a716-446655440000",
      "query_text": "xxxx模块设计",
      "answer_preview": null,
      "total_tokens": 0,
      "response_time_ms": 2500,
      "status": "failed",
      "error_message": "未找到相关文档",
      "created_at": "2025-01-20T09:15:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 150,
    "total_pages": 8
  }
}
```

---

## 3. 获取查询详情

### 接口信息
- **路径**: `GET /query-history/{query_id}`
- **描述**: 获取指定查询的完整信息

### 请求参数

| 参数 | 类型 | 位置 | 必填 | 说明 |
|------|------|------|------|------|
| query_id | string | path | 是 | 查询ID |

### 响应示例

```json
{
  "data": {
    "id": "query-ff0e8400-e29b-41d4-a716-446655440012",
    "kb_id": "kb-550e8400-e29b-41d4-a716-446655440000",
    "kb_name": "产品PRD知识库",
    "query_text": "登录注册模块的演进历史是怎样的？",
    "rewritten_queries": [
      "登录功能的版本迭代历史",
      "用户认证模块的发展历程",
      "注册登录方式的演进"
    ],
    "retrieved_document_ids": [
      "doc-aa0e8400",
      "doc-bb0e8400",
      "doc-cc0e8400"
    ],
    "answer": "根据检索到的文档，登录注册模块经历了以下演进：\n\n## 第一阶段（v1.0，2023年1月）\n\n最初版本仅支持**手机号+短信验证码**登录方式。[^1]\n\n## 第二阶段（v1.5，2023年6月）\n\n新增了以下登录方式：\n- 微信一键登录\n- 邮箱+密码登录\n\n登录流程如下图所示：[^2]\n\n## 第三阶段（v2.0，2024年1月）\n\n进一步增强了安全性和便捷性：\n- 增加人脸识别登录\n- 支持第三方OAuth（Apple、Google）\n- 增加设备信任机制[^3]",
    "citations": [
      {
        "chunk_id": "chunk-cc0e8400",
        "chunk_type": "text",
        "document_id": "doc-aa0e8400",
        "document_name": "PRD_v1.0.pdf",
        "content": "v1.0版本支持手机号+短信验证码登录，用户输入手机号后，系统发送6位数字验证码，验证通过后创建账号或登录。",
        "chunk_index": 5
      },
      {
        "chunk_id": "chunk-dd0e8400",
        "chunk_type": "image",
        "document_id": "doc-bb0e8400",
        "document_name": "PRD_v1.5.pdf",
        "image_url": "/api/chunks/chunk-dd0e8400/image",
        "image_description": "登录流程图，展示了用户输入、验证、跳转三个步骤，采用泳道图形式，包含用户端、服务端、第三方服务三个角色。",
        "chunk_index": 8
      },
      {
        "chunk_id": "chunk-ee0e8400",
        "chunk_type": "text",
        "document_id": "doc-cc0e8400",
        "document_name": "PRD_v2.0.pdf",
        "content": "v2.0新增人脸识别登录和第三方OAuth支持（Apple、Google），同时引入设备信任机制，在信任设备上可跳过二次验证。",
        "chunk_index": 12
      }
    ],
    "total_tokens": 16086,
    "prompt_tokens": 15230,
    "completion_tokens": 856,
    "response_time_ms": 8500,
    "status": "completed",
    "created_at": "2025-01-20T11:00:00Z"
  }
}
```

### 错误响应

**查询不存在**（404）：
```json
{
  "error": {
    "code": "8001",
    "message": "查询记录不存在",
    "details": {
      "query_id": "query-invalid-id"
    }
  }
}
```

---

## 4. 删除查询历史

### 接口信息
- **路径**: `DELETE /query-history/{query_id}`
- **描述**: 删除指定的查询记录

### 请求参数

| 参数 | 类型 | 位置 | 必填 | 说明 |
|------|------|------|------|------|
| query_id | string | path | 是 | 查询ID |

### 响应示例

```json
{
  "message": "查询历史删除成功"
}
```

---

## 使用示例

### Python - 使用sseclient库

```python
import requests
import json
from sseclient import SSEClient

BASE_URL = "http://localhost:8000/api/v1"
KB_ID = "kb-550e8400-e29b-41d4-a716-446655440000"

# 流式问答
query = {"query": "登录注册模块的演进历史是怎样的？"}

response = requests.post(
    f"{BASE_URL}/knowledge-bases/{KB_ID}/query/stream",
    json=query,
    stream=True,
    headers={'Accept': 'text/event-stream'}
)

client = SSEClient(response)

answer_text = ""
citations = []
query_id = None

for event in client.events():
    data = json.loads(event.data)

    if event.event == 'status':
        print(f"状态: {data['message']}")

    elif event.event == 'retrieved_documents':
        print(f"检索到 {len(data['document_ids'])} 个文档")

    elif event.event == 'chunk':
        answer_text += data['content']
        print(data['content'], end='', flush=True)

    elif event.event == 'citation':
        citations.append(data)

    elif event.event == 'tokens':
        print(f"\n\nToken消耗: {data['total_tokens']}")

    elif event.event == 'done':
        query_id = data['query_id']
        print(f"\n完成！查询ID: {query_id}")

    elif event.event == 'error':
        print(f"\n错误: {data['message']}")
        break

# 展示引用
print("\n\n引用来源：")
for i, citation in enumerate(citations, 1):
    if citation['chunk_type'] == 'text':
        print(f"[{i}] {citation['document_name']}: {citation['content'][:100]}...")
    else:
        print(f"[{i}] {citation['document_name']}: [图片] {citation['image_description']}")
```

### JavaScript - 使用EventSource

```javascript
const BASE_URL = 'http://localhost:8000/api/v1';
const KB_ID = 'kb-550e8400-e29b-41d4-a716-446655440000';

const streamQuery = (query) => {
  // 注意：EventSource不支持POST，需要后端支持GET方式或使用fetch
  // 这里使用fetch + EventSource polyfill

  const url = `${BASE_URL}/knowledge-bases/${KB_ID}/query/stream`;

  fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream'
    },
    body: JSON.stringify({ query })
  }).then(response => {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    const processStream = ({ done, value }) => {
      if (done) {
        console.log('Stream complete');
        return;
      }

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      lines.forEach(line => {
        if (line.startsWith('event:')) {
          const eventType = line.substring(7).trim();
          console.log('Event:', eventType);
        } else if (line.startsWith('data:')) {
          const data = JSON.parse(line.substring(6));

          if (data.content) {
            // 答案片段
            document.getElementById('answer').innerHTML += data.content;
          } else if (data.chunk_id) {
            // 引用
            addCitation(data);
          } else if (data.total_tokens) {
            // Token统计
            document.getElementById('tokens').innerText = data.total_tokens;
          }
        }
      });

      reader.read().then(processStream);
    };

    reader.read().then(processStream);
  });
};

// 使用
streamQuery('登录注册模块的演进历史是怎样的？');
```

### cURL - 测试SSE

```bash
# 流式问答（会持续输出事件流）
curl -N -X POST "http://localhost:8000/api/v1/knowledge-bases/{kb_id}/query/stream" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"query": "登录注册模块的演进历史是怎样的？"}'

# 获取查询历史
curl "http://localhost:8000/api/v1/knowledge-bases/{kb_id}/query-history?page=1&page_size=20"

# 获取查询详情
curl "http://localhost:8000/api/v1/query-history/{query_id}"

# 删除查询历史
curl -X DELETE "http://localhost:8000/api/v1/query-history/{query_id}"
```

---

## 前端集成建议

### 1. 答案展示组件

```jsx
import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';

const AnswerDisplay = ({ kbId, query }) => {
  const [answer, setAnswer] = useState('');
  const [citations, setCitations] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleQuery = async () => {
    setLoading(true);
    setAnswer('');
    setCitations([]);

    const response = await fetch(`/api/v1/knowledge-bases/${kbId}/query/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      // 解析SSE事件并更新UI
      // ... (同上JavaScript示例)
    }

    setLoading(false);
  };

  return (
    <div>
      <ReactMarkdown>{answer}</ReactMarkdown>
      <div className="citations">
        {citations.map((c, i) => (
          <Citation key={i} data={c} />
        ))}
      </div>
    </div>
  );
};
```

### 2. 引用展示组件

```jsx
const Citation = ({ data }) => {
  if (data.chunk_type === 'text') {
    return (
      <div className="citation-text">
        <strong>{data.document_name}</strong>
        <p>{data.content}</p>
      </div>
    );
  } else {
    return (
      <div className="citation-image">
        <strong>{data.document_name}</strong>
        <img src={data.image_url} alt={data.image_description} />
        <p className="description">{data.image_description}</p>
      </div>
    );
  }
};
```

---

## 性能优化建议

1. **客户端缓存**: 缓存最近的查询结果，避免重复请求
2. **去抖处理**: 用户输入时避免频繁触发查询
3. **超时处理**: 设置30秒超时，超时后提示用户
4. **错误重试**: 网络错误时自动重试1-2次
5. **Token展示**: 实时展示Token消耗，帮助用户了解成本
