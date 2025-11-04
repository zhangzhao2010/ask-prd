# Phase 2: 知识库构建系统

> 预计工期：3周
> 目标：实现PDF上传、转换、向量化的完整流程

---

## 第1周：知识库和文档管理

### 1.1 知识库管理API (Day 1-2)

- [ ] **实现 app/services/knowledge_base.py**
  ```python
  from app.models.database import KnowledgeBase
  from app.services.opensearch import OpenSearchService
  import uuid

  class KnowledgeBaseService:
      def __init__(self, db, opensearch: OpenSearchService):
          self.db = db
          self.opensearch = opensearch

      async def create_knowledge_base(self, name, description, s3_bucket, s3_prefix):
          """创建知识库"""
          # 1. 检查名称是否重复
          # 2. 创建OpenSearch Collection和Index
          # 3. 保存到数据库
          # 4. 返回结果

      async def list_knowledge_bases(self):
          """获取知识库列表"""
          pass

      async def get_knowledge_base(self, kb_id):
          """获取知识库详情"""
          pass

      async def delete_knowledge_base(self, kb_id):
          """删除知识库"""
          # 1. 删除OpenSearch Index
          # 2. 删除S3文件（可选）
          # 3. 删除数据库记录
          pass
  ```

- [ ] **实现 app/api/v1/knowledge_bases.py**
  ```python
  from fastapi import APIRouter, Depends, HTTPException
  from app.models.schemas import KnowledgeBaseCreate, KnowledgeBaseResponse
  from app.services.knowledge_base import KnowledgeBaseService
  from app.core.database import get_db

  router = APIRouter()

  @router.post("/", response_model=KnowledgeBaseResponse, status_code=201)
  async def create_knowledge_base(
      kb: KnowledgeBaseCreate,
      db = Depends(get_db)
  ):
      """创建知识库"""
      service = KnowledgeBaseService(db)
      return await service.create_knowledge_base(
          kb.name, kb.description, kb.s3_bucket, kb.s3_prefix
      )

  @router.get("/", response_model=List[KnowledgeBaseResponse])
  async def list_knowledge_bases(db = Depends(get_db)):
      """获取知识库列表"""
      pass

  @router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
  async def get_knowledge_base(kb_id: str, db = Depends(get_db)):
      """获取知识库详情"""
      pass

  @router.delete("/{kb_id}")
  async def delete_knowledge_base(kb_id: str, db = Depends(get_db)):
      """删除知识库"""
      pass
  ```

- [ ] **测试知识库API**
  ```bash
  # 创建知识库
  curl -X POST http://localhost:8000/api/v1/knowledge-bases \
    -H "Content-Type: application/json" \
    -d '{"name": "测试知识库", "s3_bucket": "test", "s3_prefix": "test/"}'

  # 获取列表
  curl http://localhost:8000/api/v1/knowledge-bases
  ```

### 1.2 文档管理API (Day 2-3)

- [ ] **实现 app/services/document.py**
  ```python
  from app.models.database import Document
  from app.services.s3 import S3Service
  import uuid

  class DocumentService:
      def __init__(self, db, s3: S3Service):
          self.db = db
          self.s3 = s3

      async def upload_document(self, kb_id, file):
          """上传文档"""
          # 1. 验证文件格式（PDF）
          # 2. 验证文件大小（<100MB）
          # 3. 上传到S3
          # 4. 保存元数据到数据库
          # 5. 状态设为uploaded
          pass

      async def list_documents(self, kb_id, status=None, page=1, page_size=20):
          """获取文档列表"""
          pass

      async def get_document(self, doc_id):
          """获取文档详情"""
          pass

      async def delete_documents(self, kb_id, document_ids):
          """批量删除文档"""
          # 1. 删除S3文件
          # 2. 删除OpenSearch向量
          # 3. 删除数据库记录
          # 4. 删除本地缓存
          pass
  ```

