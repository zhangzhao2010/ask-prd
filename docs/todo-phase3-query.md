# Phase 3: 检索问答系统

> 预计工期：3周
> 目标：实现基于Multi-Agent的智能问答

---

## 第1周：检索系统

### 1.1 Query Rewrite (Day 1-2)

- [ ] **实现查询重写**
  ```python
  # app/services/query.py

  class QueryService:
      def __init__(self, bedrock: BedrockService):
          self.bedrock = bedrock

      async def rewrite_query(self, original_query: str) -> List[str]:
          """
          重写用户查询，生成多个检索变体

          Args:
              original_query: 用户原始查询

          Returns:
              List of rewritten queries
          """
          prompt = f"""
          用户的原始问题是："{original_query}"

          请将这个问题改写成3个不同的检索查询，以提高召回率。
          改写要求：
          1. 保持原意
          2. 使用不同的表达方式
          3. 添加可能的同义词或相关术语
          4. 适合向量检索和关键词检索

          请直接输出3个改写后的查询，每行一个，不要编号。
          """

          response = self.bedrock.generate_text(prompt)

          # 解析响应
          rewritten_queries = [q.strip() for q in response.strip().split('\n') if q.strip()]

          # 包含原始查询
          return [original_query] + rewritten_queries[:3]
  ```

- [ ] **测试Query Rewrite**
  ```python
  # tests/test_services/test_query.py

  def test_query_rewrite():
      service = QueryService(bedrock)
      queries = await service.rewrite_query("登录注册模块的演进历史")

      assert len(queries) >= 2  # 至少原始+1个改写
      assert "登录" in queries[0] or "注册" in queries[0]
  ```

### 1.2 Hybrid Search (Day 2-4)

- [ ] **实现向量检索**
  ```python
  # app/services/opensearch.py 中添加

  def vector_search(
      self,
      index_name: str,
      query_vector: List[float],
      top_k: int = 20,
      filters: dict = None
  ):
      """
      向量检索

      Args:
          index_name: 索引名称
          query_vector: 查询向量
          top_k: 返回数量
          filters: 过滤条件

      Returns:
          List of search results
      """
      query = {
          "size": top_k,
          "query": {
              "knn": {
                  "embedding": {
                      "vector": query_vector,
                      "k": top_k
                  }
              }
          }
      }

      if filters:
          query["query"] = {
              "bool": {
                  "must": [query["query"]],
                  "filter": filters
              }
          }

      response = self.client.search(
          index=index_name,
          body=query
      )

      return self._parse_search_results(response)
  ```

- [ ] **实现BM25检索**
  ```python
  def bm25_search(
      self,
      index_name: str,
      query_text: str,
      top_k: int = 20
  ):
      """
      BM25关键词检索

      Args:
          index_name: 索引名称
          query_text: 查询文本
          top_k: 返回数量

      Returns:
          List of search results
      """
      query = {
          "size": top_k,
          "query": {
              "multi_match": {
                  "query": query_text,
                  "fields": ["content^2", "content_with_context"],
                  "type": "best_fields"
              }
          }
      }

      response = self.client.search(
          index=index_name,
          body=query
      )

      return self._parse_search_results(response)
  ```

