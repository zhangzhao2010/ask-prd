# 技术设计文档：本地化存储改造

## 1. 架构变更概览

### 1.1 变更范围

**移除组件**：
- S3Client：所有S3相关调用
- 知识库创建时的S3配置验证

**新增组件**：
- 本地文件管理模块
- 图片代理API（`/api/v1/documents/{doc_id}/images/{image_name}`）

**改造组件**：
- ConversionService：输出目录改为本地
- DocumentLoader：从本地读取而非S3
- TwoStageExecutor：构建图文混排content时读取本地图片
- ChunkingService：处理带图片描述的text_markdown

### 1.2 数据流变化

**原有流程**：
```
PDF上传 → S3 → Marker转换 → S3 → 向量化 → OpenSearch
                                ↓
                            本地缓存（LRU）
```

**新流程**：
```
PDF上传 → 本地pdfs/ → Marker转换 → 本地markdowns/ → 图片描述生成 → 本地text_markdowns/ → 向量化 → OpenSearch
```

## 2. 目录结构设计

```
data/
├── documents/
│   ├── pdfs/                      # 原始PDF存储
│   │   └── {document_id}.pdf      # 命名规则：UUID.pdf
│   ├── markdowns/                 # Marker转换结果（原始版）
│   │   └── {document_id}/
│   │       ├── content.md         # 含图片引用 ![](xxx.png)
│   │       ├── _page_1_Figure_1.png
│   │       └── _page_2_Chart_5.jpeg
│   └── text_markdowns/            # 纯文本版（含图片描述）
│       └── {document_id}.md       # 图片替换为<figure>描述
├── cache/
│   ├── conversions/               # Marker临时目录
│   └── temp/
└── ask-prd.db                     # SQLite数据库
```

**路径规则**：
- PDF路径：`{data_dir}/documents/pdfs/{document_id}.pdf`
- 原始Markdown：`{data_dir}/documents/markdowns/{document_id}/content.md`
- 图片文件：`{data_dir}/documents/markdowns/{document_id}/*.png`（与markdown同目录）
- Text Markdown：`{data_dir}/documents/text_markdowns/{document_id}.md`

## 3. 数据库Schema变更

### 3.1 KnowledgeBase表

**移除字段**：
```sql
-- 删除
s3_bucket VARCHAR
s3_prefix VARCHAR
```

**新增字段**：
```sql
-- 新增
local_storage_path VARCHAR  -- 例如: data/knowledge_bases/{kb_id}/
```

### 3.2 Document表

**移除字段**：
```sql
-- 删除
s3_key VARCHAR             -- 原始PDF的S3路径
s3_key_markdown VARCHAR    -- Markdown的S3路径
```

**新增字段**：
```sql
-- 新增
local_pdf_path VARCHAR              -- data/documents/pdfs/{document_id}.pdf
local_markdown_path VARCHAR         -- data/documents/markdowns/{document_id}/content.md
local_text_markdown_path VARCHAR    -- data/documents/text_markdowns/{document_id}.md
```

### 3.3 Chunk表

**字段保持不变，但语义调整**：
- `image_filename` 和 `image_description` 字段保留但不再使用
- 图片描述已融入text chunk的content中

## 4. 核心模块设计

### 4.1 ConversionService改造

**改造点1：输出目录改为本地**

```python
# 原代码
output_dir = Path(settings.cache_dir) / "conversions" / document_id

# 改为
output_dir = Path(settings.data_dir) / "documents" / "markdowns" / document_id
```

**改造点2：Marker输出配置（图片与markdown同目录）**

确保Marker转换时图片直接输出到与content.md同级目录：
```python
# _process_images方法需要调整
@staticmethod
def _process_images(
    images_dict: Dict[str, Any],
    output_dir: Path,
    document_id: str
) -> List[Dict]:
    """处理图片，保存到与markdown同级目录"""
    images_info = []

    # 注意：不要创建images/子目录
    # 图片直接保存到output_dir下
    for idx, (original_filename, pil_image) in enumerate(images_dict.items()):
        img_filename = original_filename
        img_path = output_dir / img_filename  # 直接在output_dir下

        pil_image.save(img_path)

        images_info.append({
            "filename": img_filename,
            "path": str(img_path),
            "index": idx,
            "description": None
        })

    return images_info
```

**改造点3：新增图片描述生成和替换（带上下文）**

