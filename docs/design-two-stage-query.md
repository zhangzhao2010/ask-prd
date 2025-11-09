# Two-Stage查询系统设计文档

> 版本：v1.0
> 更新时间：2025-01-07
> 状态：设计完成

---

## 一、系统架构

### 1.1 整体架构图

```
用户Query
  ↓
混合检索（复用现有逻辑）
  ↓
提取Document ID列表
  ↓
┌─────────────────────────────────────────────────┐
│            Two-Stage Executor                    │
│                                                  │
│  ┌────────────────────────────────────────┐    │
│  │  Stage 1: 串行处理每个Document         │    │
│  │                                         │    │
│  │  For each Document:                    │    │
│  │    1. DocumentLoader (下载文件)        │    │
│  │    2. DocumentProcessor (分段标记)     │    │
│  │    3. BedrockModel调用 (理解文档)      │    │
│  │    4. 返回结构化结果                   │    │
│  │    5. SSE推送进度                      │    │
│  └────────────────────────────────────────┘    │
│                  ↓                              │
│  ┌────────────────────────────────────────┐    │
│  │  Stage 2: 综合答案和流式输出           │    │
│  │                                         │    │
│  │    1. 汇总所有Stage1结果               │    │
│  │    2. BedrockModel流式调用             │    │
│  │    3. ReferenceExtractor (提取引用)    │    │
│  │    4. SSE推送答案片段                  │    │
│  │    5. SSE推送引用列表                  │    │
│  └────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
  ↓
返回前端 (SSE)
```

### 1.2 核心模块

| 模块 | 职责 | 输入 | 输出 |
|------|------|------|------|
| DocumentLoader | 从S3/缓存下载文档和图片 | document_id | 本地文件路径 |
| DocumentProcessor | 文档分段、标记、构建content | Markdown文本、图片列表 | 图文混排content |
| ReferenceExtractor | 提取和格式化引用 | 答案文本、Stage1结果 | 引用列表 |
| TwoStageExecutor | 协调整个查询流程 | Query、Document列表 | 流式事件 |
| ImageService | 提供图片访问接口 | document_id、image_filename | 图片文件 |

---

## 二、数据流设计

### 2.1 Stage 1数据流

```
Document ID
  ↓
DocumentLoader
  ├─→ 检查本地缓存: /data/cache/documents/{doc_id}/content.md
  │   ├─→ 存在 → 直接返回
  │   └─→ 不存在 → 从S3下载 → 保存到本地 → 返回
  │
  └─→ 获取图片列表（从chunks表查询）
      ├─→ 检查本地缓存: /data/cache/documents/{doc_id}/img_*.png
      │   ├─→ 存在 → 直接使用
      │   └─→ 不存在 → 从S3下载 → 保存到本地
      │
      └─→ 返回: {markdown_path, image_paths[]}

DocumentProcessor
  ├─→ 读取Markdown文本
  ├─→ 分段 (split_into_paragraphs)
  ├─→ 标记段落和图片
  ├─→ 构建图文混排content
  └─→ 返回: {content[], references_map{}}

BedrockModel调用
  ├─→ 构建Prompt (Stage1模板 + content + Query)
  ├─→ 调用Bedrock API
  └─→ 返回: 结构化文档理解结果

结果存储
  ├─→ 保存到内存: stage1_results[]
  └─→ SSE推送进度: {type: "progress", current: X, total: N}
```

### 2.2 Stage 2数据流

```
汇总Stage1结果
  ├─→ 提取所有文档的理解结果
  └─→ 构建综合Prompt

BedrockModel流式调用
  ├─→ 发送Prompt
  └─→ 接收流式响应
      └─→ SSE推送: {type: "answer_delta", text: "..."}

引用提取
  ├─→ 从完整答案中提取引用标记
  ├─→ 根据标记从Stage1结果中查找内容
  ├─→ 构建引用对象列表
  └─→ SSE推送: {type: "references", data: [...]}

完成
  └─→ SSE推送: {type: "done", tokens: {...}}
```

---

## 三、核心模块详细设计

### 3.1 DocumentLoader模块

**文件位置**：`app/services/document_loader.py`

#### 3.1.1 类设计

