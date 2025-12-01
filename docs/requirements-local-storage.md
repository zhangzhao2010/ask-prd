# 需求文档：本地化存储改造

## 1. 变更概述

### 1.1 变更目标
将ASK-PRD系统从依赖S3存储改为完全本地化存储，简化Demo部署和开发流程。

### 1.2 变更范围
- **知识库管理**：移除S3配置要求
- **文档上传**：PDF存储到本地文件系统
- **数据同步**：Marker转换结果存储到本地
- **图片处理**：生成图片描述并替换markdown中的图片引用
- **智能问答**：Agent读取原始markdown（含图片），使用Vision API理解图片

### 1.3 不变更内容
- 向量数据库（OpenSearch）存储方式
- 数据库Schema基本结构
- Multi-Agent工作流核心逻辑
- 前端交互模式

---

## 2. 功能需求

### 2.1 知识库创建（变更）

**原有逻辑**：
```json
POST /api/v1/knowledge-bases
{
  "name": "产品PRD",
  "s3_bucket": "my-bucket",
  "s3_prefix": "prds/product-a/"
}
```

**新逻辑**：
```json
POST /api/v1/knowledge-bases
{
  "name": "产品PRD",
  "description": "产品需求文档知识库"
}
```

**变更点**：
- 移除 `s3_bucket` 和 `s3_prefix` 参数
- 系统自动为每个知识库分配本地存储目录
- 目录结构：`data/knowledge_bases/{kb_id}/`

---

### 2.2 文档上传（变更）

**原有逻辑**：
- 上传PDF到S3
- Document表记录 `s3_key`
- 状态设置为 `uploaded`

**新逻辑**：
```
POST /api/v1/knowledge-bases/{kb_id}/documents
Content-Type: multipart/form-data

file: xxx.pdf
```

**文件存储规则**：
1. 生成 `document_id`（UUID）
2. PDF存储到：`data/documents/pdfs/{document_id}.pdf`
3. 创建Document记录，状态设置为 `uploaded`
4. 返回 `document_id`

**数据库记录**：
```python
Document(
    id=document_id,
    kb_id=kb_id,
    filename="xxx.pdf",
    local_pdf_path="data/documents/pdfs/{document_id}.pdf",
    status="uploaded"
)
```

---

### 2.3 数据同步（重大变更）

#### 2.3.1 触发方式
**不变**：用户手动点击"同步数据"按钮

```
POST /api/v1/knowledge-bases/{kb_id}/sync
{
  "document_ids": ["doc-id-1", "doc-id-2"]
}
```

#### 2.3.2 同步流程（7个步骤）

**Step 1: Marker转换PDF**
- 输入：`data/documents/pdfs/{document_id}.pdf`
- 输出目录：`data/documents/markdowns/{document_id}/`
- 输出内容：
  - `content.md`：原始markdown（含图片引用 `![](xxx.png)`）
  - `*.png/jpeg`：图片文件，保留原始文件名，与content.md同目录

**示例输出**：
```
data/documents/markdowns/abc-123/
├── content.md
├── _page_1_Figure_1.png
└── _page_2_Chart_5.jpeg
```

**Step 2: 生成图片描述（带上下文）**

**关键改进**：不再单独理解图片，而是结合上下文：

1. **解析markdown结构**：
   - 将markdown解析为内容序列：文本块、图片块交替
   - 记录每个图片在文档中的位置

2. **按顺序生成描述**（从第一张到最后一张）：
   - 获取**上文**（最多500字符）：
     - 如果上一个元素是文本 → 取文本内容
     - 如果上一个元素是图片 → 取该图片的描述（已生成）
   - 获取**下文**（最多500字符）：
     - 如果下一个元素是文本 → 取文本内容
     - 如果下一个元素是图片 → 不传（还没生成）
   - 调用Bedrock Vision API，传入：上文+图片+下文

3. **生成严格格式的描述**：

```xml
<figure>
<figure_type>Chart</figure_type>
<figure_description>这是一个柱状图，展示了2023年Q1-Q4的用户增长趋势。Q1用户数为1000，Q2增长到1500，Q3达到2300，Q4突破3000。整体呈现快速增长态势。</figure_description>
</figure>
```