新增方法：
```python
@staticmethod
def generate_and_replace_images(
    markdown_content: str,
    doc_dir: str,
    document_id: str
) -> str:
    """
    生成图片描述并替换markdown中的图片引用（带上下文）

    Returns:
        替换后的markdown文本
    """
    # 1. 解析markdown为内容序列
    content_sequence = ConversionService._parse_markdown_content(
        markdown_content, doc_dir
    )

    # 2. 按顺序生成图片描述（带上下文）
    ConversionService._generate_descriptions_with_context(content_sequence)

    # 3. 替换markdown中的图片引用
    def replace_image(match):
        img_ref = match.group(1)  # xxx.png
        img_filename = os.path.basename(img_ref)

        # 从content_sequence中查找图片信息
        img_item = next(
            (item for item in content_sequence
             if item["type"] == "image" and item["filename"] == img_filename),
            None
        )

        if not img_item or not img_item.get("description"):
            return match.group(0)

        # 构建替换文本
        return (
            f"\n[IMAGE:{img_ref}]\n"
            f"<figure>\n"
            f"<figure_type>{img_item['figure_type']}</figure_type>\n"
            f"<figure_description>{img_item['description']}</figure_description>\n"
            f"</figure>\n"
        )

    pattern = r'!\[\]\(([^)]+\.(?:jpeg|jpg|png|gif|webp))\)'
    replaced = re.sub(pattern, replace_image, markdown_content)

    return replaced

@staticmethod
def _parse_markdown_content(markdown_text: str, doc_dir: str) -> List[Dict]:
    """解析markdown为内容序列（见6.1节）"""
    # 实现见上文

@staticmethod
def _generate_descriptions_with_context(content_sequence: List[Dict]) -> None:
    """按顺序生成图片描述（见6.1节）"""
    # 实现见上文
```

### 4.2 DocumentLoader改造

**改造点：移除S3下载逻辑**

```python
def load_document(self, document_id: str) -> DocumentContent:
    # 1. 查询数据库
    doc = self.db.query(Document).filter(Document.id == document_id).first()

    # 2. 直接从本地读取markdown
    markdown_path = doc.local_markdown_path
    # 例如: data/documents/markdowns/{document_id}/content.md

    with open(markdown_path, 'r', encoding='utf-8') as f:
        markdown_text = f.read()

    # 3. 获取图片列表（扫描markdown同级目录）
    doc_dir = os.path.dirname(markdown_path)
    image_paths = glob.glob(f"{doc_dir}/*.png") + glob.glob(f"{doc_dir}/*.jpeg") + glob.glob(f"{doc_dir}/*.jpg")

    return DocumentContent(
        doc_id=document_id,
        doc_name=doc.filename,
        markdown_path=markdown_path,
        markdown_text=markdown_text,
        image_paths=image_paths
    )
```

### 4.3 TwoStageExecutor改造

**改造点：读取本地图片构建图文混排content**

DocumentProcessor的 `build_content` 方法无需改动，因为它已经从本地路径读取图片bytes。

确认现有逻辑：
```python
# document_processor.py 第206-222行
with open(matching_path, 'rb') as f:
    img_bytes = f.read()

content.append({
    "image": {
        "format": img_format,
        "source": {"bytes": img_bytes}
    }
})
```

此逻辑已经是从本地读取，无需改动。

### 4.4 新增ImageAPI

**文件位置**：`backend/app/api/v1/documents.py`（新建）

```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os

router = APIRouter(prefix="/documents", tags=["documents"])

@router.get("/{doc_id}/images/{image_name}")
async def get_document_image(doc_id: str, image_name: str):
    """
    获取文档中的图片

    Args:
        doc_id: 文档ID
        image_name: 图片文件名

    Returns:
        图片文件
    """
    from app.core.config import settings

    image_path = os.path.join(
        settings.data_dir,
        "documents",
        "markdowns",
        doc_id,
        image_name
    )

    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")

    # 判断Content-Type
    ext = image_name.split('.')[-1].lower()
    media_type = f"image/{ext}" if ext != "jpg" else "image/jpeg"

    return FileResponse(image_path, media_type=media_type)
```

## 5. 关键流程设计

### 5.1 文档上传流程

```
POST /api/v1/knowledge-bases/{kb_id}/documents
```

**步骤**：
1. 接收multipart/form-data文件
2. 生成document_id（UUID）
3. 保存PDF到：`data/documents/pdfs/{document_id}.pdf`
4. 创建Document记录：
   ```python
   doc = Document(
       id=document_id,
       kb_id=kb_id,
       filename=file.filename,
       local_pdf_path=f"data/documents/pdfs/{document_id}.pdf",
       file_size=file_size,
       status="uploaded"
   )
   ```