- [ ] **实现 app/api/v1/documents.py**
  ```python
  from fastapi import APIRouter, UploadFile, File, Depends
  from app.services.document import DocumentService

  router = APIRouter()

  @router.post("/knowledge-bases/{kb_id}/documents/upload")
  async def upload_document(
      kb_id: str,
      file: UploadFile = File(...),
      db = Depends(get_db)
  ):
      """上传文档"""
      service = DocumentService(db)
      return await service.upload_document(kb_id, file)

  @router.get("/knowledge-bases/{kb_id}/documents")
  async def list_documents(
      kb_id: str,
      status: Optional[str] = None,
      page: int = 1,
      page_size: int = 20,
      db = Depends(get_db)
  ):
      """获取文档列表"""
      pass

  @router.delete("/knowledge-bases/{kb_id}/documents")
  async def delete_documents(
      kb_id: str,
      doc_ids: DocumentDeleteRequest,
      db = Depends(get_db)
  ):
      """批量删除文档"""
      pass
  ```

- [ ] **测试文档API**
  ```bash
  # 上传文档
  curl -X POST http://localhost:8000/api/v1/knowledge-bases/{kb_id}/documents/upload \
    -F "file=@test.pdf"

  # 获取文档列表
  curl "http://localhost:8000/api/v1/knowledge-bases/{kb_id}/documents"
  ```

---

## 第2周：PDF转换和图片理解

### 2.1 Marker集成 (Day 4-5)

- [ ] **安装Marker**
  ```bash
  # 需要GPU支持
  pip install marker-pdf

  # 验证安装
  python -c "import marker; print(marker.__version__)"
  ```

- [ ] **实现 app/utils/pdf_converter.py**
  ```python
  from marker.converters.pdf import PdfConverter
  from marker.models import create_model_dict
  import os

  class PDFConverter:
      def __init__(self):
          self.models = create_model_dict()
          self.converter = PdfConverter(
              artifact_dict=self.models,
              processor_list=["ocr", "layout", "reading_order"]
          )

      def convert_pdf_to_markdown(self, pdf_path: str, output_dir: str):
          """
          转换PDF到Markdown

          Args:
              pdf_path: PDF文件路径
              output_dir: 输出目录

          Returns:
              (markdown_path, images_dir): Markdown文件路径和图片目录
          """
          try:
              # 转换PDF
              rendered = self.converter(pdf_path)

              # 保存Markdown
              markdown_path = os.path.join(output_dir, "content.md")
              with open(markdown_path, 'w', encoding='utf-8') as f:
                  f.write(rendered.markdown)

              # 保存图片
              images_dir = os.path.join(output_dir, "images")
              os.makedirs(images_dir, exist_ok=True)

              for img_name, img_data in rendered.images.items():
                  img_path = os.path.join(images_dir, img_name)
                  with open(img_path, 'wb') as f:
                      f.write(img_data)

              return markdown_path, images_dir

          except Exception as e:
              raise PDFConversionError(f"PDF转换失败: {str(e)}")
  ```

- [ ] **测试PDF转换**
  ```python
  # tests/test_utils/test_pdf_converter.py
  def test_pdf_conversion():
      converter = PDFConverter()
      markdown_path, images_dir = converter.convert_pdf_to_markdown(
          "tests/fixtures/test.pdf",
          "tests/output"
      )
      assert os.path.exists(markdown_path)
      assert os.path.exists(images_dir)
  ```

### 2.2 图片理解（Bedrock Claude） (Day 5-6)