**figure_type枚举值**：
- `Chart`：图表（柱状图、折线图、饼图等）
- `Diagram`：示意图（架构图、流程图）
- `Logo`：标志、图标
- `Icon`：小图标
- `Natural Image`：自然图片（照片）
- `Screenshot`：截图
- `Other`：其他类型

**Prompt模板示例**：
```
你正在阅读一份产品文档，需要理解文档中的图片。

【上文】
{context_before}

【当前图片】
[图片内容...]

【下文】
{context_after}

请结合上下文，详细描述这张图片的内容、类型和作用。

首先判断图片类型（Chart/Diagram/Logo/Icon/Natural Image/Screenshot/Other），
然后生成详细描述，包括：
- 图片的主要内容
- 图片在文档中的作用（例如：支撑论点、展示数据、说明流程等）
- 关键信息和细节

输出格式：
<figure>
<figure_type>图片类型</figure_type>
<figure_description>详细描述...</figure_description>
</figure>
```

**实际示例**：

假设markdown内容：
```markdown
用户增长策略如下：
![](img1.png)
根据上图可以看出，Q3-Q4增速明显加快...
```

传给Vision API：
```
【上文】
用户增长策略如下：

【当前图片】
[img1.png的bytes]

【下文】
根据上图可以看出，Q3-Q4增速明显加快...
```

生成的描述：
```xml
<figure>
<figure_type>Chart</figure_type>
<figure_description>这是一个展示用户增长策略效果的柱状图。图表标题为"2023年用户增长趋势"，横轴为季度（Q1-Q4），纵轴为用户数。数据显示Q1-Q2增长平缓，但Q3-Q4增速明显加快，与下文提到的"增速加快"相呼应。这张图用于支撑用户增长策略的有效性。</figure_description>
</figure>
```

**处理流程示意**：
```
markdown内容：
  段落1 → 图片1 → 段落2 → 图片2 → 段落3

生成顺序：
  图片1：上文=段落1, 下文=段落2  → 生成描述1
  图片2：上文=段落2+[图片1描述], 下文=段落3  → 生成描述2
```

**Step 3: 替换markdown中的图片**
- 使用Step 2生成的描述，替换所有图片引用
- 查找：`![](xxx.png)`
- 替换为：图片描述块（保留图片路径信息）

**替换规则**：
```markdown
# 原始markdown
用户增长策略如下：
![](_page_1_Figure_1.png)
基于上图可以看出...

# 替换后
用户增长策略如下：

[IMAGE:_page_1_Figure_1.png]
<figure>
<figure_type>Chart</figure_type>
<figure_description>这是一个柱状图，展示了2023年Q1-Q4的用户增长趋势...</figure_description>
</figure>

基于上图可以看出...
```

**关键点**：
- 插入 `[IMAGE:xxx]` 标记，保留图片路径信息
- 紧接着插入 `<figure>` 描述块
- 保持原有文本内容不变

**Step 4: 生成text_markdown**
- 将替换后的markdown保存到：`data/documents/text_markdowns/{document_id}.md`
- 这是纯文本版本，用于向量化

**Step 5: 文本分块（Chunking）**
- 读取 `text_markdowns/{document_id}.md`
- 使用现有的分块策略（RecursiveCharacterTextSplitter）
- chunk_size: 1000, overlap: 200
- 图片描述会被包含在chunk中

**Step 6: 向量化（Embedding）**
- 每个text chunk生成embedding（使用Titan Embeddings V2）
- 不再为图片生成独立chunk
- 图片描述已经融入文本chunk

**Step 7: 存储到OpenSearch**
- 将chunk和embedding写入OpenSearch
- 索引名：`kb_{kb_id}_index`
- 同时写入SQLite的chunks表

---

### 2.4 智能问答（重大变更）

#### 2.4.1 工作流（4个阶段）

**阶段1: 混合召回**
```
POST /api/v1/query
{
  "kb_id": "xxx",
  "query": "用户增长策略是什么？",
  "top_k": 20
}
```

- Query Rewrite：生成多个检索查询
- 混合检索：kNN + BM25
- 返回Top-K个相关文档的document_id列表

