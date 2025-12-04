# Two-Stage查询系统使用指南

## 🎉 实现完成

Two-Stage查询系统已全部实现完成，所有核心模块测试通过！

## ✅ 已实现的功能

### 核心模块
1. **DocumentLoader** - 从S3/缓存加载文档和图片
2. **DocumentProcessor** - 智能分段、标记生成、图文混排
3. **ReferenceExtractor** - 引用提取和格式化
4. **TwoStageExecutor** - 两阶段执行器（文档理解 + 答案综合）

### API接口
1. **查询接口** - `POST /api/v1/query/stream` (已集成Two-Stage)
2. **图片服务** - `GET /api/v1/documents/{doc_id}/images/{filename}`

## 🚀 快速开始

### 1. 运行单元测试

```bash
cd /home/ubuntu/ask-prd/backend
python test_two_stage.py
```

**预期输出**：
```
============================================================
Two-Stage System Unit Tests
============================================================
Testing DocumentProcessor...
✓ test_document_processor PASSED

Testing ReferenceExtractor...
✓ test_reference_extractor PASSED

Testing _group_chunks_by_document...
✓ test_group_chunks PASSED

============================================================
Results: 3 passed, 0 failed
============================================================
```

### 2. 启动后端服务

```bash
cd /home/ubuntu/ask-prd/backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 测试查询接口

```bash
# 使用curl测试流式查询
curl -N "http://localhost:8000/api/v1/query/stream?kb_id={知识库ID}&query=测试问题"
```

### 4. 测试图片接口

```bash
# 获取文档图片
curl "http://localhost:8000/api/v1/documents/{doc_id}/images/img_001.png" --output test.png
```

## 📊 SSE事件格式

查询接口返回以下SSE事件：

### 1. status事件
```json
{
  "type": "status",
  "message": "正在检索相关文档..."
}
```
**注意**：与Multi-Agent系统保持一致的格式。

### 2. retrieved_documents事件
```json
{
  "type": "retrieved_documents",
  "document_ids": ["doc-id-1", "doc-id-2"],
  "document_count": 2
}
```

### 3. progress事件（Stage 1处理进度）
```json
{
  "type": "progress",
  "data": {
    "current": 1,
    "total": 3,
    "doc_name": "产品需求v1.md"
  }
}
```

### 4. answer_delta事件（Stage 2流式答案）
```json
{
  "type": "answer_delta",
  "data": {
    "text": "根据"
  }
}
```

### 5. references事件（引用列表）
```json
{
  "type": "references",
  "data": [
    {
      "ref_id": "DOC-abc12345-PARA-5",
      "doc_id": "abc12345-...",
      "doc_name": "产品需求v1.md",
      "chunk_type": "text",
      "content": "JOIN是一款专为年轻人设计的社交App...",
      "image_url": null
    },
    {
      "ref_id": "DOC-abc12345-IMAGE-2",
      "doc_id": "abc12345-...",
      "doc_name": "产品需求v1.md",
      "chunk_type": "image",
      "content": null,
      "image_url": "/api/v1/documents/abc12345.../images/img_002.png"
    }
  ]
}
```

### 6. done事件（完成）
```json
{
  "type": "done",
  "data": {
    "tokens": {
      "prompt_tokens": 15000,
      "completion_tokens": 800,
      "total_tokens": 15800
    }
  }
}
```

### 7. error事件（错误）
```json
{
  "type": "error",
  "data": {
    "message": "查询执行失败: ..."
  }
}
```

## 🔧 核心流程

### Two-Stage执行流程

```
1. 混合检索 (Hybrid Search)
   - 向量检索 (kNN)
   - 关键词检索 (BM25)
   - RRF合并
   ↓
2. 提取Document ID列表
   ↓
3. Stage 1: 串行处理每个Document
   - DocumentLoader: 下载Markdown + 图片
   - DocumentProcessor: 分段、标记、构建content
   - Bedrock调用: 理解文档并返回结构化回复
   - 推送progress事件
   ↓
4. Stage 2: 综合答案（JSON格式，非流式）
   - 汇总所有Stage1结果
   - Bedrock同步调用（非流式）: 一次性获取完整JSON响应
     {
       "answer": "完整答案（包含引用标记）",
       "references": [
         {
           "chunk_id": "[DOC-xxx-PARA-Y]",
           "chunk_type": "text/image",
           "chunk_content": "段落内容或图片URL"
         }
       ]
     }
   - 解析JSON并模拟流式推送answer（逐字发送，每次10字符）
   ↓
5. 处理引用
   - 从JSON的references字段解析引用
   - 构建Reference对象（自动补充doc_id、doc_name、image_url）
   - 降级方案：如果references为空，从stage1_results构建基础引用
   - 推送references事件
   ↓
6. 完成
   - 推送done事件