- [ ] **实现图片描述生成**
  ```python
  # app/services/bedrock.py 中添加

  def generate_image_description(
      self,
      image_path: str,
      context: str,
      max_retries: int = 3
  ) -> str:
      """
      生成图片描述

      Args:
          image_path: 图片路径
          context: 图片上下文（前后文本）
          max_retries: 最大重试次数

      Returns:
          图片描述文本
      """
      # 读取图片
      with open(image_path, 'rb') as f:
          image_bytes = f.read()

      # 构建prompt
      prompt = f"""
      这是一张来自PRD文档的图片。

      图片上下文：
      {context}

      请详细描述这张图片的内容，包括：
      1. 图片类型（流程图/原型图/架构图/其他）
      2. 核心内容
      3. 关键元素和关系

      请用中文回答。
      """

      # 调用Bedrock
      for attempt in range(max_retries):
          try:
              response = self.client.invoke_model(
                  modelId=settings.GENERATION_MODEL_ID,
                  body=json.dumps({
                      "anthropic_version": "bedrock-2023-05-31",
                      "max_tokens": 1000,
                      "messages": [
                          {
                              "role": "user",
                              "content": [
                                  {
                                      "type": "image",
                                      "source": {
                                          "type": "base64",
                                          "media_type": "image/png",
                                          "data": base64.b64encode(image_bytes).decode()
                                      }
                                  },
                                  {
                                      "type": "text",
                                      "text": prompt
                                  }
                              ]
                          }
                      ]
                  })
              )

              result = json.loads(response['body'].read())
              return result['content'][0]['text']

          except Exception as e:
              if "throttling" in str(e).lower() or "rate" in str(e).lower():
                  # 限流，等待后重试
                  wait_time = 2 ** attempt
                  time.sleep(wait_time)
              else:
                  # 其他错误，返回降级描述
                  return f"[图片描述生成失败: {os.path.basename(image_path)}]"

      # 所有重试失败
      return f"[图片描述生成失败: {os.path.basename(image_path)}]"
  ```

- [ ] **实现图片上下文提取**
  ```python
  # app/utils/text_splitter.py

  def extract_image_context(markdown_content: str, image_name: str, context_length: int = 500):
      """
      从Markdown中提取图片上下文

      Args:
          markdown_content: Markdown内容
          image_name: 图片文件名
          context_length: 上下文字符数

      Returns:
          图片前后的文本
      """
      # 查找图片引用位置
      pattern = f"!\\[.*?\\]\\(.*?{image_name}.*?\\)"
      match = re.search(pattern, markdown_content)

      if not match:
          return ""

      pos = match.start()
      start = max(0, pos - context_length)
      end = min(len(markdown_content), pos + context_length)

      return markdown_content[start:end]
  ```

### 2.3 文本分块 (Day 6-7)

- [ ] **实现文本分块**
  ```python
  # app/utils/text_splitter.py

  from langchain.text_splitter import RecursiveCharacterTextSplitter

  class ChunkSplitter:
      def __init__(self, chunk_size=1000, chunk_overlap=200):
          self.splitter = RecursiveCharacterTextSplitter(
              chunk_size=chunk_size,
              chunk_overlap=chunk_overlap,
              separators=["\n\n", "\n", "。", "！", "？", " ", ""]
          )

      def split_markdown(self, markdown_content: str):
          """
          分块Markdown文本

          Returns:
              List of chunks
          """
          return self.splitter.split_text(markdown_content)

      def create_chunks_with_metadata(
          self,
          markdown_content: str,
          document_id: str,
          kb_id: str,
          image_descriptions: dict
      ):
          """
          创建带元数据的chunks

          Args:
              markdown_content: Markdown内容
              document_id: 文档ID
              kb_id: 知识库ID
              image_descriptions: 图片描述字典 {image_name: description}

          Returns:
              List of Chunk objects
          """
          chunks = []
          text_chunks = self.split_markdown(markdown_content)

          for idx, chunk_text in enumerate(text_chunks):
              # 检查chunk中是否引用了图片
              referenced_images = self._find_referenced_images(chunk_text)

              # 增强内容（添加图片描述）
              enhanced_content = chunk_text
              for img_name in referenced_images:
                  if img_name in image_descriptions:
                      enhanced_content += f"\n\n[图片描述: {image_descriptions[img_name]}]"

              chunk = {
                  'id': str(uuid.uuid4()),
                  'document_id': document_id,
                  'kb_id': kb_id,
                  'chunk_type': 'text',
                  'chunk_index': idx,
                  'content': chunk_text,
                  'content_with_context': enhanced_content,
                  'char_start': self._calculate_char_position(markdown_content, chunk_text),
                  'char_end': self._calculate_char_position(markdown_content, chunk_text) + len(chunk_text),
                  'token_count': self._count_tokens(enhanced_content)
              }
              chunks.append(chunk)

          return chunks

      def create_image_chunks(
          self,
          images_info: list,
          document_id: str,
          kb_id: str
      ):
          """
          创建图片chunks

          Args:
              images_info: 图片信息列表 [{'filename', 'description', 'context', ...}]

          Returns:
              List of Image Chunk objects
          """
          chunks = []

          for idx, img_info in enumerate(images_info):
              chunk = {
                  'id': str(uuid.uuid4()),
                  'document_id': document_id,
                  'kb_id': kb_id,
                  'chunk_type': 'image',
                  'chunk_index': idx,
                  'image_filename': img_info['filename'],
                  'image_s3_key': img_info['s3_key'],
                  'image_local_path': img_info['local_path'],
                  'image_description': img_info['description'],
                  'image_type': img_info.get('type', 'other'),
                  'content_with_context': f"{img_info.get('context', '')}\n\n图片描述：{img_info['description']}",
                  'token_count': self._count_tokens(img_info['description'])
              }
              chunks.append(chunk)

          return chunks
  ```