- [ ] **实现Hybrid Search（RRF合并）**
  ```python
  # app/services/query.py 中添加

  def hybrid_search(
      self,
      index_name: str,
      queries: List[str],
      top_k: int = 20
  ) -> List[dict]:
      """
      混合检索：向量检索 + BM25检索

      Args:
          index_name: 索引名称
          queries: 查询列表（包含原始和改写）
          top_k: 最终返回数量

      Returns:
          List of search results (sorted by score)
      """
      all_results = []

      for query in queries:
          # 向量检索
          query_vector = self.bedrock.generate_embedding(query)
          vector_results = self.opensearch.vector_search(
              index_name, query_vector, top_k * 2
          )

          # BM25检索
          bm25_results = self.opensearch.bm25_search(
              index_name, query, top_k * 2
          )

          all_results.append((vector_results, bm25_results))

      # 使用RRF合并结果
      merged_results = self._reciprocal_rank_fusion(
          all_results, k=60
      )

      # 去重和排序
      deduplicated = self._deduplicate_results(merged_results)

      return deduplicated[:top_k]

  def _reciprocal_rank_fusion(
      self,
      result_lists: List[tuple],
      k: int = 60
  ) -> List[dict]:
      """
      Reciprocal Rank Fusion算法合并多个检索结果

      Args:
          result_lists: 多组检索结果
          k: RRF参数

      Returns:
          合并后的结果
      """
      scores = {}

      for vector_results, bm25_results in result_lists:
          # 向量检索结果
          for rank, result in enumerate(vector_results, 1):
              chunk_id = result['chunk_id']
              if chunk_id not in scores:
                  scores[chunk_id] = {'score': 0, 'result': result}
              scores[chunk_id]['score'] += 1 / (k + rank)

          # BM25结果
          for rank, result in enumerate(bm25_results, 1):
              chunk_id = result['chunk_id']
              if chunk_id not in scores:
                  scores[chunk_id] = {'score': 0, 'result': result}
              scores[chunk_id]['score'] += 1 / (k + rank)

      # 排序
      sorted_results = sorted(
          scores.values(),
          key=lambda x: x['score'],
          reverse=True
      )

      return [r['result'] for r in sorted_results]

  def _deduplicate_results(self, results: List[dict]) -> List[dict]:
      """去重"""
      seen = set()
      deduplicated = []

      for result in results:
          chunk_id = result['chunk_id']
          if chunk_id not in seen:
              seen.add(chunk_id)
              deduplicated.append(result)

      return deduplicated
  ```

- [ ] **测试Hybrid Search**
  ```python
  def test_hybrid_search():
      service = QueryService(bedrock, opensearch)
      results = service.hybrid_search(
          "kb_test_index",
          ["登录功能", "用户登录", "认证方式"],
          top_k=10
      )

      assert len(results) <= 10
      assert all('chunk_id' in r for r in results)
  ```

### 1.3 文档聚合 (Day 4)

- [ ] **实现按文档聚合chunks**
  ```python
  # app/services/query.py 中添加

  def aggregate_by_document(
      self,
      search_results: List[dict]
  ) -> dict:
      """
      将检索到的chunks按文档聚合

      Args:
          search_results: 检索结果

      Returns:
          {document_id: [chunk1, chunk2, ...]}
      """
      aggregated = {}

      for result in search_results:
          doc_id = result['document_id']
          if doc_id not in aggregated:
              aggregated[doc_id] = []
          aggregated[doc_id].append(result)

      return aggregated
  ```

---

## 第2周：Multi-Agent系统

### 2.1 Sub-Agent实现 (Day 5-7)

