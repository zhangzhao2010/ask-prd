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

event: done
data: {}
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

    elif event.event == 'done':
        print(f"\n完成！")

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