---

## 第3周：同步任务系统

### 3.1 同步任务模型 (Day 8)

- [ ] **实现 app/services/sync.py - 同步服务**
  ```python
  from app.models.database import SyncTask, Document, Chunk
  from app.utils.pdf_converter import PDFConverter
  from app.utils.text_splitter import ChunkSplitter
  from app.services.bedrock import BedrockService
  from app.services.opensearch import OpenSearchService
  import threading

  class SyncService:
      def __init__(self, db):
          self.db = db
          self.pdf_converter = PDFConverter()
          self.chunk_splitter = ChunkSplitter()
          self.bedrock = BedrockService()
          self.opensearch = OpenSearchService()

      async def create_sync_task(self, kb_id, task_type, document_ids=None):
          """创建同步任务"""
          # 1. 检查是否已有运行中的任务
          # 2. 创建任务记录
          # 3. 启动后台线程处理
          task = SyncTask(
              id=str(uuid.uuid4()),
              kb_id=kb_id,
              task_type=task_type,
              document_ids=json.dumps(document_ids or []),
              status='pending'
          )
          self.db.add(task)
          self.db.commit()

          # 异步执行
          thread = threading.Thread(
              target=self._process_sync_task,
              args=(task.id,)
          )
          thread.start()

          return task

      def _process_sync_task(self, task_id):
          """处理同步任务（后台线程）"""
          try:
              # 1. 更新任务状态为running
              task = self.db.query(SyncTask).filter_by(id=task_id).first()
              task.status = 'running'
              task.started_at = datetime.utcnow()
              self.db.commit()

              # 2. 获取需要处理的文档
              documents = self._get_documents_to_process(task)
              task.total_documents = len(documents)
              self.db.commit()

              # 3. 逐个处理文档
              for idx, doc in enumerate(documents):
                  try:
                      self._process_document(doc, task)
                      task.processed_documents += 1
                  except Exception as e:
                      logger.error(f"Document processing failed: {doc.id}", exc_info=True)
                      task.failed_documents += 1
                      doc.status = 'failed'
                      doc.error_message = str(e)

                  # 更新进度
                  task.progress = int((idx + 1) / len(documents) * 100)
                  task.current_step = f"正在处理文档 {idx + 1}/{len(documents)}"
                  self.db.commit()

              # 4. 完成任务
              if task.failed_documents == 0:
                  task.status = 'completed'
              elif task.processed_documents == 0:
                  task.status = 'failed'
              else:
                  task.status = 'partial_success'

              task.completed_at = datetime.utcnow()
              self.db.commit()

          except Exception as e:
              logger.error(f"Sync task failed: {task_id}", exc_info=True)
              task.status = 'failed'
              task.error_message = str(e)
              self.db.commit()

      def _process_document(self, document, task):
          """处理单个文档"""
          logger.info(f"Processing document: {document.id}")

          # 1. 下载PDF到本地
          task.current_step = f"正在下载 {document.filename}"
          self.db.commit()

          local_pdf = self._download_pdf(document)

          # 2. PDF转Markdown
          task.current_step = f"正在转换 {document.filename}"
          self.db.commit()

          output_dir = f"/data/cache/documents/{document.id}"
          os.makedirs(output_dir, exist_ok=True)

          markdown_path, images_dir = self.pdf_converter.convert_pdf_to_markdown(
              local_pdf, output_dir
          )

          # 3. 处理图片
          task.current_step = f"正在处理图片 {document.filename}"
          self.db.commit()

          images_info = self._process_images(
              markdown_path, images_dir, document
          )

          # 4. 创建chunks
          task.current_step = f"正在分块 {document.filename}"
          self.db.commit()

          with open(markdown_path, 'r', encoding='utf-8') as f:
              markdown_content = f.read()

          # 创建文本chunks
          text_chunks = self.chunk_splitter.create_chunks_with_metadata(
              markdown_content,
              document.id,
              document.kb_id,
              {img['filename']: img['description'] for img in images_info}
          )

          # 创建图片chunks
          image_chunks = self.chunk_splitter.create_image_chunks(
              images_info, document.id, document.kb_id
          )

          all_chunks = text_chunks + image_chunks

          # 5. 向量化
          task.current_step = f"正在向量化 {document.filename}"
          self.db.commit()

          self._vectorize_chunks(all_chunks)

          # 6. 存储到OpenSearch和数据库
          task.current_step = f"正在存储 {document.filename}"
          self.db.commit()

          self._store_chunks(all_chunks, document.kb_id)

          # 7. 更新文档状态
          document.status = 'completed'
          document.local_markdown_path = markdown_path
          document.local_images_dir = images_dir
          self.db.commit()

          logger.info(f"Document processed successfully: {document.id}")

      def _process_images(self, markdown_path, images_dir, document):
          """处理所有图片"""
          images_info = []

          with open(markdown_path, 'r', encoding='utf-8') as f:
              markdown_content = f.read()

          # 找到所有图片文件
          image_files = [f for f in os.listdir(images_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]

          for img_file in image_files:
              img_path = os.path.join(images_dir, img_file)

              # 提取上下文
              context = extract_image_context(markdown_content, img_file)

              # 生成描述
              description = self.bedrock.generate_image_description(img_path, context)

              # 上传到S3
              s3_key = f"{document.kb_id}/converted/{document.id}/images/{img_file}"
              self.s3.upload_file(img_path, s3_key)

              images_info.append({
                  'filename': img_file,
                  'local_path': img_path,
                  's3_key': s3_key,
                  'description': description,
                  'context': context,
                  'type': self._detect_image_type(description)
              })

          return images_info

      def _vectorize_chunks(self, chunks):
          """向量化chunks"""
          for chunk in chunks:
              try:
                  embedding = self.bedrock.generate_embedding(
                      chunk['content_with_context']
                  )
                  chunk['embedding'] = embedding
              except Exception as e:
                  logger.error(f"Embedding failed for chunk: {chunk['id']}", exc_info=True)
                  chunk['embedding'] = None

      def _store_chunks(self, chunks, kb_id):
          """存储chunks到OpenSearch和数据库"""
          # 存储到数据库
          for chunk_data in chunks:
              chunk = Chunk(**chunk_data)
              self.db.add(chunk)

          # 批量存储到OpenSearch
          index_name = f"kb_{kb_id}_index"
          for chunk in chunks:
              if chunk.get('embedding'):
                  self.opensearch.index_document(
                      index_name,
                      chunk['id'],
                      {
                          'chunk_id': chunk['id'],
                          'document_id': chunk['document_id'],
                          'kb_id': chunk['kb_id'],
                          'chunk_type': chunk['chunk_type'],
                          'content': chunk.get('content', ''),
                          'content_with_context': chunk['content_with_context'],
                          'embedding': chunk['embedding']
                      }
                  )

          self.db.commit()
  ```