```python
class DocumentLoader:
    """负责从S3或本地缓存加载文档内容"""

    def __init__(
        self,
        db_session: Session,
        s3_client,
        cache_dir: str = "/data/cache/documents"
    ):
        self.db = db_session
        self.s3_client = s3_client
        self.cache_dir = cache_dir

    def load_document(self, document_id: str) -> DocumentContent:
        """
        加载文档的Markdown和图片

        Returns:
            DocumentContent(
                markdown_path: str,
                markdown_text: str,
                image_paths: List[str],
                doc_id: str,
                doc_name: str
            )
        """
        pass

    def _get_markdown(self, document_id: str, s3_key: str) -> Tuple[str, str]:
        """获取Markdown文件（优先本地缓存）"""
        pass

    def _get_images(self, document_id: str) -> List[str]:
        """获取所有图片文件（优先本地缓存）"""
        pass

    def _download_from_s3(self, s3_key: str, local_path: str) -> None:
        """从S3下载文件到本地"""
        pass
```

#### 3.1.2 数据结构

```python
from dataclasses import dataclass
from typing import List

@dataclass
class DocumentContent:
    """文档内容"""
    doc_id: str              # 完整document_id
    doc_name: str            # 文档名称
    markdown_path: str       # Markdown本地路径
    markdown_text: str       # Markdown文本内容
    image_paths: List[str]   # 图片本地路径列表
```

#### 3.1.3 关键逻辑

**Markdown下载逻辑**：

```python
def _get_markdown(self, document_id: str, s3_key: str) -> Tuple[str, str]:
    """
    获取Markdown文件

    Returns:
        (本地路径, 文本内容)
    """
    # 1. 构建本地路径
    local_path = os.path.join(
        self.cache_dir,
        document_id,
        "content.md"
    )

    # 2. 检查本地缓存
    if os.path.exists(local_path):
        with open(local_path, 'r', encoding='utf-8') as f:
            text = f.read()
        return local_path, text

    # 3. 从S3下载
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    self.s3_client.download_file(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Filename=local_path
    )

    # 4. 读取内容
    with open(local_path, 'r', encoding='utf-8') as f:
        text = f.read()

    return local_path, text
```

**图片下载逻辑**：

```python
def _get_images(self, document_id: str) -> List[str]:
    """
    获取文档的所有图片

    Returns:
        图片本地路径列表
    """
    # 1. 从数据库查询该文档的所有图片chunks
    image_chunks = (
        self.db.query(Chunk)
        .filter(
            Chunk.document_id == document_id,
            Chunk.chunk_type == 'image'
        )
        .order_by(Chunk.chunk_index)
        .all()
    )

    image_paths = []

    # 2. 逐个下载图片
    for chunk in image_chunks:
        # 构建本地路径（与Markdown同目录）
        # 假设chunk.image_s3_key = "prds/.../converted/doc-xxx/images/img_001.png"
        image_filename = os.path.basename(chunk.image_s3_key)
        local_path = os.path.join(
            self.cache_dir,
            document_id,
            image_filename
        )

        # 检查本地缓存
        if not os.path.exists(local_path):
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.s3_client.download_file(
                Bucket=S3_BUCKET,
                Key=chunk.image_s3_key,
                Filename=local_path
            )

        image_paths.append(local_path)

    return image_paths
```

### 3.2 DocumentProcessor模块

**文件位置**：`app/services/document_processor.py`

#### 3.2.1 类设计

```python
class DocumentProcessor:
    """负责文档分段、标记和构建图文混排content"""

    def process(
        self,
        document_content: DocumentContent
    ) -> ProcessedDocument:
        """
        处理文档：分段、标记、构建content

        Returns:
            ProcessedDocument(
                doc_id: str,
                doc_short_id: str,
                content: List[Dict],  # Bedrock API格式
                references_map: Dict[str, str]  # {ref_id: 原文内容}
            )
        """
        pass

    def split_into_paragraphs(self, text: str) -> List[str]:
        """智能分段（参考demo）"""
        pass

    def build_content(
        self,
        markdown_text: str,
        image_paths: List[str],
        doc_short_id: str
    ) -> Tuple[List[Dict], Dict[str, str]]:
        """构建图文混排content"""
        pass
```

#### 3.2.2 数据结构

