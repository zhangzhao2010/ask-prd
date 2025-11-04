# Phase 5: 测试和优化

> 预计工期：1周
> 目标：完善功能、修复bug、优化性能

---

## Day 1-2: 单元测试

### 1.1 后端单元测试

- [ ] **测试工具配置**
  ```python
  # tests/conftest.py

  import pytest
  from sqlalchemy import create_engine
  from sqlalchemy.orm import sessionmaker
  from app.models.database import Base
  from app.main import app

  @pytest.fixture(scope="session")
  def test_db():
      """测试数据库"""
      engine = create_engine("sqlite:///:memory:")
      Base.metadata.create_all(bind=engine)
      SessionLocal = sessionmaker(bind=engine)
      yield SessionLocal()
      Base.metadata.drop_all(bind=engine)

  @pytest.fixture
  def client():
      """测试客户端"""
      from fastapi.testclient import TestClient
      return TestClient(app)
  ```

- [ ] **数据模型测试**
  ```python
  # tests/test_models/test_database.py

  def test_create_knowledge_base(test_db):
      """测试创建知识库"""
      kb = KnowledgeBase(
          id=str(uuid.uuid4()),
          name="测试知识库",
          s3_bucket="test-bucket",
          s3_prefix="test/"
      )
      test_db.add(kb)
      test_db.commit()

      assert kb.id is not None
      assert kb.name == "测试知识库"

  def test_document_cascade_delete(test_db):
      """测试级联删除"""
      # 创建知识库
      kb = create_test_kb(test_db)

      # 创建文档
      doc = create_test_document(test_db, kb.id)

      # 创建chunk
      chunk = create_test_chunk(test_db, doc.id, kb.id)

      # 删除文档
      test_db.delete(doc)
      test_db.commit()

      # 验证chunk也被删除
      chunk_count = test_db.query(Chunk).filter_by(document_id=doc.id).count()
      assert chunk_count == 0
  ```

- [ ] **服务层测试**
  ```python
  # tests/test_services/test_knowledge_base.py

  @pytest.mark.asyncio
  async def test_create_knowledge_base_success(test_db, mock_opensearch):
      """测试成功创建知识库"""
      service = KnowledgeBaseService(test_db, mock_opensearch)

      kb = await service.create_knowledge_base(
          name="测试知识库",
          description="测试",
          s3_bucket="test-bucket",
          s3_prefix="test/"
      )

      assert kb.id is not None
      assert kb.opensearch_index_name is not None
      mock_opensearch.create_index.assert_called_once()

  @pytest.mark.asyncio
  async def test_create_knowledge_base_duplicate_name(test_db):
      """测试重复名称"""
      service = KnowledgeBaseService(test_db)

      # 创建第一个
      await service.create_knowledge_base("测试", "", "bucket", "prefix/")

      # 尝试创建重复名称
      with pytest.raises(KnowledgeBaseAlreadyExistsError):
          await service.create_knowledge_base("测试", "", "bucket", "prefix/")
  ```

- [ ] **API测试**
  ```python
  # tests/test_api/test_knowledge_bases.py

  def test_list_knowledge_bases(client, test_db):
      """测试获取知识库列表"""
      # 创建测试数据
      create_test_kb(test_db)

      response = client.get("/api/v1/knowledge-bases")

      assert response.status_code == 200
      assert len(response.json()['data']) > 0

  def test_create_knowledge_base_invalid_data(client):
      """测试无效数据"""
      response = client.post(
          "/api/v1/knowledge-bases",
          json={"name": ""}  # 缺少必填字段
      )

      assert response.status_code == 400
      assert response.json()['error']['code'] == "1002"
  ```

- [ ] **工具函数测试**
  ```python
  # tests/test_utils/test_text_splitter.py

  def test_split_markdown():
      """测试Markdown分块"""
      splitter = ChunkSplitter(chunk_size=100, chunk_overlap=20)

      content = "这是一个测试文本。" * 50
      chunks = splitter.split_markdown(content)

      assert len(chunks) > 1
      assert all(len(c) <= 120 for c in chunks)  # chunk_size + overlap

  def test_extract_image_context():
      """测试提取图片上下文"""
      markdown = """
      这是一段文字。

      ![图片](image1.png)

      这是另一段文字。
      """

      context = extract_image_context(markdown, "image1.png", context_length=20)
      assert "图片" in context
  ```

### 1.2 前端单元测试

- [ ] **安装测试工具**
  ```bash
  cd frontend
  npm install --save-dev jest @testing-library/react @testing-library/jest-dom
  npm install --save-dev @testing-library/user-event
  ```

