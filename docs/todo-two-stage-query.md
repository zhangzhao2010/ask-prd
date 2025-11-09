# Two-Stage查询系统开发任务清单

> 版本：v1.0
> 更新时间：2025-01-07
> 预计工时：5-7个工作日

---

## 任务概览

| 阶段 | 任务数 | 预计工时 | 优先级 |
|------|--------|----------|--------|
| Phase 1: 核心模块开发 | 15 | 2天 | P0 |
| Phase 2: 执行器开发 | 8 | 1天 | P0 |
| Phase 3: API集成 | 6 | 1天 | P0 |
| Phase 4: 前端集成 | 5 | 1天 | P1 |
| Phase 5: 测试和优化 | 10 | 1-2天 | P1 |

---

## Phase 1: 核心模块开发

### 1.1 DocumentLoader模块

**文件**：`app/services/document_loader.py`

- [ ] **Task 1.1.1**: 创建DocumentContent数据类
  - 定义dataclass
  - 包含字段：doc_id, doc_name, markdown_path, markdown_text, image_paths
  - 预计工时：15分钟

- [ ] **Task 1.1.2**: 实现DocumentLoader基础类
  - 初始化方法（接收db_session, s3_client, cache_dir）
  - 预计工时：15分钟

- [ ] **Task 1.1.3**: 实现_get_markdown方法
  - 检查本地缓存
  - 从S3下载（如果不存在）
  - 读取文件内容
  - 返回(路径, 内容)
  - 预计工时：30分钟

- [ ] **Task 1.1.4**: 实现_get_images方法
  - 从数据库查询图片chunks
  - 遍历chunks，检查本地缓存
  - 从S3下载（如果不存在）
  - 返回图片路径列表
  - 预计工时：45分钟

- [ ] **Task 1.1.5**: 实现load_document方法
  - 查询document元数据
  - 调用_get_markdown
  - 调用_get_images
  - 构建并返回DocumentContent对象
  - 预计工时：30分钟

- [ ] **Task 1.1.6**: 错误处理和日志
  - 添加异常捕获
  - 添加结构化日志
  - S3下载失败时的处理
  - 预计工时：30分钟

**Phase 1.1小计**：约3小时

---

### 1.2 DocumentProcessor模块

**文件**：`app/services/document_processor.py`

- [ ] **Task 1.2.1**: 创建ProcessedDocument数据类
  - 定义dataclass
  - 包含字段：doc_id, doc_name, doc_short_id, content, references_map
  - 预计工时：15分钟

- [ ] **Task 1.2.2**: 实现split_into_paragraphs方法
  - 按空行分割文本
  - 检测标题行（# 开头）
  - 标题单独成段
  - 过滤空段落
  - 参考demo中的实现
  - 预计工时：45分钟

- [ ] **Task 1.2.3**: 实现build_content方法（Part 1：解析图片位置）
  - 使用正则提取Markdown中的图片引用
  - 记录图片位置和文件名
  - 预计工时：30分钟

- [ ] **Task 1.2.4**: 实现build_content方法（Part 2：构建content）
  - 按位置交替插入文本和图片
  - 生成段落标记（DOC-{short_id}-PARA-X）
  - 生成图片标记（DOC-{short_id}-IMAGE-X）
  - 读取图片文件并base64编码
  - 构建Bedrock API格式的content列表
  - 预计工时：1.5小时

- [ ] **Task 1.2.5**: 实现build_content方法（Part 3：维护references_map）
  - 为每个标记保存原文内容或图片路径
  - 预计工时：30分钟

- [ ] **Task 1.2.6**: 实现process方法
  - 生成doc_short_id（前8位UUID）
  - 调用build_content
  - 构建并返回ProcessedDocument对象
  - 预计工时：30分钟

- [ ] **Task 1.2.7**: 错误处理和日志
  - 图片文件不存在的处理
  - Markdown解析失败的处理
  - 预计工时：30分钟

**Phase 1.2小计**：约4.5小时

---

### 1.3 ReferenceExtractor模块

**文件**：`app/services/reference_extractor.py`