### 3.2 同步任务API (Day 9)

- [ ] **实现 app/api/v1/sync_tasks.py**
  ```python
  from fastapi import APIRouter, Depends
  from app.services.sync import SyncService

  router = APIRouter()

  @router.post("/knowledge-bases/{kb_id}/sync")
  async def create_sync_task(
      kb_id: str,
      request: SyncTaskCreate,
      db = Depends(get_db)
  ):
      """创建同步任务"""
      service = SyncService(db)
      return await service.create_sync_task(
          kb_id, request.task_type, request.document_ids
      )

  @router.get("/knowledge-bases/{kb_id}/sync-tasks")
  async def list_sync_tasks(
      kb_id: str,
      status: Optional[str] = None,
      db = Depends(get_db)
  ):
      """获取同步任务列表"""
      pass

  @router.get("/sync-tasks/{task_id}")
  async def get_sync_task(task_id: str, db = Depends(get_db)):
      """获取任务详情"""
      pass

  @router.post("/sync-tasks/{task_id}/cancel")
  async def cancel_sync_task(task_id: str, db = Depends(get_db)):
      """取消任务"""
      pass
  ```

### 3.3 测试和优化 (Day 10)

- [ ] **端到端测试**
  ```python
  # tests/test_integration/test_sync_flow.py

  def test_full_sync_flow():
      """测试完整同步流程"""
      # 1. 创建知识库
      kb = create_knowledge_base("测试知识库")

      # 2. 上传文档
      doc = upload_document(kb.id, "test.pdf")

      # 3. 创建同步任务
      task = create_sync_task(kb.id, "full_sync")

      # 4. 等待任务完成
      wait_for_task_completion(task.id, timeout=300)

      # 5. 验证结果
      task = get_sync_task(task.id)
      assert task.status == "completed"

      # 6. 验证chunks已创建
      chunks = list_chunks(doc.id)
      assert len(chunks) > 0
  ```