- [ ] **组件测试**
  ```tsx
  // src/components/__tests__/AnswerDisplay.test.tsx

  import { render, screen } from '@testing-library/react'
  import AnswerDisplay from '../query/AnswerDisplay'

  describe('AnswerDisplay', () => {
    it('renders markdown content', () => {
      const answer = '# 标题\n\n这是内容'
      const citations = []

      render(<AnswerDisplay answer={answer} citations={citations} />)

      expect(screen.getByText('标题')).toBeInTheDocument()
      expect(screen.getByText('这是内容')).toBeInTheDocument()
    })

    it('renders text citation', () => {
      const citation = {
        chunk_type: 'text',
        document_name: 'test.pdf',
        content: '引用内容'
      }

      render(<AnswerDisplay answer="" citations={[citation]} />)

      expect(screen.getByText('test.pdf')).toBeInTheDocument()
      expect(screen.getByText('引用内容')).toBeInTheDocument()
    })

    it('renders image citation', () => {
      const citation = {
        chunk_type: 'image',
        document_name: 'test.pdf',
        image_url: '/api/image.png',
        image_description: '图片描述'
      }

      render(<AnswerDisplay answer="" citations={[citation]} />)

      const img = screen.getByRole('img')
      expect(img).toHaveAttribute('src', '/api/image.png')
    })
  })
  ```

---

## Day 3-4: 集成测试

### 3.1 端到端流程测试

- [ ] **知识库完整流程**
  ```python
  # tests/test_integration/test_knowledge_base_flow.py

  @pytest.mark.integration
  def test_knowledge_base_lifecycle(client):
      """测试知识库完整生命周期"""
      # 1. 创建知识库
      create_response = client.post(
          "/api/v1/knowledge-bases",
          json={
              "name": "集成测试知识库",
              "description": "测试",
              "s3_bucket": "test-bucket",
              "s3_prefix": "test/"
          }
      )
      assert create_response.status_code == 201
      kb_id = create_response.json()['data']['id']

      # 2. 获取列表
      list_response = client.get("/api/v1/knowledge-bases")
      assert list_response.status_code == 200
      assert any(kb['id'] == kb_id for kb in list_response.json()['data'])

      # 3. 获取详情
      detail_response = client.get(f"/api/v1/knowledge-bases/{kb_id}")
      assert detail_response.status_code == 200
      assert detail_response.json()['data']['name'] == "集成测试知识库"

      # 4. 删除
      delete_response = client.delete(f"/api/v1/knowledge-bases/{kb_id}")
      assert delete_response.status_code == 200

      # 5. 验证已删除
      detail_response = client.get(f"/api/v1/knowledge-bases/{kb_id}")
      assert detail_response.status_code == 404
  ```

- [ ] **文档同步完整流程**
  ```python
  # tests/test_integration/test_document_sync_flow.py

  @pytest.mark.integration
  @pytest.mark.slow
  def test_document_sync_flow(client, test_pdf_file):
      """测试文档同步完整流程"""
      # 1. 创建知识库
      kb = create_test_kb_via_api(client)

      # 2. 上传文档
      with open(test_pdf_file, 'rb') as f:
          upload_response = client.post(
              f"/api/v1/knowledge-bases/{kb['id']}/documents/upload",
              files={"file": f}
          )
      assert upload_response.status_code == 201
      doc_id = upload_response.json()['data']['id']

      # 3. 创建同步任务
      sync_response = client.post(
          f"/api/v1/knowledge-bases/{kb['id']}/sync",
          json={"task_type": "full_sync", "document_ids": []}
      )
      assert sync_response.status_code == 201
      task_id = sync_response.json()['data']['task_id']

      # 4. 等待任务完成（轮询）
      max_wait = 300  # 最多等待5分钟
      start_time = time.time()

      while time.time() - start_time < max_wait:
          task_response = client.get(f"/api/v1/sync-tasks/{task_id}")
          task = task_response.json()['data']

          if task['status'] in ['completed', 'failed', 'partial_success']:
              break

          time.sleep(2)

      assert task['status'] == 'completed'
      assert task['processed_documents'] > 0

      # 5. 验证文档状态
      doc_response = client.get(f"/api/v1/documents/{doc_id}")
      doc = doc_response.json()['data']
      assert doc['status'] == 'completed'

      # 6. 验证chunks已创建
      # (通过查询测试)
  ```

- [ ] **问答完整流程**
  ```python
  # tests/test_integration/test_query_flow.py

  @pytest.mark.integration
  @pytest.mark.slow
  def test_query_flow(client, kb_with_documents):
      """测试问答完整流程"""
      kb_id = kb_with_documents['id']

      # 模拟SSE请求（使用requests-sse）
      import requests
      from sseclient import SSEClient

      response = requests.post(
          f"http://localhost:8000/api/v1/knowledge-bases/{kb_id}/query/stream",
          json={"query": "测试问题"},
          stream=True
      )

      events = []
      client = SSEClient(response)

      for event in client.events():
          events.append({
              'event': event.event,
              'data': json.loads(event.data)
          })

          if event.event == 'done':
              break

      # 验证事件序列
      event_types = [e['event'] for e in events]
      assert 'status' in event_types
      assert 'chunk' in event_types
      assert 'done' in event_types

      # 验证有答案内容
      chunks = [e['data']['content'] for e in events if e['event'] == 'chunk']
      answer = ''.join(chunks)
      assert len(answer) > 0

      # 验证查询历史已保存
      done_event = next(e for e in events if e['event'] == 'done')
      query_id = done_event['data']['query_id']

      history_response = client.get(f"/api/v1/query-history/{query_id}")
      assert history_response.status_code == 200
  ```