**变更点**：
- `top_k` 设置为可配置参数（默认20）
- 允许前端或配置文件调整

**阶段2: 读取原始markdown**
- 根据document_id找到：`data/documents/markdowns/{document_id}/`
- 读取 `content.md`（原始版本，含图片引用 `![](xxx.png)`）
- 读取同级目录下的所有图片文件（`*.png`, `*.jpeg`, `*.jpg`, `*.gif`, `*.webp`）

**阶段3: 串行问答（图文混排）**

对每个文档执行：

1. **构建图文混排content**：
   ```python
   content = []
   # 解析markdown，按顺序插入文本和图片
   # 遇到 ![](images/xxx.png)，读取图片并转为bytes
   content.append({"text": "段落1内容"})
   content.append({"text": "[IMAGE: xxx.png]"})
   content.append({
       "image": {
           "format": "png",
           "source": {"bytes": image_bytes}
       }
   })
   content.append({"text": "段落2内容"})
   ```

2. **调用Bedrock Vision API**：
   - 模型：Claude Sonnet 4.5
   - 输入：图文混排content
   - Prompt：见2.4.2
   - 输出：文档结构、回答、引用

3. **流式推送进度**：
   ```json
   {
     "type": "progress",
     "data": {
       "current": 3,
       "total": 20,
       "doc_name": "产品PRD v1.0.pdf"
     }
   }
   ```

**阶段4: 综合答案**
- 收集所有文档的回答和引用
- 调用Bedrock生成最终答案（**Markdown格式，包含"综合回复"和"引用文档"两部分**）
- 流式输出完整markdown（逐字推送）
- 前端直接渲染markdown展示

---

#### 2.4.2 Prompt设计

**Stage 1 Prompt（单文档理解）**：

```
以下是一份产品文档的完整内容，包含文字和图片。
文档中的每个段落都有标记 [DOC-{doc_short_id}-PARA-X]，每张图片都有标记 [DOC-{doc_short_id}-IMAGE-X]。

请仔细阅读文档（包括图片中的信息），然后按照以下格式回复：

## 文档结构
[简要描述文档的主题、版本、日期等元信息，1-2句话]
[列出文档的主要分块，每个分块一行，格式：- [DOC-xxx-PARA-X] 分块主题]

## 针对query的回复
[基于本文档内容回答用户问题，务必在相关内容后标注引用来源]
例如：根据[DOC-xxx-PARA-5]的描述，用户增长策略包括...
如图[DOC-xxx-IMAGE-2]所示，系统架构分为...

## 引用
[列出所有引用的段落和图片，每个引用占一行：]
[DOC-xxx-PARA-X] 段落完整内容...
[DOC-xxx-IMAGE-X] 图片文件名

用户问题：{query}
```

**Stage 2 Prompt（综合答案）**：

```
我已经让{doc_count}个助手分别阅读了相关文档，并基于这些文档回答了用户的问题。

以下是每个助手的回复：

=== 文档1: xxx.pdf ===
[Stage 1输出]

=== 文档2: yyy.pdf ===
[Stage 1输出]

...

现在请你综合这些回复，给出一个完整、准确、结构清晰的最终答案。

**输出格式要求**（直接输出Markdown，无需JSON）：

## 综合回复
[在这里写出完整的回答，结构清晰，逻辑连贯]
[重要：回答中需要标注引用来源，格式为 [DOC-xxx-PARA-X] 或 [DOC-xxx-IMAGE-X]]

例如：
根据产品需求文档[DOC-abc12345-PARA-5]，用户增长策略包括三个方面...
如架构图[DOC-def67890-IMAGE-2]所示，系统分为三层...

## 引用文档

### 文档1：{doc_name_1}
- [DOC-xxx-PARA-5] 段落完整内容...
- [DOC-xxx-IMAGE-1] 图片：xxx.png

### 文档2：{doc_name_2}
- [DOC-xxx-PARA-3] 段落完整内容...
- [DOC-xxx-IMAGE-2] 图片：yyy.jpeg

（按文档分组，列出所有被引用的段落和图片）


**关键要求**：
1. **必须保持引用标记**：在"综合回复"中提到信息时，必须在相关句子后添加引用标记 [DOC-xxx-PARA-X] 或 [DOC-xxx-IMAGE-X]
2. 如果多个文档的回复有冲突，请指出差异并说明可能的原因
3. 如果多个文档的回复互补，请整合成完整答案
4. 答案要自然流畅，不要简单罗列
5. 在"引用文档"部分，按文档分组列出所有被引用的段落和图片完整内容

用户问题：{query}
```