```

### JSON格式说明

**Stage 2 返回格式**：
```json
{
  "answer": "根据产品需求文档[DOC-abc12345-PARA-3]，JOIN是一款社交App...",
  "references": [
    {
      "chunk_id": "[DOC-abc12345-PARA-3]",
      "chunk_type": "text",
      "chunk_content": "JOIN是一款专为年轻人设计的社交App..."
    },
    {
      "chunk_id": "[DOC-abc12345-IMAGE-1]",
      "chunk_type": "image",
      "chunk_content": "img_001.png"
    }
  ]
}
```

**处理流程**：
1. 使用Bedrock同步API一次性获取完整JSON响应
2. 移除可能的markdown代码块标记（```json ... ```）
3. 清理尾部逗号（防止JSON格式错误）
4. 解析JSON获取answer和references
5. 将answer逐字流式发送给前端（每次10字符，每次延迟10ms，模拟流式效果）
6. 从references构建完整的Reference对象（补充doc_id、doc_name、image_url等）

## 📝 引用标记格式

### 段落标记
```
[DOC-{短ID}-PARA-{序号}]

示例：[DOC-abc12345-PARA-5]
```

### 图片标记
```
[DOC-{短ID}-IMAGE-{序号}]

示例：[DOC-abc12345-IMAGE-2]
```

**短ID规则**：取document_id的前8位UUID字符

## 🗂️ 文件路径规则

### S3路径
```
s3://bucket/prds/product-a/converted/doc-{uuid}/
├── content.md
└── images/
    ├── img_001.png
    ├── img_002.png
    └── ...
```

### 本地缓存路径
```
/data/cache/documents/{doc_id}/
├── content.md
├── img_001.png
├── img_002.png
└── ...
```

### 前端访问URL
```
/api/v1/documents/{doc_id}/images/img_001.png
```

## 🐛 已知问题和解决方案

### ✅ 问题1：document_id为None
**原因**：OpenSearch返回的document_id在source字段里
**解决**：已修复`_group_chunks_by_document`方法，从`source`字段提取

### ✅ 问题2：BedrockModel参数冲突
**原因**：不能同时指定`boto_session`和`region_name`
**错误**：`ValueError: Cannot specify both 'region_name' and 'boto_session'.`
**解决**：
- 修复`bedrock_client.py`的`get_generation_model`，只传`boto_session`
- 修复`two_stage_executor.py`的Bedrock调用，使用`bedrock_client.boto_session`

### ✅ 问题3：BedrockModel没有model_id属性
**原因**：Strands的BedrockModel不暴露model_id等配置属性
**错误**：`AttributeError: 'BedrockModel' object has no attribute 'model_id'`
**解决**：
- 不再使用BedrockModel对象（它只是Strands的封装）
- 直接使用boto3的bedrock-runtime客户端
- 从settings获取model_id、temperature、max_tokens参数
- 修复`_invoke_bedrock_sync`和`_invoke_bedrock_stream`方法

### ✅ 问题4：前端references为空
**原因**：LLM可能没有在答案中生成引用标记
**解决**：
- 改用JSON格式返回，LLM直接返回结构化的answer和references
- 在prompt中加入JSON schema示例
- 实现JSON解析逻辑，自动移除markdown代码块标记
- 实现降级方案：JSON解析失败或references为空时，自动从stage1_results构建基础引用
- 添加调试日志：`stage2_json_received`、`stage2_json_parsed`、`llm_references_parsed`

### ⚠️ 问题5：JSON格式解析可能失败
**原因**：LLM可能返回带有markdown标记的JSON或格式不规范的JSON
**解决方案**：
- 自动移除```json和```标记
- 使用try-catch捕获解析错误
- 降级方案：解析失败时，将原始响应作为answer，references使用fallback
- 调试：查看`stage2_json_parse_failed`日志

### ⚠️ 问题6：Token统计暂未实现
**现象**：done事件中的tokens为0
**计划**：从Bedrock响应中提取token统计信息

### ⚠️ 问题7：图片名称映射
**注意**：确保Markdown中的图片引用名称与实际文件名一致
**示例**：Markdown中`![](img_001.png)` → 本地文件`img_001.png`

## 🔍 调试技巧

### 1. 查看详细日志
```bash
# 设置日志级别为DEBUG
export LOG_LEVEL=DEBUG
python -m uvicorn app.main:app --reload

# 实时监控Stage 1每个文档的总结
tail -f logs/app.log | grep "document_stage1_completed"

# 实时监控Stage 2的JSON响应
tail -f logs/app.log | grep -E "(stage2_json_received|stage2_json_parsed)"

# 监控引用解析情况
tail -f logs/app.log | grep -E "(llm_references_parsed|no_references_in_llm_response)"

# 监控JSON解析失败
tail -f logs/app.log | grep "stage2_json_parse_failed"
```

### 2. 检查文档是否正确下载
```bash
ls -la /data/cache/documents/{doc_id}/
```

### 3. 测试单个模块
```python
# 测试DocumentProcessor
from app.services.document_processor import DocumentProcessor
processor = DocumentProcessor()
# ...
```

## 📚 相关文档

- [需求文档](docs/requirements-two-stage-query.md)
- [设计文档](docs/design-two-stage-query.md)
- [TODO清单](docs/todo-two-stage-query.md)

## 🎯 下一步

1. **前端集成** - 实现SSE事件监听和引用展示
2. **性能优化** - Stage 1并发处理
3. **Token统计** - 从Bedrock响应提取
4. **缓存优化** - Document处理结果缓存
5. **测试完善** - 端到端集成测试

## 📞 支持

如有问题，请查看：
- 日志文件：`backend/logs/`
- 单元测试：`backend/test_two_stage.py`
- 代码文档：各模块的docstring

---

**实现日期**：2025-01-07
**版本**：v1.0
**状态**：✅ 核心功能完成，可开始集成测试