- [ ] **Task 1.3.1**: 创建Reference数据类
  - 定义dataclass
  - 包含字段：ref_id, doc_id, doc_name, chunk_type, content, image_url
  - 预计工时：15分钟

- [ ] **Task 1.3.2**: 实现_extract_ref_ids方法
  - 使用正则提取引用标记：`\[(DOC-[a-f0-9]{8}-(PARA|IMAGE)-\d+)\]`
  - 去重并保持顺序
  - 预计工时：30分钟

- [ ] **Task 1.3.3**: 实现_build_reference方法
  - 解析ref_id，提取doc_short_id和chunk_type
  - 从stage1_results中查找对应文档
  - 从references_map中查找内容
  - 构建Reference对象（区分text和image）
  - 预计工时：1小时

- [ ] **Task 1.3.4**: 实现extract_references方法
  - 调用_extract_ref_ids
  - 遍历ref_ids，调用_build_reference
  - 返回Reference列表
  - 预计工时：30分钟

- [ ] **Task 1.3.5**: 错误处理
  - ref_id解析失败的处理
  - 找不到对应文档的处理
  - 预计工时：15分钟

**Phase 1.3小计**：约2.5小时

---

## Phase 2: 执行器开发

### 2.1 TwoStageExecutor核心逻辑

**文件**：`app/services/agentic_robot/two_stage_executor.py`

- [ ] **Task 2.1.1**: 创建Stage1Result数据类
  - 定义dataclass
  - 包含字段：doc_id, doc_name, doc_short_id, response_text, references_map
  - 预计工时：15分钟

- [ ] **Task 2.1.2**: 实现TwoStageExecutor初始化
  - 接收db_session, s3_client, bedrock_model
  - 初始化DocumentLoader, DocumentProcessor, ReferenceExtractor
  - 预计工时：15分钟

- [ ] **Task 2.1.3**: 实现_build_stage1_prompt方法
  - 构建Stage 1 Prompt模板
  - 填充query和doc_short_id
  - 预计工时：30分钟

- [ ] **Task 2.1.4**: 实现_call_bedrock_stage1方法
  - 调用Bedrock API（使用Strands BedrockModel）
  - 传入图文混排content
  - 获取结构化回复
  - 预计工时：45分钟

- [ ] **Task 2.1.5**: 实现_process_single_document方法
  - 调用DocumentLoader.load_document
  - 调用DocumentProcessor.process
  - 构建Stage 1 Prompt
  - 调用Bedrock
  - 返回Stage1Result
  - 预计工时：1小时

- [ ] **Task 2.1.6**: 实现_build_stage2_prompt方法
  - 构建Stage 2 Prompt模板
  - 汇总所有stage1_results
  - 填充query和doc_count
  - 预计工时：45分钟

- [ ] **Task 2.1.7**: 实现_stage2_synthesize_streaming方法
  - 调用Bedrock API流式接口（使用Strands BedrockModel.stream_async）
  - Yield文本片段
  - 预计工时：1小时

- [ ] **Task 2.1.8**: 实现execute_streaming方法
  - 遍历document_ids，串行处理
  - 推送progress事件
  - 收集stage1_results
  - 调用Stage 2流式生成
  - 推送answer_delta事件
  - 提取引用并推送
  - 推送done事件
  - 错误处理和error事件
  - 预计工时：2小时

**Phase 2.1小计**：约6.5小时

---

## Phase 3: API集成

### 3.1 修改查询接口

**文件**：`app/api/v1/query/routes.py`

- [ ] **Task 3.1.1**: 修改query接口为SSE流式
  - 移除原有Multi-Agent逻辑
  - 使用StreamingResponse
  - 设置Content-Type为text/event-stream
  - 预计工时：1小时

- [ ] **Task 3.1.2**: 集成TwoStageExecutor
  - 初始化executor
  - 从检索结果提取document_ids
  - 调用executor.execute_streaming
  - 转换事件为SSE格式
  - 预计工时：1.5小时