- [ ] **实现Sub-Agent**
  ```python
  # app/agents/sub_agent.py

  class SubAgent:
      def __init__(self, bedrock: BedrockService):
          self.bedrock = bedrock

      async def process_document(
          self,
          document_id: str,
          query: str,
          relevant_chunks: List[dict]
      ) -> dict:
          """
          阅读单个文档并生成回答

          Args:
              document_id: 文档ID
              query: 用户问题
              relevant_chunks: 相关chunks

          Returns:
              {
                  "document_id": str,
                  "document_name": str,
                  "answer": str,
                  "citations": [chunk_id, ...]
              }
          """
          # 1. 获取文档内容（优先本地缓存）
          markdown_path = await self._get_document_content(document_id)

          # 2. 读取文档
          with open(markdown_path, 'r', encoding='utf-8') as f:
              markdown_content = f.read()

          # 3. 加载相关图片
          images = await self._load_relevant_images(relevant_chunks)

          # 4. 构建Prompt
          prompt = self._build_prompt(query, markdown_content, relevant_chunks)

          # 5. 调用Bedrock（多模态）
          response = await self.bedrock.generate_with_images(
              text=prompt,
              images=images
          )

          # 6. 解析响应
          result = self._parse_response(response)

          return {
              "document_id": document_id,
              "document_name": self._get_document_name(document_id),
              "answer": result['answer'],
              "citations": result['citations']
          }

      def _build_prompt(
          self,
          query: str,
          markdown_content: str,
          relevant_chunks: List[dict]
      ) -> str:
          """构建Prompt"""
          # 格式化相关chunks
          chunks_text = "\n\n".join([
              f"【片段{i+1} - chunk_id: {c['chunk_id']}】\n{c['content']}"
              for i, c in enumerate(relevant_chunks)
          ])

          prompt = f"""
          你是一个专业的产品文档分析助手。请仔细阅读以下PRD文档，回答用户的问题。

          用户问题：
          {query}

          完整文档内容：
          {markdown_content}

          重点关注的片段：
          {chunks_text}

          请输出JSON格式的回答：
          {{
              "answer": "针对用户问题的回答",
              "citations": ["chunk_id1", "chunk_id2", ...]
          }}

          要求：
          1. 回答要准确、完整
          2. citations中列出你引用的chunk_id
          3. 如果文档中没有相关信息，明确说明
          """

          return prompt

      def _parse_response(self, response: str) -> dict:
          """解析Bedrock响应"""
          try:
              import json
              result = json.loads(response)
              return result
          except:
              # 如果不是JSON格式，尝试提取
              return {
                  "answer": response,
                  "citations": []
              }

      async def _get_document_content(self, document_id: str) -> str:
          """获取文档内容（本地缓存优先）"""
          # 从数据库查询
          doc = self.db.query(Document).filter_by(id=document_id).first()

          if doc.local_markdown_path and os.path.exists(doc.local_markdown_path):
              return doc.local_markdown_path

          # 从S3下载
          local_path = f"/data/cache/documents/{document_id}/content.md"
          await self.s3.download_file(doc.s3_key_markdown, local_path)

          # 更新数据库
          doc.local_markdown_path = local_path
          self.db.commit()

          return local_path

      async def _load_relevant_images(self, relevant_chunks: List[dict]) -> List[str]:
          """加载相关图片"""
          images = []

          for chunk in relevant_chunks:
              if chunk.get('chunk_type') == 'image':
                  # 获取图片路径
                  chunk_obj = self.db.query(Chunk).filter_by(id=chunk['chunk_id']).first()

                  if chunk_obj.image_local_path and os.path.exists(chunk_obj.image_local_path):
                      images.append(chunk_obj.image_local_path)
                  else:
                      # 从S3下载
                      local_path = f"/data/cache/images/{chunk_obj.id}.png"
                      await self.s3.download_file(chunk_obj.image_s3_key, local_path)
                      images.append(local_path)

          return images
  ```

### 2.2 Main Agent实现 (Day 7-8)