- [ ] **性能测试**
  ```python
  def test_batch_document_processing():
      """测试批量文档处理"""
      # 上传10个文档
      # 测试处理时间
      # 验证成功率
      pass
  ```

---

## 验收标准

### 必须完成
- [ ] 知识库CRUD API全部实现
- [ ] 文档上传API实现
- [ ] PDF转Markdown成功（Marker）
- [ ] 图片描述生成成功（Bedrock）
- [ ] 文本分块正确
- [ ] 向量化成功（Bedrock Embedding）
- [ ] OpenSearch索引成功
- [ ] 同步任务系统工作正常
- [ ] 可以查看任务进度
- [ ] 错误处理完善

### 可选
- [ ] 批量上传文档
- [ ] 任务取消功能
- [ ] 失败重试功能

---

## 检查清单

在进入Phase 3之前，确认：

- [ ] 可以成功创建知识库
- [ ] 可以上传PDF文档
- [ ] PDF可以转换为Markdown
- [ ] 图片可以被正确理解
- [ ] Chunks可以被正确创建
- [ ] 向量可以被正确生成
- [ ] 数据可以存入OpenSearch
- [ ] 可以查看同步任务进度
- [ ] 错误会被正确记录和展示
- [ ] 完整流程测试通过

---

## 下一步

完成Phase 2后，进入 [Phase 3: 检索问答系统](./todo-phase3-query.md)