---

### 2.5 图片展示（新增API）

#### 2.5.1 图片代理API

```
GET /api/v1/documents/{doc_id}/images/{image_name}
```

**功能**：
- 从 `data/documents/markdowns/{doc_id}/images/{image_name}` 读取图片
- 返回图片二进制流
- 设置正确的Content-Type

**示例**：
```python
@app.get("/api/v1/documents/{doc_id}/images/{image_name}")
async def get_document_image(doc_id: str, image_name: str):
    image_path = f"data/documents/markdowns/{doc_id}/images/{image_name}"
    if not os.path.exists(image_path):
        raise HTTPException(404, "Image not found")

    # 判断图片格式
    ext = image_name.split('.')[-1].lower()
    media_type = f"image/{ext}" if ext != "jpg" else "image/jpeg"

    return FileResponse(image_path, media_type=media_type)
```

#### 2.5.2 前端渲染逻辑

**大模型输出的Markdown示例**：
```markdown
## 综合回复
根据用户增长策略[DOC-abc123-PARA-5]，系统采用三阶段方案。如架构图[DOC-abc123-IMAGE-1]所示，系统分为三层...

## 引用文档

### 文档1：产品PRD v1.0.pdf
- [DOC-abc123-PARA-5] 用户增长策略包括...
- [DOC-abc123-IMAGE-1] 图片：_page_1_Figure_1.png

### 文档2：技术方案.pdf
- [DOC-def456-PARA-3] 技术架构采用...
```

**前端处理步骤**：

1. **接收流式Markdown**：直接累积所有`answer_delta`事件的文本

2. **解析引用信息**：
```typescript
function parseReferences(markdown: string): Map<string, string> {
  const refMap = new Map<string, string>();

  // 匹配 "引用文档" 部分的图片引用
  // 格式：- [DOC-xxx-IMAGE-X] 图片：filename.png
  const imageRefPattern = /- \[DOC-([a-z0-9]+)-IMAGE-(\d+)\] 图片：([^\n]+)/g;

  let match;
  while ((match = imageRefPattern.exec(markdown)) !== null) {
    const docShortId = match[1];  // abc123
    const imgNum = match[2];      // 1
    const filename = match[3];    // _page_1_Figure_1.png

    const refId = `[DOC-${docShortId}-IMAGE-${imgNum}]`;
    refMap.set(refId, filename);
  }

  return refMap;
}
```

3. **替换图片引用为实际图片**：
```typescript
function renderMarkdownWithImages(markdown: string, docId: string): string {
  const refMap = parseReferences(markdown);

  // 只处理"综合回复"部分
  const sections = markdown.split('## 引用文档');
  let answerSection = sections[0];
  const referencesSection = sections[1] || '';

  // 替换图片引用
  answerSection = answerSection.replace(
    /\[DOC-([a-z0-9]+)-IMAGE-(\d+)\]/g,
    (match) => {
      const filename = refMap.get(match);
      if (filename) {
        // 构建图片URL
        const imageUrl = `/api/v1/documents/${docId}/images/${filename}`;
        return `![${match}](${imageUrl})`;
      }
      return match;
    }
  );

  // 返回处理后的完整markdown
  return answerSection + (referencesSection ? '\n\n## 引用文档' + referencesSection : '');
}
```

4. **使用ReactMarkdown渲染**：
```tsx
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
  {renderMarkdownWithImages(fullMarkdown, docId)}
</ReactMarkdown>
```

---

## 3. 数据库Schema变更

### 3.1 KnowledgeBase表

**移除字段**：
- `s3_bucket`
- `s3_prefix`

**新增字段**：
- `local_storage_path`：本地存储目录，格式：`data/knowledge_bases/{kb_id}/`