- [ ] **实现Main Agent**
  ```python
  # app/agents/main_agent.py

  from concurrent.futures import ThreadPoolExecutor, as_completed

  class MainAgent:
      def __init__(self, bedrock: BedrockService):
          self.bedrock = bedrock
          self.sub_agent = SubAgent(bedrock)

      async def process_query(
          self,
          query: str,
          kb_id: str
      ) -> dict:
          """
          处理用户查询（完整流程）

          Args:
              query: 用户问题
              kb_id: 知识库ID

          Returns:
              {
                  "query_id": str,
                  "answer": str,
                  "citations": [...],
                  "tokens": {...}
              }
          """
          # 1. Query Rewrite
          rewritten_queries = await self.query_service.rewrite_query(query)

          # 2. Hybrid Search
          index_name = f"kb_{kb_id}_index"
          search_results = self.query_service.hybrid_search(
              index_name, rewritten_queries, top_k=20
          )

          if not search_results:
              raise NoDocumentsFoundError("未找到相关文档")

          # 3. 按文档聚合
          aggregated = self.query_service.aggregate_by_document(search_results)

          # 4. 并发执行Sub-Agent
          sub_agent_results = await self._run_sub_agents(
              query, aggregated
          )

          if not sub_agent_results:
              raise AgentExecutionError("所有文档处理都失败了")

          # 5. Main Agent综合
          final_answer = await self._synthesize_answer(
              query, sub_agent_results
          )

          # 6. 保存查询历史
          query_record = await self._save_query_history(
              kb_id, query, rewritten_queries, final_answer
          )

          return {
              "query_id": query_record.id,
              "answer": final_answer['answer'],
              "citations": final_answer['citations'],
              "tokens": final_answer['tokens']
          }

      async def _run_sub_agents(
          self,
          query: str,
          aggregated: dict
      ) -> List[dict]:
          """并发运行Sub-Agent"""
          results = []
          failed_docs = []

          # 限制并发数为5
          with ThreadPoolExecutor(max_workers=5) as executor:
              futures = {
                  executor.submit(
                      self.sub_agent.process_document,
                      doc_id,
                      query,
                      chunks
                  ): doc_id
                  for doc_id, chunks in aggregated.items()
              }

              for future in as_completed(futures):
                  doc_id = futures[future]
                  try:
                      result = future.result(timeout=60)  # 60秒超时
                      results.append(result)
                  except TimeoutError:
                      logger.error(f"Sub-agent timeout: {doc_id}")
                      failed_docs.append(doc_id)
                  except Exception as e:
                      logger.error(f"Sub-agent error: {doc_id}, {e}")
                      failed_docs.append(doc_id)

          if failed_docs:
              logger.warning(f"Sub-agents partial failure: {failed_docs}")

          return results

      async def _synthesize_answer(
          self,
          query: str,
          sub_agent_results: List[dict]
      ) -> dict:
          """综合Sub-Agent的结果"""
          # 构建Prompt
          sub_results_text = "\n\n".join([
              f"【文档：{r['document_name']}】\n{r['answer']}"
              for r in sub_agent_results
          ])

          prompt = f"""
          你是一个产品知识问答助手。现在有多个文档的分析结果，请综合回答用户的问题。

          用户问题：
          {query}

          各文档的分析结果：
          {sub_results_text}

          请综合以上信息，生成一个完整、准确、结构化的回答。
          如果不同文档有演进关系，请按时间顺序组织答案。

          在相关段落后使用[^1][^2]标注引用。
          """

          # 流式生成
          answer_chunks = []
          async for chunk in self.bedrock.generate_text_stream(prompt):
              answer_chunks.append(chunk)

          answer = "".join(answer_chunks)

          # 收集所有citations
          all_citations = []
          for r in sub_agent_results:
              for chunk_id in r['citations']:
                  # 从数据库获取chunk详情
                  chunk = self.db.query(Chunk).filter_by(id=chunk_id).first()
                  citation = self._format_citation(chunk)
                  all_citations.append(citation)

          return {
              "answer": answer,
              "citations": all_citations,
              "tokens": {
                  "prompt_tokens": 0,  # TODO: 计算
                  "completion_tokens": 0,  # TODO: 计算
                  "total_tokens": 0
              }
          }

      def _format_citation(self, chunk: Chunk) -> dict:
          """格式化引用"""
          doc = self.db.query(Document).filter_by(id=chunk.document_id).first()

          if chunk.chunk_type == 'text':
              return {
                  "chunk_id": chunk.id,
                  "chunk_type": "text",
                  "document_id": chunk.document_id,
                  "document_name": doc.filename,
                  "content": chunk.content,
                  "chunk_index": chunk.chunk_index
              }
          else:  # image
              return {
                  "chunk_id": chunk.id,
                  "chunk_type": "image",
                  "document_id": chunk.document_id,
                  "document_name": doc.filename,
                  "image_url": f"/api/v1/chunks/{chunk.id}/image",
                  "image_description": chunk.image_description,
                  "chunk_index": chunk.chunk_index
              }
  ```

---

## 第3周：流式输出和API实现

### 3.1 流式输出（SSE） (Day 9-10)