```python
@dataclass
class ProcessedDocument:
    """处理后的文档"""
    doc_id: str                      # 完整document_id
    doc_name: str                    # 文档名称
    doc_short_id: str                # 短ID（前8位）
    content: List[Dict]              # Bedrock API格式的content
    references_map: Dict[str, str]   # {ref_id: 原文内容或图片路径}
```

#### 3.2.3 关键逻辑

**段落分割**（复用demo逻辑）：

```python
def split_into_paragraphs(self, text: str) -> List[str]:
    """
    智能分段：按空行和标题分割
    """
    paragraphs = []

    # 按空行分割
    blocks = re.split(r'\n\s*\n', text)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.split('\n')
        current_para = []

        for line in lines:
            # 检测标题行
            if re.match(r'^#{1,6}\s+', line):
                # 保存之前的段落
                if current_para:
                    paragraphs.append('\n'.join(current_para))
                    current_para = []
                # 标题单独成段
                paragraphs.append(line)
            else:
                current_para.append(line)

        # 保存最后的段落
        if current_para:
            paragraphs.append('\n'.join(current_para))

    return [p for p in paragraphs if p.strip()]
```

**构建图文混排content**：

```python
def build_content(
    self,
    markdown_text: str,
    image_paths: List[str],
    doc_short_id: str
) -> Tuple[List[Dict], Dict[str, str]]:
    """
    构建图文混排content

    Returns:
        (content列表, references映射表)
    """
    content = []
    references_map = {}

    # 1. 解析Markdown中的图片位置
    image_pattern = r'!\[\]\(([^)]+\.(?:jpeg|jpg|png|gif|webp))\)'
    images_in_md = []

    for match in re.finditer(image_pattern, markdown_text):
        img_filename = os.path.basename(match.group(1))
        position = match.start()
        images_in_md.append((position, img_filename))

    # 2. 按位置交替插入文本和图片
    para_counter = 1
    img_counter = 1
    last_pos = 0

    for pos, img_filename in images_in_md:
        # 处理图片前的文本
        text_before = markdown_text[last_pos:pos].strip()
        if text_before:
            paragraphs = self.split_into_paragraphs(text_before)

            for para in paragraphs:
                if not para.strip():
                    continue

                # 生成段落标记
                para_id = f"DOC-{doc_short_id}-PARA-{para_counter}"
                labeled_para = f"[{para_id}]\n{para}"

                # 保存到映射表
                references_map[para_id] = para

                # 添加到content
                content.append({"text": labeled_para})

                para_counter += 1

        # 处理图片
        # 查找对应的本地图片路径
        matching_path = None
        for img_path in image_paths:
            if os.path.basename(img_path) == img_filename:
                matching_path = img_path
                break

        if matching_path:
            # 生成图片标记
            img_id = f"DOC-{doc_short_id}-IMAGE-{img_counter}"
            img_label = f"[{img_id}: {img_filename}]"

            # 保存到映射表（存储相对路径，供前端访问）
            references_map[img_id] = img_filename

            # 添加标记文本
            content.append({"text": img_label})

            # 添加图片
            with open(matching_path, 'rb') as f:
                img_bytes = f.read()

            # 判断图片格式
            img_format = img_filename.split('.')[-1].lower()
            if img_format == 'jpg':
                img_format = 'jpeg'

            content.append({
                "image": {
                    "format": img_format,
                    "source": {
                        "bytes": img_bytes
                    }
                }
            })

            img_counter += 1

        # 更新位置
        last_pos = pos + len(f"![]({img_filename})")

    # 处理最后剩余的文本
    text_after = markdown_text[last_pos:].strip()
    if text_after:
        paragraphs = self.split_into_paragraphs(text_after)

        for para in paragraphs:
            if not para.strip():
                continue

            para_id = f"DOC-{doc_short_id}-PARA-{para_counter}"
            labeled_para = f"[{para_id}]\n{para}"

            references_map[para_id] = para
            content.append({"text": labeled_para})

            para_counter += 1

    return content, references_map
```

### 3.3 ReferenceExtractor模块

**文件位置**：`app/services/reference_extractor.py`

#### 3.3.1 类设计