### 3.2 Document表

**移除字段**：
- `s3_key`（原始PDF的S3路径）
- `s3_key_markdown`（Markdown的S3路径）

**新增/修改字段**：
- `local_pdf_path`：PDF本地路径，格式：`data/documents/pdfs/{document_id}.pdf`
- `local_markdown_path`：原始markdown路径，格式：`data/documents/markdowns/{document_id}/content.md`
- `local_text_markdown_path`：纯文本markdown路径，格式：`data/documents/text_markdowns/{document_id}.md`

### 3.3 Chunk表

**移除字段**：
- `image_s3_key`
- `image_local_path`

**新增字段**：
- `source_document_path`：用于快速定位原始文档

**说明**：
- 图片不再作为独立chunk
- 图片描述已融入text chunk

---

## 4. 目录结构

```
data/
├── knowledge_bases/          # 知识库目录（预留，暂未使用）
│   └── {kb_id}/
├── documents/
│   ├── pdfs/                 # 原始PDF
│   │   └── {document_id}.pdf
│   ├── markdowns/            # Marker转换结果（原始版本，含图片）
│   │   └── {document_id}/
│   │       ├── content.md
│   │       ├── _page_1_Figure_1.png
│   │       └── _page_2_Chart_5.jpeg
│   └── text_markdowns/       # 纯文本版本（图片描述版本，用于向量化）
│       └── {document_id}.md
├── cache/                    # 临时缓存（可清理）
│   ├── conversions/          # Marker转换临时目录
│   └── temp/
└── ask-prd.db                # SQLite数据库
```

---

## 5. 配置变更

### 5.1 环境变量

**移除**：
```bash
S3_BUCKET=xxx
```

**新增**：
```bash
# 数据存储根目录
DATA_DIR=/home/ubuntu/ask-prd/data

# 可调参数
MAX_RETRIEVAL_DOCS=20  # 混合召回的最大文档数
```

### 5.2 代码配置

**backend/app/core/config.py**：
```python
class Settings(BaseSettings):
    # 移除
    # s3_bucket: str

    # 新增
    data_dir: str = "/home/ubuntu/ask-prd/data"
    max_retrieval_docs: int = 20  # 可配置

    # 派生路径
    @property
    def pdf_dir(self) -> str:
        return os.path.join(self.data_dir, "documents", "pdfs")

    @property
    def markdown_dir(self) -> str:
        return os.path.join(self.data_dir, "documents", "markdowns")

    @property
    def text_markdown_dir(self) -> str:
        return os.path.join(self.data_dir, "documents", "text_markdowns")
```

---

## 6. 验收标准

### 6.1 功能验收

- [ ] 创建知识库时不需要输入S3信息
- [ ] 上传PDF后，文件正确存储到 `data/documents/pdfs/`
- [ ] 同步数据时：
  - [ ] Marker正确转换PDF为markdown+图片
  - [ ] 图片正确存储到 `markdowns/{doc_id}/images/`
  - [ ] 所有图片都成功生成描述（`<figure>`格式）
  - [ ] text_markdown正确包含图片描述和 `[IMAGE:xxx]` 标记
  - [ ] chunk正确生成并向量化
- [ ] 智能问答时：
  - [ ] 能读取到20篇文档（如果召回了20篇）
  - [ ] 显示"正在阅读第X/20篇文档"进度提示
  - [ ] Agent能看到图片（Vision API调用成功）
  - [ ] 最终答案是Markdown格式
  - [ ] 引用中包含图片引用
- [ ] 前端能正确展示图片：
  - [ ] 调用 `/api/v1/documents/{doc_id}/images/{image_name}` 成功返回图片
  - [ ] 答案中的图片引用能渲染为实际图片

### 6.2 性能验收

- [ ] 20篇文档串行读取时间 < 180秒（平均9秒/篇）
- [ ] 单张图片描述生成 < 5秒
- [ ] 10MB PDF转换时间 < 60秒

### 6.3 兼容性验收

- [ ] 不影响OpenSearch的现有功能
- [ ] 数据库迁移脚本能成功执行
- [ ] 前端无需重大改动（只需添加图片渲染逻辑）

