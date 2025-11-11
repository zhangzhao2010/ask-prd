# API接口文档：本地化存储改造

## 1. 变更的API

### 1.1 创建知识库

**接口**：`POST /api/v1/knowledge-bases`

**变更**：移除S3相关参数

**旧请求体**：
```json
{
  "name": "产品PRD知识库",
  "description": "存储所有产品需求文档",
  "s3_bucket": "my-bucket",
  "s3_prefix": "prds/product-a/"
}
```

**新请求体**：
```json
{
  "name": "产品PRD知识库",
  "description": "存储所有产品需求文档"
}
```

**响应**：
```json
{
  "id": "kb-uuid-123",
  "name": "产品PRD知识库",
  "description": "存储所有产品需求文档",
  "local_storage_path": "data/knowledge_bases/kb-uuid-123/",
  "status": "active",
  "created_at": "2025-11-11T10:00:00Z"
}
```

### 1.2 上传文档

**接口**：`POST /api/v1/knowledge-bases/{kb_id}/documents`

**变更**：文件存储到本地，不再上传S3

**请求**：
```http
POST /api/v1/knowledge-bases/kb-123/documents
Content-Type: multipart/form-data

file: @产品PRD_v1.0.pdf
```

**响应**：
```json
{
  "id": "doc-uuid-456",
  "kb_id": "kb-123",
  "filename": "产品PRD_v1.0.pdf",
  "local_pdf_path": "data/documents/pdfs/doc-uuid-456.pdf",
  "file_size": 2048576,
  "status": "uploaded",
  "created_at": "2025-11-11T10:05:00Z"
}
```

### 1.3 数据同步

**接口**：`POST /api/v1/knowledge-bases/{kb_id}/sync`

**变更**：无参数变更，但内部逻辑改为本地存储

**请求体**：
```json
{
  "document_ids": ["doc-uuid-456", "doc-uuid-789"]
}
```

**响应**：
```json
{
  "task_id": "task-uuid-111",
  "status": "pending",
  "total_documents": 2,
  "processed_documents": 0,
  "created_at": "2025-11-11T10:10:00Z"
}
```

### 1.4 智能问答（变更参数）

**接口**：`POST /api/v1/query`

**变更**：新增`top_k`参数，控制检索文档数量

**旧请求体**：
```json
{
  "kb_id": "kb-123",
  "query": "用户增长策略是什么？"
}
```

**新请求体**：
```json
{
  "kb_id": "kb-123",
  "query": "用户增长策略是什么？",
  "top_k": 20
}
```

**参数说明**：
- `top_k`（可选）：检索的最大文档数，默认20，范围1-50

**流式响应**（SSE格式）：
```
event: progress
data: {"type": "progress", "data": {"current": 1, "total": 20, "doc_name": "产品PRD v1.0.pdf"}}

event: progress
data: {"type": "progress", "data": {"current": 2, "total": 20, "doc_name": "产品PRD v2.0.pdf"}}

...

event: status
data: {"type": "status", "message": "正在生成综合答案..."}

event: answer_delta
data: {"type": "answer_delta", "data": {"text": "## 综合回复\n根据"}}

event: answer_delta
data: {"type": "answer_delta", "data": {"text": "文档分析"}}

event: answer_delta
data: {"type": "answer_delta", "data": {"text": "[DOC-abc123-PARA-5]"}}

...

event: answer_delta
data: {"type": "answer_delta", "data": {"text": "\n\n## 引用文档\n\n### 文档1：xxx.pdf\n- [DOC-abc123-PARA-5] xxx"}}

event: done
data: {"type": "done", "data": {}}
```

**说明**：
- 大模型直接输出Markdown格式，包含"综合回复"和"引用文档"两部分
- 前端累积所有`answer_delta`的文本，得到完整Markdown
- 不再有单独的`references`事件

## 2. 新增的API

### 2.1 获取文档图片

**接口**：`GET /api/v1/documents/{doc_id}/images/{image_name}`

**功能**：获取文档中的图片文件

**路径参数**：
- `doc_id`：文档ID
- `image_name`：图片文件名（例如：`_page_1_Figure_1.png`）

**请求示例**：
```http
GET /api/v1/documents/doc-uuid-456/images/_page_1_Figure_1.png
```

**注意**：虽然API路径包含`/images/`，但后端实际从`markdowns/{doc_id}/`目录读取图片（图片与markdown同目录）。

**响应**：
- **成功**（200）：返回图片二进制流
  ```
  Content-Type: image/png
  Content-Length: 102400

  [图片二进制数据]
  ```

- **失败**（404）：图片不存在
  ```json
  {
    "detail": "Image not found"
  }
  ```

**支持的图片格式**：
- PNG (image/png)
- JPEG (image/jpeg)
- GIF (image/gif)
- WEBP (image/webp)

## 3. 请求响应示例

### 3.1 创建知识库示例

```bash
curl -X POST http://localhost:8000/api/v1/knowledge-bases \
  -H "Content-Type: application/json" \
  -d '{
    "name": "产品PRD知识库",
    "description": "存储所有产品需求文档"
  }'
```

### 3.2 上传文档示例

```bash
curl -X POST http://localhost:8000/api/v1/knowledge-bases/kb-123/documents \
  -F "file=@产品PRD_v1.0.pdf"
```

### 3.3 数据同步示例

```bash
curl -X POST http://localhost:8000/api/v1/knowledge-bases/kb-123/sync \
  -H "Content-Type: application/json" \
  -d '{
    "document_ids": ["doc-456", "doc-789"]
  }'
```

### 3.4 智能问答示例

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "kb_id": "kb-123",
    "query": "用户增长策略是什么？",
    "top_k": 10
  }'