5. 返回document_id

### 5.2 数据同步流程

```
POST /api/v1/knowledge-bases/{kb_id}/sync
{"document_ids": ["doc1", "doc2"]}
```

**完整流程（7步）**：

```python
async def sync_documents(kb_id: str, document_ids: List[str]):
    for doc_id in document_ids:
        # Step 1: Marker转换
        pdf_path = f"data/documents/pdfs/{doc_id}.pdf"
        output_dir = f"data/documents/markdowns/{doc_id}/"
        markdown_content, images_info = marker_convert(pdf_path, output_dir)
        # 输出: output_dir/content.md + output_dir/*.png（图片与markdown同目录）

        # Step 2-3: 生成图片描述（带上下文）并替换
        text_markdown = ConversionService.generate_and_replace_images(
            markdown_content=markdown_content,
            doc_dir=output_dir,
            document_id=doc_id
        )
        # 内部会：
        # 1. 解析markdown为内容序列
        # 2. 按顺序生成图片描述（传入上下文）
        # 3. 替换图片引用为描述

        # Step 4: 保存text_markdown
        text_md_path = f"data/documents/text_markdowns/{doc_id}.md"
        save_file(text_md_path, text_markdown)

        # Step 5: 文本分块
        chunks = chunk_text(text_markdown)

        # Step 6: 向量化
        embeddings = embed_chunks(chunks)

        # Step 7: 存储
        opensearch.index(chunks, embeddings)
        db.bulk_insert(chunks)
```

### 5.3 智能问答流程

```
POST /api/v1/query
{"kb_id": "xxx", "query": "用户增长策略", "top_k": 20}
```

**4个阶段**：

```python
async def query_streaming(kb_id, query, top_k):
    # 阶段1: 混合召回
    document_ids = hybrid_search(kb_id, query, top_k)
    # 返回: ["doc1", "doc2", ..., "doc20"]

    # 阶段2-3: 串行读取文档并问答
    stage1_results = []
    for idx, doc_id in enumerate(document_ids, 1):
        # 推送进度
        yield {"type": "progress", "data": {"current": idx, "total": len(document_ids)}}

        # 读取原始markdown
        markdown_path = f"data/documents/markdowns/{doc_id}/content.md"
        markdown_text = read_file(markdown_path)
        doc_dir = f"data/documents/markdowns/{doc_id}/"
        image_paths = glob_images(doc_dir)  # 获取同目录下的所有图片文件

        # 构建图文混排content
        content = build_multimodal_content(markdown_text, image_paths)

        # 调用Bedrock Vision API
        response = bedrock_converse(
            messages=[{"role": "user", "content": [prompt_text] + content}]
        )

        stage1_results.append(response)

    # 阶段4: 综合答案
    yield {"type": "status", "message": "正在生成综合答案..."}

    # 调用Bedrock流式API，直接输出Markdown
    async for event in bedrock_converse_stream(
        messages=[{"role": "user", "content": stage2_prompt}]
    ):
        if event.type == "content_block_delta":
            # 流式推送markdown片段
            yield {"type": "answer_delta", "data": {"text": event.delta.text}}

    yield {"type": "done"}
```

## 6. 代码实现细节

### 6.1 图片描述生成（带上下文）

**核心改进**：解析markdown结构，按顺序生成带上下文的图片描述

**步骤1：解析markdown为内容序列**
```python
def parse_markdown_content(markdown_text: str, doc_dir: str) -> List[Dict]:
    """
    解析markdown为文本块和图片块的序列

    Returns:
        [
            {"type": "text", "content": "段落1..."},
            {"type": "image", "filename": "img1.png", "path": "/path/to/img1.png"},
            {"type": "text", "content": "段落2..."},
            ...
        ]
    """
    content_sequence = []

    # 按图片引用分割markdown
    pattern = r'!\[\]\(([^)]+\.(?:jpeg|jpg|png|gif|webp))\)'
    parts = re.split(pattern, markdown_text)

    for i, part in enumerate(parts):
        if i % 2 == 0:  # 文本部分
            if part.strip():
                content_sequence.append({
                    "type": "text",
                    "content": part.strip()
                })
        else:  # 图片文件名
            img_filename = part
            img_path = os.path.join(doc_dir, img_filename)
            content_sequence.append({
                "type": "image",
                "filename": img_filename,
                "path": img_path,
                "description": None  # 待生成
            })

    return content_sequence
```