```python
class ReferenceExtractor:
    """负责从答案中提取和格式化引用"""

    def extract_references(
        self,
        answer_text: str,
        stage1_results: List[Stage1Result]
    ) -> List[Reference]:
        """
        从答案中提取引用标记，并构建引用对象

        Args:
            answer_text: Stage 2生成的完整答案
            stage1_results: 所有Stage 1的结果

        Returns:
            引用对象列表
        """
        pass

    def _extract_ref_ids(self, text: str) -> List[str]:
        """从文本中提取所有引用标记"""
        pass

    def _build_reference(
        self,
        ref_id: str,
        stage1_results: List[Stage1Result]
    ) -> Optional[Reference]:
        """根据ref_id构建引用对象"""
        pass
```

#### 3.3.2 数据结构

```python
@dataclass
class Reference:
    """引用对象"""
    ref_id: str              # 例如: "DOC-abc12345-PARA-5"
    doc_id: str              # 完整document_id
    doc_name: str            # 文档名称
    chunk_type: str          # "text" 或 "image"
    content: Optional[str]   # 文本chunk的内容
    image_url: Optional[str] # 图片chunk的URL
```

#### 3.3.3 关键逻辑

**提取引用标记**：

```python
def _extract_ref_ids(self, text: str) -> List[str]:
    """
    从文本中提取所有引用标记

    Returns:
        去重后的引用标记列表
    """
    # 正则匹配 [DOC-xxxxxxxx-PARA-Y] 或 [DOC-xxxxxxxx-IMAGE-Z]
    pattern = r'\[(DOC-[a-f0-9]{8}-(PARA|IMAGE)-\d+)\]'
    matches = re.findall(pattern, text)

    # 提取第一个捕获组（ref_id）
    ref_ids = [match[0] for match in matches]

    # 去重并保持顺序
    seen = set()
    unique_refs = []
    for ref_id in ref_ids:
        if ref_id not in seen:
            seen.add(ref_id)
            unique_refs.append(ref_id)

    return unique_refs
```

**构建引用对象**：

```python
def _build_reference(
    self,
    ref_id: str,
    stage1_results: List[Stage1Result]
) -> Optional[Reference]:
    """
    根据ref_id构建引用对象

    Args:
        ref_id: 例如 "DOC-abc12345-PARA-5"
        stage1_results: 所有Stage 1的结果

    Returns:
        Reference对象，如果找不到则返回None
    """
    # 1. 解析ref_id，提取doc_short_id
    # ref_id格式: DOC-{short_id}-{TYPE}-{number}
    parts = ref_id.split('-')
    if len(parts) < 4:
        return None

    doc_short_id = parts[1]  # 例如: "abc12345"
    chunk_type_raw = parts[2]  # "PARA" 或 "IMAGE"
    chunk_type = "text" if chunk_type_raw == "PARA" else "image"

    # 2. 从stage1_results中查找对应的文档
    target_result = None
    for result in stage1_results:
        if result.doc_short_id == doc_short_id:
            target_result = result
            break

    if not target_result:
        return None

    # 3. 从references_map中查找内容
    if ref_id not in target_result.references_map:
        return None

    content_or_path = target_result.references_map[ref_id]

    # 4. 构建引用对象
    if chunk_type == "text":
        return Reference(
            ref_id=ref_id,
            doc_id=target_result.doc_id,
            doc_name=target_result.doc_name,
            chunk_type="text",
            content=content_or_path,
            image_url=None
        )
    else:
        # 图片类型，content_or_path是图片文件名
        image_url = f"/api/v1/documents/{target_result.doc_id}/images/{content_or_path}"
        return Reference(
            ref_id=ref_id,
            doc_id=target_result.doc_id,
            doc_name=target_result.doc_name,
            chunk_type="image",
            content=None,
            image_url=image_url
        )
```

### 3.4 TwoStageExecutor模块

**文件位置**：`app/services/agentic_robot/two_stage_executor.py`

#### 3.4.1 类设计