---

## Day 5: 性能测试

### 5.1 负载测试

- [ ] **使用Locust进行负载测试**
  ```python
  # tests/performance/locustfile.py

  from locust import HttpUser, task, between

  class AKSPRDUser(HttpUser):
      wait_time = between(1, 5)

      def on_start(self):
          """初始化"""
          # 获取知识库列表
          response = self.client.get("/api/v1/knowledge-bases")
          kbs = response.json()['data']
          if kbs:
              self.kb_id = kbs[0]['id']

      @task(3)
      def list_documents(self):
          """获取文档列表（高频操作）"""
          self.client.get(f"/api/v1/knowledge-bases/{self.kb_id}/documents")

      @task(1)
      def query(self):
          """查询（低频但耗时操作）"""
          self.client.post(
              f"/api/v1/knowledge-bases/{self.kb_id}/query/stream",
              json={"query": "测试问题"}
          )

      @task(2)
      def get_query_history(self):
          """获取历史记录"""
          self.client.get(f"/api/v1/knowledge-bases/{self.kb_id}/query-history")
  ```

  ```bash
  # 运行负载测试
  locust -f tests/performance/locustfile.py --host=http://localhost:8000
  ```

### 5.2 性能优化

- [ ] **数据库查询优化**
  - 添加必要的索引
  - 使用连接池
  - 避免N+1查询

- [ ] **缓存优化**
  - 文档内容缓存
  - 查询结果缓存（可选）
  - Embedding结果缓存

- [ ] **并发优化**
  - Sub-Agent并发数调整
  - 数据库连接池大小
  - OpenSearch批量操作

---

## Day 6-7: Bug修复和完善

### 6.1 已知问题清单

- [ ] **高优先级**
  - [ ] PDF转换失败时的错误处理
  - [ ] Bedrock限流时的重试机制
  - [ ] OpenSearch连接失败的恢复
  - [ ] 文件上传大小验证
  - [ ] SSE连接断开重连

- [ ] **中优先级**
  - [ ] 任务取消功能
  - [ ] 失败文档重试
  - [ ] 查询历史分页
  - [ ] Token统计准确性
  - [ ] 日志格式统一

- [ ] **低优先级**
  - [ ] 性能监控
  - [ ] 缓存清理策略
  - [ ] API限流
  - [ ] 请求ID追踪

### 6.2 代码质量

- [ ] **代码审查**
  - 代码规范检查（black, isort, flake8）
  - 类型检查（mypy）
  - 安全检查（bandit）

- [ ] **代码覆盖率**
  ```bash
  # 运行测试并生成覆盖率报告
  pytest tests/ --cov=app --cov-report=html

  # 目标：覆盖率 > 70%
  ```

- [ ] **文档完善**
  - 所有公共API添加docstring
  - 复杂逻辑添加注释
  - README更新

---

## 验收清单

### 功能验收
- [ ] 所有单元测试通过
- [ ] 所有集成测试通过
- [ ] 端到端流程测试通过
- [ ] 错误场景测试通过
- [ ] 性能测试达标

### 质量验收
- [ ] 代码覆盖率 > 70%
- [ ] 无严重bug
- [ ] 无安全漏洞
- [ ] 代码规范通过
- [ ] 文档完整

### 性能验收
- [ ] 问答响应时间 < 30秒
- [ ] 文档同步无明显卡顿
- [ ] 并发10用户无问题
- [ ] 内存占用合理
- [ ] 磁盘使用合理

---

## 最终交付物

### 代码
- [ ] 完整的后端代码
- [ ] 完整的前端代码
- [ ] 完整的测试代码
- [ ] 部署脚本

### 文档
- [ ] 需求文档
- [ ] 架构设计文档
- [ ] API文档
- [ ] 数据库设计文档
- [ ] 部署文档
- [ ] 用户手册

### 其他
- [ ] 测试报告
- [ ] 性能测试报告
- [ ] 已知问题清单
- [ ] 后续优化建议

---

## 下一步计划

Phase 5完成后，项目进入维护阶段，可以考虑：

1. **功能增强**
   - 多轮对话支持
   - 用户系统
   - 权限管理
   - 更多文档格式支持

2. **性能优化**
   - 引入Reranker
   - 使用更小的模型
   - 分布式部署
   - 缓存优化

3. **运维优化**
   - 监控系统
   - 告警系统
   - 自动化部署
   - 日志分析

4. **成本优化**
   - Token消耗优化
   - 向量维度降维
   - 批量处理优化