**步骤2：按顺序生成图片描述**
```python
def generate_descriptions_with_context(content_sequence: List[Dict]) -> None:
    """
    按顺序生成图片描述，传入上下文
    """
    for i, item in enumerate(content_sequence):
        if item["type"] != "image":
            continue

        # 获取上文（最多500字符）
        context_before = ""
        if i > 0:
            prev_item = content_sequence[i - 1]
            if prev_item["type"] == "text":
                context_before = prev_item["content"][-500:]
            elif prev_item["type"] == "image" and prev_item.get("description"):
                context_before = f"[上一张图片] {prev_item['description'][:200]}"

        # 获取下文（最多500字符）
        context_after = ""
        if i < len(content_sequence) - 1:
            next_item = content_sequence[i + 1]
            if next_item["type"] == "text":
                context_after = next_item["content"][:500]
            # 如果下一个是图片，不传（还没生成）

        # 调用Vision API
        description = generate_image_description_with_context(
            img_path=item["path"],
            context_before=context_before,
            context_after=context_after
        )

        item["description"] = description["description"]
        item["figure_type"] = description["figure_type"]
```

**步骤3：调用Vision API（带上下文）**
```python
def generate_image_description_with_context(
    img_path: str,
    context_before: str,
    context_after: str
) -> Dict[str, str]:
    """
    调用Bedrock Vision API，传入上下文
    """
    with open(img_path, 'rb') as f:
        img_bytes = f.read()

    img_base64 = base64.b64encode(img_bytes).decode()

    # 构建带上下文的prompt
    prompt = f"""你正在阅读一份产品文档，需要理解文档中的图片。

【上文】
{context_before if context_before else "（文档开头）"}

【当前图片】
[请分析下方图片]

【下文】
{context_after if context_after else "（文档结尾）"}

请结合上下文，详细描述这张图片的内容、类型和作用。

首先判断图片类型（Chart/Diagram/Logo/Icon/Natural Image/Screenshot/Other），
然后生成详细描述，包括：
- 图片的主要内容
- 图片在文档中的作用
- 关键信息和细节

输出格式：
<figure>
<figure_type>图片类型</figure_type>
<figure_description>详细描述...</figure_description>
</figure>
"""

    response = bedrock_client.analyze_image(
        image_base64=img_base64,
        prompt=prompt,
        max_tokens=1000,
        temperature=0.3
    )

    # 解析响应
    figure_type = extract_figure_type(response)
    description = extract_description(response)

    return {
        "figure_type": figure_type,
        "description": description
    }
```

### 6.2 Markdown替换逻辑

**核心代码**：
```python
def replace_images_with_descriptions(
    markdown_text: str,
    images_info: List[Dict]
) -> str:
    """
    替换markdown中的图片引用为描述

    Args:
        markdown_text: 原始markdown
        images_info: [{"filename": "xxx.png", "figure_type": "Chart", "description": "..."}]

    Returns:
        替换后的markdown
    """
    # 创建文件名到描述的映射
    filename_to_info = {
        os.path.basename(info["path"]): info
        for info in images_info
    }

    # 替换函数
    def replacer(match):
        img_ref = match.group(1)  # xxx.png（文件名，不含路径）
        img_filename = os.path.basename(img_ref)

        if img_filename not in filename_to_info:
            return match.group(0)  # 保持原样

        info = filename_to_info[img_filename]

        # 构建替换文本
        return (
            f"\n[IMAGE:{img_ref}]\n"
            f"<figure>\n"
            f"<figure_type>{info['figure_type']}</figure_type>\n"
            f"<figure_description>{info['description']}</figure_description>\n"
            f"</figure>\n"
        )

    # 执行替换
    pattern = r'!\[\]\(([^)]+\.(?:jpeg|jpg|png|gif|webp))\)'
    result = re.sub(pattern, replacer, markdown_text)

    return result
```

### 6.3 图文混排构建

**DocumentProcessor.build_content方法已实现，无需改动**

关键逻辑（document_processor.py:112-280）：
1. 解析markdown中的图片位置：`re.finditer(r'!\[\]\(([^)]+\.(?:jpeg|jpg|png|gif|webp))\)', markdown_text)`
2. 按位置交替插入文本和图片
3. 文本块：`{"text": "[DOC-xxx-PARA-1]\n段落内容"}`
4. 图片块：`{"text": "[DOC-xxx-IMAGE-1: filename]"}` + `{"image": {"format": "png", "source": {"bytes": ...}}}`

## 7. 配置和部署

### 7.1 环境变量配置