---

## 7. 风险和限制

### 7.1 已知风险

1. **本地存储容量**：
   - 大量PDF和图片会占用磁盘空间
   - 建议定期清理已删除的文档

2. **并发安全**：
   - 多个同步任务同时写入同一文件可能冲突
   - 建议使用文件锁或任务队列

3. **Vision API限流**：
   - 20篇文档可能包含大量图片
   - 每次查询可能调用100+次Vision API
   - 建议添加重试和限流逻辑

### 7.2 未来优化

1. **缓存Vision结果**：
   - 图片描述已在同步阶段生成，无需重复调用

2. **并发读取文档**：
   - 当前串行读取20篇文档较慢
   - 可改为并发（但需控制并发数，避免限流）

3. **分页查询**：
   - Top-K设置为20可能太多
   - 可以先返回Top-5，用户可选"查看更多"

---

## 8. 迁移计划

### 8.1 数据迁移

**如果已有S3数据，需要迁移**：
1. 下载所有PDF到本地
2. 下载所有markdown和图片到本地
3. 更新数据库路径字段
4. 验证数据完整性

**迁移脚本**：
```bash
python scripts/migrate_s3_to_local.py
```

### 8.2 代码部署

1. 创建目录结构：
   ```bash
   mkdir -p data/documents/{pdfs,markdowns,text_markdowns}
   mkdir -p data/cache/{conversions,temp}
   ```

2. 执行数据库迁移：
   ```bash
   alembic revision --autogenerate -m "Remove S3, add local storage"
   alembic upgrade head
   ```

3. 更新环境变量
4. 重启服务

---

## 9. 附录

### 9.1 图片描述示例

**输入图片**：柱状图

**输出**：
```xml
<figure>
<figure_type>Chart</figure_type>
<figure_description>这是一个纵向柱状图，标题为"2023年用户增长趋势"。横轴为季度（Q1-Q4），纵轴为用户数（单位：千人）。数据显示：Q1为1.0千人，Q2增长至1.5千人，Q3达到2.3千人，Q4突破3.0千人。整体呈现加速增长态势，Q3-Q4增速尤为明显。图表使用蓝色柱体，风格简洁清晰。</figure_description>
</figure>
```

### 9.2 text_markdown示例

```markdown
# 用户增长策略

## 背景
过去一年我们的用户增长遇到瓶颈，需要制定新的增长策略。

## 数据分析

[IMAGE:_page_1_Figure_1.png]
<figure>
<figure_type>Chart</figure_type>
<figure_description>这是一个纵向柱状图，标题为"2023年用户增长趋势"...</figure_description>
</figure>

从上图可以看出，Q3-Q4增速明显加快，主要得益于以下策略：

1. 社交媒体推广
2. 推荐奖励机制
3. 产品功能优化

## 下一步计划
...
```

### 9.3 Agent看到的content示例

```python
[
    {"text": "# 用户增长策略\n\n## 背景\n过去一年..."},
    {"text": "[IMAGE: _page_1_Figure_1.png]"},
    {
        "image": {
            "format": "png",
            "source": {
                "bytes": b'\x89PNG\r\n...'
            }
        }
    },
    {"text": "从上图可以看出，Q3-Q4增速明显加快..."}
]
```

---

## 10. 总结

此次改造将ASK-PRD从依赖S3改为本地存储，同时优化了图片理解流程：

**核心优势**：
1. **简化部署**：无需配置AWS S3
2. **降低成本**：无S3存储和传输费用
3. **提升体验**：Agent能直接看到图片，理解更精准
4. **灵活调试**：本地文件便于开发和调试

**关键设计**：
1. **双markdown策略**：text版本用于向量化，原始版本用于Agent阅读
2. **图片描述标准化**：统一的`<figure>`格式，便于解析和展示
3. **流式进度反馈**：用户能实时看到"正在阅读第X篇文档"
4. **可配置召回数**：通过`MAX_RETRIEVAL_DOCS`灵活调整

**下一步**：
- 生成技术设计文档（详细实现方案）
- 生成API接口文档
- 生成数据库迁移文档