```python
class TwoStageExecutor:
    """Two-Stage查询执行器"""

    def __init__(
        self,
        db_session: Session,
        s3_client,
        bedrock_model: BedrockModel
    ):
        self.db = db_session
        self.s3_client = s3_client
        self.bedrock_model = bedrock_model

        # 初始化子模块
        self.doc_loader = DocumentLoader(db_session, s3_client)
        self.doc_processor = DocumentProcessor()
        self.ref_extractor = ReferenceExtractor()

    async def execute_streaming(
        self,
        query: str,
        document_ids: List[str]
    ) -> AsyncGenerator[Dict, None]:
        """
        执行Two-Stage查询，流式返回结果

        Yields:
            SSE事件字典
        """
        pass

    async def _stage1_process_documents(
        self,
        query: str,
        document_ids: List[str]
    ) -> List[Stage1Result]:
        """Stage 1: 串行处理每个文档"""
        pass

    async def _stage2_synthesize_streaming(
        self,
        query: str,
        stage1_results: List[Stage1Result]
    ) -> AsyncGenerator[str, None]:
        """Stage 2: 综合答案并流式输出"""
        pass
```

#### 3.4.2 数据结构

```python
@dataclass
class Stage1Result:
    """Stage 1的处理结果"""
    doc_id: str
    doc_name: str
    doc_short_id: str
    response_text: str         # 大模型返回的结构化文本
    references_map: Dict[str, str]  # {ref_id: 内容}
```

#### 3.4.3 核心流程

**完整执行流程**：

```python
async def execute_streaming(
    self,
    query: str,
    document_ids: List[str]
) -> AsyncGenerator[Dict, None]:
    """
    执行Two-Stage查询

    Yields:
        SSE事件：
        - {"type": "progress", "data": {...}}
        - {"type": "answer_delta", "data": {"text": "..."}}
        - {"type": "references", "data": [...]}
        - {"type": "done", "data": {"tokens": {...}}}
        - {"type": "error", "data": {"message": "..."}}
    """
    try:
        # Stage 1: 处理所有文档
        stage1_results = []

        for idx, doc_id in enumerate(document_ids, 1):
            # 推送进度
            doc = self.db.query(Document).filter(Document.id == doc_id).first()
            yield {
                "type": "progress",
                "data": {
                    "current": idx,
                    "total": len(document_ids),
                    "doc_name": doc.filename if doc else "Unknown"
                }
            }

            # 处理单个文档
            try:
                result = await self._process_single_document(query, doc_id)
                stage1_results.append(result)
            except Exception as e:
                logger.error(f"Failed to process document {doc_id}", exc_info=True)
                # 继续处理其他文档

        if not stage1_results:
            yield {
                "type": "error",
                "data": {"message": "所有文档处理失败"}
            }
            return

        # Stage 2: 综合答案（流式）
        full_answer = ""
        async for text_chunk in self._stage2_synthesize_streaming(query, stage1_results):
            full_answer += text_chunk
            yield {
                "type": "answer_delta",
                "data": {"text": text_chunk}
            }

        # 提取引用
        references = self.ref_extractor.extract_references(full_answer, stage1_results)

        yield {
            "type": "references",
            "data": [asdict(ref) for ref in references]
        }

        # 完成
        yield {
            "type": "done",
            "data": {
                "tokens": {
                    # TODO: 收集Token统计
                }
            }
        }

    except Exception as e:
        logger.error("Query execution failed", exc_info=True)
        yield {
            "type": "error",
            "data": {"message": str(e)}
        }
```

**Stage 1处理单个文档**：

```python
async def _process_single_document(
    self,
    query: str,
    document_id: str
) -> Stage1Result:
    """
    处理单个文档

    Returns:
        Stage1Result
    """
    # 1. 加载文档
    doc_content = self.doc_loader.load_document(document_id)

    # 2. 处理文档（分段、标记）
    processed_doc = self.doc_processor.process(doc_content)

    # 3. 构建Stage 1 Prompt
    prompt = self._build_stage1_prompt(query, processed_doc)

    # 4. 调用Bedrock（非流式）
    response = await self._call_bedrock_stage1(prompt)

    # 5. 返回结果
    return Stage1Result(
        doc_id=processed_doc.doc_id,
        doc_name=processed_doc.doc_name,
        doc_short_id=processed_doc.doc_short_id,
        response_text=response,
        references_map=processed_doc.references_map
    )
```

**Stage 2综合答案**：