```

### 3.5 获取图片示例

```bash
curl http://localhost:8000/api/v1/documents/doc-456/images/_page_1_Figure_1.png \
  --output chart.png
```

## 4. 错误码

| 错误码 | 说明 | 场景 |
|--------|------|------|
| 400 | 参数错误 | `top_k`超出范围（1-50） |
| 404 | 资源不存在 | 文档ID或图片文件不存在 |
| 413 | 文件过大 | PDF超过100MB |
| 422 | 验证失败 | 文件格式不是PDF |
| 500 | 服务器错误 | Marker转换失败、Bedrock调用失败 |

## 5. 前端集成指南

### 5.1 调整知识库创建表单

**移除字段**：
- S3 Bucket输入框
- S3 Prefix输入框

**保留字段**：
- 知识库名称（必填）
- 描述（可选）

### 5.2 智能问答添加top_k参数

**方式1：固定值**
```typescript
const queryKnowledgeBase = async (kbId: string, query: string) => {
  const response = await fetch('/api/v1/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      kb_id: kbId,
      query: query,
      top_k: 20  // 固定值
    })
  });
  // ...
};
```

**方式2：用户可调（高级选项）**
```tsx
<Form>
  <Input label="问题" value={query} onChange={setQuery} />
  <ExpandableSection header="高级选项">
    <Slider
      label="检索文档数量"
      value={topK}
      onChange={setTopK}
      min={1}
      max={50}
      step={1}
    />
  </ExpandableSection>
</Form>
```

### 5.3 渲染Markdown中的图片引用

**核心逻辑**：从Markdown的"引用文档"部分提取图片信息，替换"综合回复"中的图片引用

```typescript
function parseImageReferences(markdown: string): Map<string, string> {
  const refMap = new Map<string, string>();

  // 匹配：- [DOC-xxx-IMAGE-X] 图片：filename.png
  const pattern = /- \[DOC-([a-z0-9]+)-IMAGE-(\d+)\] 图片：([^\n]+)/g;

  let match;
  while ((match = pattern.exec(markdown)) !== null) {
    const refId = `[DOC-${match[1]}-IMAGE-${match[2]}]`;
    const filename = match[3];
    refMap.set(refId, filename);
  }

  return refMap;
}

function renderMarkdownWithImages(markdown: string, docId: string): string {
  const refMap = parseImageReferences(markdown);

  // 只处理"综合回复"部分
  const sections = markdown.split('## 引用文档');
  let answerSection = sections[0];

  // 替换图片引用为实际图片
  answerSection = answerSection.replace(
    /\[DOC-([a-z0-9]+)-IMAGE-(\d+)\]/g,
    (match) => {
      const filename = refMap.get(match);
      if (filename) {
        return `![${match}](/api/v1/documents/${docId}/images/${filename})`;
      }
      return match;
    }
  );

  return answerSection + (sections[1] ? '\n\n## 引用文档' + sections[1] : '');
}
```

**CSS样式**：
```css
.inline-ref-image {
  max-width: 100%;
  max-height: 400px;
  margin: 16px 0;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.ref-link {
  color: #0073bb;
  text-decoration: none;
  font-size: 0.875rem;
  vertical-align: super;
}
```

### 5.4 图片懒加载优化

```tsx
<img
  src={ref.image_url}
  alt={ref.chunk_id}
  loading="lazy"
  onError={(e) => {
    e.currentTarget.src = '/placeholder-image.png';
  }}
/>
```

### 5.5 完整示例（React + Cloudscape）

```tsx
import { useState } from 'react';
import { Button, Textarea, SpaceBetween } from '@cloudscape-design/components';
import ReactMarkdown from 'react-markdown';

function QueryInterface({ kbId, docId }: { kbId: string, docId: string }) {
  const [query, setQuery] = useState('');
  const [markdown, setMarkdown] = useState('');  // 完整markdown
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState<{ current: number, total: number } | null>(null);

  const handleQuery = async () => {
    setLoading(true);
    setMarkdown('');
    setProgress(null);

    const eventSource = new EventSource(
      `/api/v1/query?kb_id=${kbId}&query=${encodeURIComponent(query)}&top_k=20`
    );

    eventSource.addEventListener('progress', (e) => {
      const data = JSON.parse(e.data);
      setProgress(data.data);
    });

    eventSource.addEventListener('answer_delta', (e) => {
      const data = JSON.parse(e.data);
      // 累积markdown文本
      setMarkdown(prev => prev + data.data.text);
    });

    eventSource.addEventListener('done', () => {
      eventSource.close();
      setLoading(false);
    });
  };

  // 渲染markdown，替换图片引用
  const renderedMarkdown = renderMarkdownWithImages(markdown, docId);

  return (
    <SpaceBetween size="l">
      <Textarea
        value={query}
        onChange={({ detail }) => setQuery(detail.value)}
        placeholder="输入你的问题..."
      />

      <Button variant="primary" onClick={handleQuery} loading={loading}>
        提问
      </Button>

      {progress && (
        <div>正在阅读第 {progress.current} / {progress.total} 篇文档...</div>
      )}

      {markdown && (
        <div className="answer-container">
          <ReactMarkdown
            components={{
              img: ({ src, alt }) => (
                <img
                  src={src}
                  alt={alt}
                  className="inline-ref-image"
                  loading="lazy"
                />
              ),
            }}
          >
            {renderedMarkdown}
          </ReactMarkdown>
        </div>
      )}
    </SpaceBetween>
  );
}

// 辅助函数（见5.3节）
function parseImageReferences(markdown: string): Map<string, string> {
  // 实现见上文
}

function renderMarkdownWithImages(markdown: string, docId: string): string {
  // 实现见上文
}
```

---

**API文档完成！**
