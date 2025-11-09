# Two-Stage查询系统需求文档

> 版本：v1.0
> 更新时间：2025-01-07
> 状态：需求定义

---

## 一、需求背景

### 1.1 当前系统问题

现有的Multi-Agent查询系统存在以下问题：

1. **架构复杂度过高**：使用Multi-Agent模式，涉及Sub-Agent和Main-Agent的协调，实现和维护成本高
2. **引用精度不足**：引用是基于知识库中预先分块的chunks，无法根据用户问题动态调整引用粒度
3. **文档理解不完整**：每个Sub-Agent只看到检索到的chunk片段，缺乏对完整文档的理解

### 1.2 新方案目标

基于已有的markdown文档问答demo（markdown_qa.py），改进查询系统，实现：

1. **简化架构**：从Multi-Agent改为Two-Stage单一workflow
2. **提升引用精度**：大模型在理解完整文档后，按段落动态生成引用标记
3. **完整文档理解**：每个Document以图文混排方式完整呈现给大模型
4. **灵活的chunk粒度**：引用的chunk不受知识库预分块限制，由大模型理解后自然拆解

---

## 二、核心功能需求

### 2.1 Two-Stage查询流程

#### Stage 1: 文档级理解

**输入**：
- 用户Query
- 检索到的Document列表（通过混合搜索获得）

**处理**：
- 遍历每个Document（串行处理）
- 下载Document的Markdown + 图片到本地
- 对Markdown文档进行实时分段和标记（参考demo中的`split_into_paragraphs`）
- 将图文混排内容 + Query发送给大模型
- 大模型返回结构化回复

**输出格式**：
```markdown
## 文档结构
[文档的总体描述（版本、日期、主题等），1-2句话]
[列出文档的主要分块，每个分块一行]
- [DOC-xxx-PARA-1] 分块主题
- [DOC-xxx-PARA-2] 分块主题
...

## query的回复
[基于本文档内容回答用户问题，标注引用来源]

## 引用
[列出所有引用的段落和图片]
[DOC-xxx-PARA-1] 段落完整内容...
[DOC-xxx-IMAGE-2] 图片路径
...
```

**进度推送**：
- 向前端推送文档处理进度
- 格式：`{ "type": "progress", "data": { "current": 1, "total": 3, "doc_name": "产品需求v1.md" } }`

#### Stage 2: 答案综合和流式输出

**输入**：
- 用户Query
- 所有Stage 1的结构化回复

**处理**：
- 将所有Stage 1的回复 + Query发送给大模型
- 大模型综合所有文档的信息，生成最终答案
- 提取答案中的引用标记（`[DOC-xxx-PARA-Y]` 或 `[DOC-xxx-IMAGE-Z]`）
- 根据引用标记，从Stage 1的结果中提取对应的chunk内容

**输出**：
- 流式推送答案片段（SSE）
- 推送引用列表（SSE）
- 推送Token统计（SSE）

### 2.2 文档下载和缓存

#### 2.2.1 下载逻辑

从S3或本地缓存获取Document内容：

1. **检查本地缓存**：
   - Markdown文件路径：`/data/cache/documents/{doc_id}/content.md`
   - 图片文件路径：`/data/cache/documents/{doc_id}/img_001.png`（与Markdown同目录）

2. **从S3下载**（如果本地不存在）：
   - 根据`documents.s3_key_markdown`下载Markdown
   - 根据`chunks.image_s3_key`下载图片（chunk_type='image'）
   - 下载后保存到本地缓存

3. **图片名称处理**：
   - S3路径：`s3://bucket/.../converted/doc-xxx/images/img_001.png`
   - 本地路径：`/data/cache/documents/{doc_id}/img_001.png`
   - Markdown中引用：`![](img_001.png)`

#### 2.2.2 缓存策略

- 优先使用本地缓存
- 本地文件存在则直接使用，不存在则从S3下载
- 采用LRU策略清理缓存（保留最近使用的1000个文档）

### 2.3 文档分段和标记

参考demo中的实现（`split_into_paragraphs` + `build_document_content`）：

#### 2.3.1 段落分割规则

- 按空行分割（`\n\n`）
- 标题行（`#`开头）单独成段
- 过滤空段落

#### 2.3.2 标记规则

为每个Document生成唯一的短ID（取document_id前8位）：

- 段落标记：`[DOC-{short_id}-PARA-1]`, `[DOC-{short_id}-PARA-2]`, ...
- 图片标记：`[DOC-{short_id}-IMAGE-1]`, `[DOC-{short_id}-IMAGE-2]`, ...

#### 2.3.3 图文混排构建

按Markdown中的顺序，交替插入文本段落和图片：

```python
content = [
    {"text": "[DOC-abc12345-PARA-1]\n段落内容..."},
    {"text": "[DOC-abc12345-IMAGE-1: img_001.png]"},
    {"image": {"format": "png", "source": {"bytes": image_bytes}}},
    {"text": "[DOC-abc12345-PARA-2]\n段落内容..."},
    ...
]
```

### 2.4 引用提取和返回

#### 2.4.1 引用提取