- [ ] **实现流式查询API**
  ```python
  # app/api/v1/query.py

  from fastapi import APIRouter
  from fastapi.responses import StreamingResponse
  from sse_starlette.sse import EventSourceResponse

  router = APIRouter()

  @router.post("/knowledge-bases/{kb_id}/query/stream")
  async def stream_query(
      kb_id: str,
      request: QueryRequest,
      db = Depends(get_db)
  ):
      """流式问答"""
      async def event_generator():
          try:
              # 状态: 重写查询
              yield {
                  "event": "status",
                  "data": json.dumps({
                      "status": "rewriting_query",
                      "message": "正在优化查询..."
                  }, ensure_ascii=False)
              }

              # ... Query Rewrite

              # 状态: 检索
              yield {
                  "event": "status",
                  "data": json.dumps({
                      "status": "searching",
                      "message": "正在检索文档..."
                  }, ensure_ascii=False)
              }

              # ... Hybrid Search

              # 检索到的文档
              yield {
                  "event": "retrieved_documents",
                  "data": json.dumps({
                      "document_ids": [doc_id for doc_id in aggregated.keys()],
                      "document_names": [get_doc_name(doc_id) for doc_id in aggregated.keys()]
                  }, ensure_ascii=False)
              }

              # 状态: 阅读文档
              for idx, doc_id in enumerate(aggregated.keys(), 1):
                  yield {
                      "event": "status",
                      "data": json.dumps({
                          "status": "reading_documents",
                          "message": f"正在阅读文档 {idx}/{len(aggregated)}"
                      }, ensure_ascii=False)
                  }

              # ... Sub-Agent处理

              # 状态: 生成答案
              yield {
                  "event": "status",
                  "data": json.dumps({
                      "status": "generating",
                      "message": "正在生成答案..."
                  }, ensure_ascii=False)
              }

              # 流式生成答案
              async for chunk in main_agent.generate_answer_stream(query, sub_results):
                  yield {
                      "event": "chunk",
                      "data": json.dumps({
                          "content": chunk
                      }, ensure_ascii=False)
                  }

              # 引用
              for citation in final_answer['citations']:
                  yield {
                      "event": "citation",
                      "data": json.dumps(citation, ensure_ascii=False)
                  }

              # Token统计
              yield {
                  "event": "tokens",
                  "data": json.dumps(final_answer['tokens'], ensure_ascii=False)
              }

              # 完成
              yield {
                  "event": "done",
                  "data": json.dumps({
                      "query_id": query_record.id
                  }, ensure_ascii=False)
              }

          except Exception as e:
              logger.error(f"Query failed: {str(e)}", exc_info=True)
              yield {
                  "event": "error",
                  "data": json.dumps({
                      "code": "8001",
                      "message": str(e)
                  }, ensure_ascii=False)
              }

      return EventSourceResponse(event_generator())
  ```

### 3.2 查询历史API (Day 10)

- [ ] **实现查询历史API**
  ```python
  @router.get("/knowledge-bases/{kb_id}/query-history")
  async def list_query_history(
      kb_id: str,
      page: int = 1,
      page_size: int = 20,
      db = Depends(get_db)
  ):
      """获取查询历史列表"""
      pass

  @router.get("/query-history/{query_id}")
  async def get_query_detail(query_id: str, db = Depends(get_db)):
      """获取查询详情"""
      pass

  @router.delete("/query-history/{query_id}")
  async def delete_query(query_id: str, db = Depends(get_db)):
      """删除查询记录"""
      pass
  ```

### 3.3 工具类API (Day 10)

- [ ] **实现工具API**
  ```python
  # app/api/v1/utilities.py

  @router.get("/chunks/{chunk_id}/image")
  async def get_chunk_image(chunk_id: str, db = Depends(get_db)):
      """获取图片chunk的图片"""
      chunk = db.query(Chunk).filter_by(id=chunk_id).first()

      if not chunk or chunk.chunk_type != 'image':
          raise HTTPException(404, "图片不存在")

      # 获取图片路径
      if chunk.image_local_path and os.path.exists(chunk.image_local_path):
          image_path = chunk.image_local_path
      else:
          # 从S3下载
          image_path = f"/tmp/{chunk.id}.png"
          await s3_service.download_file(chunk.image_s3_key, image_path)

      # 返回图片
      return FileResponse(
          image_path,
          media_type="image/png",
          headers={"Cache-Control": "public, max-age=86400"}
      )

  @router.get("/stats")
  async def get_stats(kb_id: Optional[str] = None, db = Depends(get_db)):
      """获取统计信息"""
      pass
  ```

---

## 验收标准

### 必须完成
- [ ] Query Rewrite功能正常
- [ ] Hybrid Search工作正常
- [ ] Sub-Agent可以正确处理文档
- [ ] Main Agent可以综合生成答案
- [ ] 流式输出工作正常
- [ ] 引用提取正确（文本+图片）
- [ ] 查询历史保存正常
- [ ] 图片可以正确展示
- [ ] 端到端测试通过

### 可选
- [ ] 查询缓存
- [ ] 答案质量评分
- [ ] 用户反馈功能

---

## 检查清单

在进入Phase 4之前，确认：

- [ ] 可以成功提问并得到答案
- [ ] 答案流式输出正常
- [ ] 引用信息正确
- [ ] 图片可以正确展示
- [ ] 查询历史可以查看
- [ ] Token统计准确
- [ ] 错误处理完善
- [ ] 性能可接受（< 30秒）
- [ ] 完整流程测试通过

---

## 下一步

完成Phase 3后，进入 [Phase 4: 前端开发](./todo-phase4-frontend.md)