- [ ] **Task 3.1.3**: SSE事件格式化
  - 实现event字段和data字段
  - JSON序列化
  - 添加\n\n分隔符
  - 预计工时：30分钟

**Phase 3.1小计**：约3小时

---

### 3.2 新增图片服务接口

**文件**：`app/api/v1/documents/routes.py`

- [ ] **Task 3.2.1**: 创建图片服务接口
  - 路径：GET /documents/{document_id}/images/{image_filename}
  - 参数验证
  - 预计工时：30分钟

- [ ] **Task 3.2.2**: 实现图片获取逻辑
  - 构建本地路径
  - 检查文件是否存在
  - 从S3下载（如果不存在）
  - 判断Content-Type
  - 返回FileResponse
  - 预计工时：1小时

- [ ] **Task 3.2.3**: 添加缓存头
  - Cache-Control: public, max-age=86400
  - 预计工时：15分钟

**Phase 3.2小计**：约1.5小时

---

## Phase 4: 前端集成（可选，如果需要修改前端）

### 4.1 查询页面修改

**文件**：`frontend/src/pages/QueryPage.tsx`（假设）

- [ ] **Task 4.1.1**: 实现SSE事件监听
  - 使用EventSource连接后端
  - 监听progress, answer_delta, references, done, error事件
  - 预计工时：1小时

- [ ] **Task 4.1.2**: 实现进度显示
  - 显示"正在处理文档 X/N"
  - 预计工时：30分钟

- [ ] **Task 4.1.3**: 实现流式答案显示
  - 累积answer_delta事件的text
  - 实时渲染Markdown
  - 预计工时：45分钟

- [ ] **Task 4.1.4**: 实现引用列表组件
  - 区分text和image类型
  - 文本引用：显示内容
  - 图片引用：显示图片（使用/api/v1/documents/.../images/...）
  - 预计工时：1.5小时

- [ ] **Task 4.1.5**: 错误提示
  - 监听error事件
  - 显示友好的错误信息
  - 预计工时：30分钟

**Phase 4.1小计**：约4.5小时

---

## Phase 5: 测试和优化

### 5.1 单元测试

- [ ] **Task 5.1.1**: DocumentLoader单元测试
  - Mock S3客户端
  - 测试缓存命中和未命中
  - 测试下载失败的处理
  - 预计工时：1.5小时

- [ ] **Task 5.1.2**: DocumentProcessor单元测试
  - 测试split_into_paragraphs
  - 测试build_content（文本和图片交替）
  - 测试references_map构建
  - 预计工时：2小时

- [ ] **Task 5.1.3**: ReferenceExtractor单元测试
  - 测试_extract_ref_ids（各种引用格式）
  - 测试_build_reference
  - 测试找不到引用的情况
  - 预计工时：1小时

- [ ] **Task 5.1.4**: TwoStageExecutor单元测试
  - Mock子模块
  - 测试execute_streaming流程
  - 测试错误处理
  - 预计工时：2小时

**Phase 5.1小计**：约6.5小时

---

### 5.2 集成测试

- [ ] **Task 5.2.1**: 端到端测试：单个Document查询
  - 准备测试数据（PDF + Markdown + 图片）
  - 调用查询接口
  - 验证SSE事件顺序和内容
  - 验证引用正确性
  - 预计工时：2小时

- [ ] **Task 5.2.2**: 端到端测试：多个Documents查询
  - 准备3个测试文档
  - 验证progress事件
  - 验证Stage 2综合答案
  - 验证跨文档引用
  - 预计工时：2小时

- [ ] **Task 5.2.3**: 端到端测试：图片引用
  - 查询包含图片的文档
  - 验证图片标记提取
  - 验证图片URL正确性
  - 访问图片接口，验证图片加载
  - 预计工时：1.5小时

- [ ] **Task 5.2.4**: 错误场景测试
  - S3文件不存在
  - Bedrock API超时
  - 所有Documents处理失败
  - 预计工时：1.5小时

**Phase 5.2小计**：约7小时

---

### 5.3 性能测试和优化