从Stage 2的答案中提取所有引用标记：

- 使用正则表达式：`\[(DOC-[a-f0-9]{8}-(PARA|IMAGE)-\d+)\]`
- 去重并保持顺序

#### 2.4.2 引用内容构建

根据引用标记，从Stage 1的结果中查找对应内容：

- 文本chunk：返回完整段落内容
- 图片chunk：返回图片访问URL

#### 2.4.3 返回格式

```typescript
interface Reference {
  ref_id: string;            // 例如: "DOC-abc12345-PARA-5"
  doc_id: string;            // 完整document_id
  doc_name: string;          // 文档名称
  chunk_type: "text" | "image";
  content?: string;          // 文本chunk的内容
  image_url?: string;        // 图片chunk的URL（例如: /api/v1/documents/{doc_id}/images/img_001.png）
}
```

### 2.5 图片服务

新增API接口，提供本地缓存图片的访问：

```
GET /api/v1/documents/{document_id}/images/{image_filename}
```

**功能**：
- 从本地缓存读取图片：`/data/cache/documents/{document_id}/{image_filename}`
- 如果本地不存在，从S3下载后返回
- 设置正确的Content-Type（image/png, image/jpeg等）
- 前端可以直接使用这个URL展示图片

---

## 三、非功能需求

### 3.1 性能要求

- **Stage 1处理**：每个Document处理时间 < 5秒
- **Stage 2处理**：流式输出首字符延迟 < 1秒
- **端到端延迟**：3个Documents的完整查询 < 20秒

### 3.2 可靠性要求

- 文档下载失败时，跳过该Document并继续处理其他Documents
- Stage 1某个Document处理失败时，不影响其他Documents
- 提供清晰的错误提示

### 3.3 可扩展性要求

- Stage 1预留并发处理能力（当前串行，未来可改并发）
- 支持处理最多10个Documents

---

## 四、用户故事

### 4.1 基本查询

**作为** 产品经理
**我想要** 询问"JOIN的核心功能是什么"
**以便** 快速了解产品定位

**验收标准**：
- 系统检索到相关文档
- 显示文档处理进度（例如：正在处理 1/3 个文档）
- 流式返回答案
- 答案中包含引用标记（例如：根据[DOC-abc12345-PARA-5]...）
- 在答案下方展示引用列表，包括段落文本和图片

### 4.2 跨文档查询

**作为** 产品经理
**我想要** 询问"登录方式的演进历史"
**以便** 了解功能迭代路径

**验收标准**：
- 系统检索到多个版本的文档
- 显示处理多个文档的进度
- 答案按时间顺序组织不同版本的信息
- 每个引用都标注来源文档

### 4.3 图片理解

**作为** 产品经理
**我想要** 询问"产品架构图的核心模块"
**以便** 理解系统设计

**验收标准**：
- 系统检索到包含架构图的文档
- 大模型能够理解图片内容
- 答案中引用图片（例如：如[DOC-abc12345-IMAGE-2]所示...）
- 引用列表中展示图片（可点击查看）

---

## 五、约束条件

### 5.1 技术约束

- 继续使用Strands Agents框架调用Bedrock Claude
- 继续使用现有的混合检索逻辑
- 不修改数据库schema
- 不修改S3存储结构

### 5.2 业务约束

- Demo阶段，暂不考虑成本优化
- 暂不支持多轮对话
- 暂不支持用户反馈机制

---

## 六、验收标准

### 6.1 功能验收

- [ ] 能够从检索结果中提取Document列表
- [ ] 能够下载Document的Markdown和图片到本地
- [ ] 能够对Markdown进行分段和标记
- [ ] 能够构建图文混排的content
- [ ] Stage 1能够返回结构化的文档理解结果
- [ ] Stage 2能够综合多个文档生成答案
- [ ] 能够提取答案中的引用标记
- [ ] 能够构建引用内容并返回前端
- [ ] 前端能够展示文本引用
- [ ] 前端能够展示图片引用
- [ ] 能够推送文档处理进度

### 6.2 性能验收

- [ ] 单个Document处理时间 < 5秒
- [ ] 流式输出延迟 < 1秒
- [ ] 3个Documents的完整查询 < 20秒

### 6.3 用户体验验收

- [ ] 进度提示清晰（例如：正在处理文档 1/3）
- [ ] 答案流式显示，无卡顿感
- [ ] 引用列表格式美观，易于理解
- [ ] 图片可以正常加载和展示
- [ ] 错误提示友好

---

## 七、后续优化方向

### 7.1 短期优化（Phase 6）

- Stage 1改为并发处理（使用asyncio + Semaphore）
- 引入缓存机制（相同Document的分段结果）
- 优化Prompt，提升引用准确性

### 7.2 中期优化（Phase 7）

- 支持多轮对话（保持上下文）
- 引入Reranker提升检索精度
- 添加用户反馈机制（引用是否有用）

### 7.3 长期优化（Phase 8+）

- 支持更多文档格式（Word, Excel）
- 支持视频和音频内容理解
- 引入知识图谱增强推理能力