**backend/.env**：
```bash
# 数据存储
DATA_DIR=/home/ubuntu/ask-prd/data

# 可调参数
MAX_RETRIEVAL_DOCS=20

# Bedrock配置
AWS_REGION=us-west-2
BEDROCK_REGION=us-west-2
EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
GENERATION_MODEL_ID=global.anthropic.claude-sonnet-4-5-20250929-v1:0

# 数据库
DATABASE_PATH=/home/ubuntu/ask-prd/data/ask-prd.db
```

### 7.2 目录初始化

```bash
# 创建目录结构
mkdir -p data/documents/{pdfs,markdowns,text_markdowns}
mkdir -p data/cache/{conversions,temp}

# 设置权限
chmod -R 755 data/
```

### 7.3 数据库迁移

```bash
# 生成迁移脚本
alembic revision --autogenerate -m "Remove S3, add local storage paths"

# 执行迁移
alembic upgrade head
```

### 7.4 代码部署步骤

1. 备份数据：
   ```bash
   cp data/ask-prd.db data/ask-prd.db.backup
   ```

2. 拉取代码：
   ```bash
   git pull origin main
   ```

3. 安装依赖（如有新增）：
   ```bash
   pip install -r requirements.txt
   ```

4. 执行数据库迁移

5. 重启服务：
   ```bash
   systemctl restart ask-prd-backend
   ```

## 8. 测试计划

### 8.1 单元测试

**测试文件结构**：
```
tests/
├── test_conversion_service.py
├── test_document_loader.py
├── test_image_api.py
└── test_markdown_replace.py
```

**关键测试用例**：

1. **图片描述生成测试**：
   ```python
   def test_generate_image_description():
       img_path = "test_data/sample_chart.png"
       result = ConversionService.generate_image_description(img_path)
       assert "figure_type" in result
       assert "description" in result
       assert result["figure_type"] in ["Chart", "Diagram", "Logo", ...]
   ```

2. **Markdown替换测试**：
   ```python
   def test_replace_images_with_descriptions():
       markdown = "# Title\n![](images/test.png)\nContent"
       images_info = [{
           "path": "images/test.png",
           "figure_type": "Chart",
           "description": "Test chart"
       }]
       result = replace_images_with_descriptions(markdown, images_info)
       assert "[IMAGE:images/test.png]" in result
       assert "<figure_type>Chart</figure_type>" in result
   ```

3. **图片API测试**：
   ```python
   def test_get_document_image(client):
       response = client.get("/api/v1/documents/doc-123/images/test.png")
       assert response.status_code == 200
       assert response.headers["content-type"].startswith("image/")
   ```

### 8.2 集成测试

**完整流程测试**：
```python
async def test_full_workflow():
    # 1. 创建知识库
    kb = await create_kb("测试KB")

    # 2. 上传PDF
    doc_id = await upload_pdf(kb.id, "test.pdf")
    assert os.path.exists(f"data/documents/pdfs/{doc_id}.pdf")

    # 3. 同步数据
    await sync_documents(kb.id, [doc_id])

    # 验证文件生成
    assert os.path.exists(f"data/documents/markdowns/{doc_id}/content.md")
    assert os.path.exists(f"data/documents/text_markdowns/{doc_id}.md")

    # 验证text_markdown包含图片描述
    text_md = read_file(f"data/documents/text_markdowns/{doc_id}.md")
    assert "[IMAGE:" in text_md
    assert "<figure>" in text_md

    # 4. 查询
    results = await query(kb.id, "测试问题", top_k=5)
    assert len(results) > 0
```

### 8.3 性能测试

**测试指标**：
- 单张图片描述生成时间 < 5秒
- 10MB PDF Marker转换时间 < 60秒
- 20篇文档串行问答时间 < 180秒

**测试脚本**：
```python
import time

def test_performance():
    # 测试图片描述生成
    start = time.time()
    generate_image_description("test_chart.png")
    elapsed = time.time() - start
    assert elapsed < 5.0

    # 测试Marker转换
    start = time.time()
    marker_convert("10mb_test.pdf")
    elapsed = time.time() - start
    assert elapsed < 60.0
```

### 8.4 手动验收测试

**测试场景**：
1. 上传包含10张图片的PDF
2. 触发同步，观察日志
3. 验证所有图片都生成了描述
4. 查询问题，验证：
   - 能看到"正在阅读第X/20篇文档"进度
   - 最终答案包含图片引用
   - 点击图片引用能正确显示图片
5. 检查本地文件结构是否正确

---

**文档完成！** 下一步生成API接口文档。