```python
async def _stage2_synthesize_streaming(
    self,
    query: str,
    stage1_results: List[Stage1Result]
) -> AsyncGenerator[str, None]:
    """
    Stage 2: 综合所有文档的理解结果，流式生成答案

    Yields:
        答案文本片段
    """
    # 1. 构建Stage 2 Prompt
    prompt = self._build_stage2_prompt(query, stage1_results)

    # 2. 使用Strands BedrockModel的流式API
    # 假设bedrock_model是一个支持流式的Strands Model实例
    async for chunk in self.bedrock_model.stream_async(prompt):
        if hasattr(chunk, 'text'):
            yield chunk.text
        elif isinstance(chunk, dict) and 'text' in chunk:
            yield chunk['text']
```

### 3.5 Prompt模板设计

#### 3.5.1 Stage 1 Prompt

```python
STAGE1_PROMPT_TEMPLATE = """以下是一份产品文档的完整内容，包含文字和图片。
文档中的每个段落都有标记 [DOC-{doc_short_id}-PARA-X]，每张图片都有标记 [DOC-{doc_short_id}-IMAGE-X]。

请仔细阅读文档（包括图片中的信息），然后按照以下格式回复：

## 文档结构
[简要描述文档的主题、版本、日期等元信息，1-2句话]
[列出文档的主要分块，每个分块一行，格式：- [DOC-xxx-PARA-X] 分块主题]

## query的回复
[基于本文档内容回答用户问题，务必在相关内容后标注引用来源，例如：根据[DOC-xxx-PARA-5]的描述...]

## 引用
[列出所有引用的段落和图片，每个引用占一行：]
[DOC-xxx-PARA-X] 段落完整内容...
[DOC-xxx-IMAGE-X] 图片文件名

用户问题：{query}
"""
```

#### 3.5.2 Stage 2 Prompt

```python
STAGE2_PROMPT_TEMPLATE = """我已经让{doc_count}个助手分别阅读了相关文档，并基于这些文档回答了用户的问题。

以下是每个助手的回复：

{all_stage1_responses}

现在请你综合这些回复，给出一个完整、准确、结构清晰的最终答案。

要求：
1. 如果多个文档的回复有冲突，请指出差异并说明可能的原因
2. 如果多个文档的回复互补，请整合成完整答案
3. 务必保持引用标记（[DOC-xxx-PARA-X]或[DOC-xxx-IMAGE-X]），便于用户追溯来源
4. 答案要自然流畅，不要简单罗列
5. 使用Markdown格式组织答案

用户问题：{query}
"""
```

---

## 四、API接口设计

### 4.1 查询接口（修改现有接口）

**路径**：`POST /api/v1/query`

**请求体**：

```json
{
  "kb_id": "uuid",
  "query": "JOIN的核心功能是什么？"
}
```

**响应**：Server-Sent Events (SSE)

**SSE事件类型**：

1. **progress事件**（Stage 1处理进度）

```
event: progress
data: {"current": 1, "total": 3, "doc_name": "产品需求v1.md"}
```

2. **answer_delta事件**（Stage 2流式答案）

```
event: answer_delta
data: {"text": "根据"}
```

3. **references事件**（引用列表）

```
event: references
data: [
  {
    "ref_id": "DOC-abc12345-PARA-5",
    "doc_id": "abc12345-1234-1234-1234-123456789012",
    "doc_name": "产品需求v1.md",
    "chunk_type": "text",
    "content": "JOIN是一款专为年轻人设计的社交App...",
    "image_url": null
  },
  {
    "ref_id": "DOC-abc12345-IMAGE-2",
    "doc_id": "abc12345-1234-1234-1234-123456789012",
    "doc_name": "产品需求v1.md",
    "chunk_type": "image",
    "content": null,
    "image_url": "/api/v1/documents/abc12345.../images/img_002.png"
  }
]
```

4. **done事件**（完成）

```
event: done
data: {
  "tokens": {
    "prompt_tokens": 15000,
    "completion_tokens": 800,
    "total_tokens": 15800
  }
}
```

5. **error事件**（错误）

```
event: error
data: {"message": "处理失败: ..."}
```

### 4.2 图片服务接口（新增）

**路径**：`GET /api/v1/documents/{document_id}/images/{image_filename}`

**响应**：图片二进制数据