- [ ] **Task 5.3.1**: 性能基准测试
  - 测试单个Document处理时间
  - 测试3个Documents的端到端延迟
  - 测试流式输出首字符延迟
  - 预计工时：1小时

- [ ] **Task 5.3.2**: 优化Prompt长度
  - 评估Stage 1 Prompt的token数
  - 评估Stage 2 Prompt的token数
  - 优化Prompt模板，减少无用词汇
  - 预计工时：1小时

**Phase 5.3小计**：约2小时

---

## 关键里程碑

| 里程碑 | 完成标志 | 预计时间 |
|--------|----------|----------|
| M1: 核心模块完成 | Phase 1所有任务完成 | Day 2 |
| M2: 执行器完成 | Phase 2所有任务完成 | Day 3 |
| M3: API集成完成 | Phase 3所有任务完成 | Day 4 |
| M4: 测试通过 | Phase 5.1和5.2完成 | Day 6 |
| M5: 上线就绪 | 所有任务完成 | Day 7 |

---

## 风险和应对

### 风险1：Bedrock API调用延迟过高

**影响**：用户体验差，查询响应慢

**应对**：
- 在Prompt中强调简洁回复
- 考虑使用更小的模型（Claude Haiku）处理Stage 1
- 引入超时机制，超时则跳过该Document

### 风险2：图片过多导致Token超限

**影响**：Bedrock API调用失败

**应对**：
- 限制单个Document的图片数量（最多10张）
- 压缩图片尺寸（缩小到1024x1024以内）
- 如果超限，分批发送给Bedrock

### 风险3：S3下载速度慢

**影响**：Stage 1处理时间过长

**应对**：
- 优先使用本地缓存
- 使用S3 Transfer Acceleration
- 考虑在本地预先同步常用文档

---

## 开发顺序建议

1. **优先开发核心模块**（Phase 1），这些模块相对独立，可以并行开发和测试
2. **然后开发执行器**（Phase 2），依赖核心模块
3. **再集成API**（Phase 3），依赖执行器
4. **测试贯穿始终**（Phase 5），每完成一个模块就进行单元测试
5. **前端集成**（Phase 4）可以与Phase 3并行，由前端开发人员负责

---

## 每日计划示例

### Day 1
- 上午：Task 1.1.1 - 1.1.6（DocumentLoader）
- 下午：Task 1.2.1 - 1.2.3（DocumentProcessor Part 1）

### Day 2
- 上午：Task 1.2.4 - 1.2.7（DocumentProcessor Part 2 + 错误处理）
- 下午：Task 1.3.1 - 1.3.5（ReferenceExtractor）

### Day 3
- 上午：Task 2.1.1 - 2.1.5（TwoStageExecutor Part 1）
- 下午：Task 2.1.6 - 2.1.8（TwoStageExecutor Part 2）

### Day 4
- 上午：Task 3.1.1 - 3.1.3（查询接口修改）
- 下午：Task 3.2.1 - 3.2.3（图片服务接口）

### Day 5-6
- 单元测试和集成测试（Phase 5.1 + 5.2）

### Day 7
- 性能测试和优化（Phase 5.3）
- Bug修复

---

## 验收标准

### 功能验收

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

### 性能验收

- [ ] 单个Document处理时间 < 5秒
- [ ] 流式输出首字符延迟 < 1秒
- [ ] 3个Documents的完整查询 < 20秒

### 用户体验验收

- [ ] 进度提示清晰（例如：正在处理文档 1/3）
- [ ] 答案流式显示，无卡顿感
- [ ] 引用列表格式美观，易于理解
- [ ] 图片可以正常加载和展示
- [ ] 错误提示友好

---

## 后续优化任务（非本期）

- [ ] Stage 1改为并发处理（使用asyncio + Semaphore）
- [ ] 引入缓存机制（相同Document的分段结果）
- [ ] 支持多轮对话（保持上下文）
- [ ] 引入Reranker提升检索精度
- [ ] 添加用户反馈机制（引用是否有用）
- [ ] 支持更多文档格式（Word, Excel）
- [ ] 支持视频和音频内容理解

---