**Headers**：
- Content-Type: image/png | image/jpeg | image/gif | image/webp
- Cache-Control: public, max-age=86400

**实现逻辑**：

```python
@router.get("/{document_id}/images/{image_filename}")
async def get_document_image(
    document_id: str,
    image_filename: str,
    db: Session = Depends(get_db)
):
    """
    获取文档的图片（从本地缓存提供）
    """
    # 1. 构建本地路径
    local_path = Path(f"/data/cache/documents/{document_id}/{image_filename}")

    # 2. 检查文件是否存在
    if not local_path.exists():
        # 尝试从S3下载
        # TODO: 实现从S3下载逻辑
        raise HTTPException(404, "Image not found")

    # 3. 判断Content-Type
    ext = image_filename.split('.')[-1].lower()
    content_type_map = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'webp': 'image/webp'
    }
    content_type = content_type_map.get(ext, 'application/octet-stream')

    # 4. 返回图片
    return FileResponse(
        local_path,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"}
    )
```

---

## 五、前端集成

### 5.1 SSE事件监听

```typescript
// 前端监听SSE事件
const eventSource = new EventSource(`/api/v1/query?kb_id=${kbId}&query=${query}`);

let currentAnswer = "";
let references: Reference[] = [];

eventSource.addEventListener('progress', (event) => {
  const data = JSON.parse(event.data);
  setProgress(data);  // 显示进度：正在处理文档 1/3
});

eventSource.addEventListener('answer_delta', (event) => {
  const data = JSON.parse(event.data);
  currentAnswer += data.text;
  setAnswer(currentAnswer);  // 流式更新答案
});

eventSource.addEventListener('references', (event) => {
  references = JSON.parse(event.data);
  setReferences(references);  // 显示引用列表
});

eventSource.addEventListener('done', (event) => {
  const data = JSON.parse(event.data);
  setTokens(data.tokens);
  eventSource.close();
});

eventSource.addEventListener('error', (event) => {
  const data = JSON.parse(event.data);
  showError(data.message);
  eventSource.close();
});
```

### 5.2 引用展示

```tsx
// 引用列表组件
function ReferenceList({ references }: { references: Reference[] }) {
  return (
    <div className="references">
      <h3>引用来源</h3>
      {references.map((ref) => (
        <div key={ref.ref_id} className="reference-item">
          <span className="ref-id">[{ref.ref_id}]</span>
          <span className="doc-name">{ref.doc_name}</span>

          {ref.chunk_type === 'text' && (
            <p className="content">{ref.content}</p>
          )}

          {ref.chunk_type === 'image' && (
            <img src={ref.image_url} alt={ref.ref_id} />
          )}
        </div>
      ))}
    </div>
  );
}
```

---

## 六、错误处理

### 6.1 文档下载失败

**场景**：S3文件不存在或网络问题

**处理**：
- 记录错误日志
- 跳过该Document，继续处理其他Documents
- 在最终答案中说明"部分文档无法访问"

### 6.2 Stage 1处理失败

**场景**：Bedrock API调用失败或超时

**处理**：
- 记录错误日志
- 跳过该Document
- 至少保证有一个Document成功，否则返回error事件

### 6.3 Stage 2处理失败

**场景**：Bedrock API调用失败或超时

**处理**：
- 返回error事件
- 前端显示错误提示：""综合答案生成失败，请重试"

---

## 七、性能优化建议

### 7.1 短期优化（当前版本不实现）

- 文档下载并发（多个Documents同时下载）
- Markdown分段结果缓存（相同Document不重复处理）

### 7.2 中期优化（后续版本）

- Stage 1改为并发处理（使用asyncio + Semaphore）
- 引入Reranker减少需要处理的Documents数量
- 图片压缩（减少传输给Bedrock的数据量）

---

## 八、测试计划

### 8.1 单元测试

- DocumentLoader测试（模拟S3下载）
- DocumentProcessor测试（分段逻辑）
- ReferenceExtractor测试（引用提取）

### 8.2 集成测试

- 完整Two-Stage流程测试
- SSE事件推送测试
- 图片服务接口测试

### 8.3 端到端测试

- 单个Document查询
- 多个Documents查询
- 跨文档查询（演进历史类问题）
- 图片引用查询

---

