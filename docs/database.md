# ASK-PRD 数据库设计文档

> 版本：v1.0
> 更新时间：2025-01-20

---

## 一、数据库选型

### 1.1 SQLite

**用途**：元数据存储

**选择原因**：
- 零配置，无需独立数据库服务
- 适合单机部署场景
- 事务支持，ACID保证
- Python原生支持

**版本要求**：SQLite 3.35+

### 1.2 Amazon OpenSearch Serverless

**用途**：向量存储和检索

**选择原因**：
- 原生支持向量检索（kNN）
- 支持BM25关键词检索
- Serverless模式，按需付费
- 与AWS生态集成

---

## 二、SQLite Schema设计

### 2.1 表结构总览

```sql
knowledge_bases      -- 知识库表
documents            -- 文档表
chunks               -- 文本/图片块表（统一）
sync_tasks           -- 同步任务表
```

---

### 2.2 详细Schema

#### 2.2.1 knowledge_bases - 知识库表

```sql
CREATE TABLE knowledge_bases (
    id TEXT PRIMARY KEY,                    -- UUID格式
    name TEXT NOT NULL,                     -- 知识库名称
    description TEXT,                       -- 描述信息
    s3_bucket TEXT NOT NULL,                -- S3桶名
    s3_prefix TEXT NOT NULL,                -- S3路径前缀，如 "prds/product-a/"
    opensearch_collection_id TEXT,          -- OpenSearch Collection ID
    opensearch_index_name TEXT,             -- OpenSearch Index名称
    status TEXT NOT NULL DEFAULT 'active',  -- active | deleted
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE UNIQUE INDEX idx_kb_name ON knowledge_bases(name);
CREATE INDEX idx_kb_status ON knowledge_bases(status);
```

**字段说明**：
- `s3_prefix`: 必须以 `/` 结尾，如 `prds/product-a/`
- `opensearch_index_name`: 格式为 `kb_{kb_id}_index`
- `status`: 软删除标记

**示例数据**：
```json
{
    "id": "kb-550e8400-e29b-41d4-a716-446655440000",
    "name": "产品PRD知识库",
    "description": "包含产品迭代的所有PRD文档",
    "s3_bucket": "my-prd-bucket",
    "s3_prefix": "prds/product-a/",
    "opensearch_collection_id": "abc123xyz",
    "opensearch_index_name": "kb_550e8400_index",
    "status": "active",
    "created_at": "2025-01-20T10:00:00Z"
}
```

---

#### 2.2.2 documents - 文档表

```sql
CREATE TABLE documents (
    id TEXT PRIMARY KEY,                    -- UUID格式
    kb_id TEXT NOT NULL,                    -- 关联知识库ID
    filename TEXT NOT NULL,                 -- 原始文件名，如 "PRD_登录_v1.2.pdf"
    s3_key TEXT NOT NULL,                   -- S3完整路径，如 "prds/product-a/PRD_登录_v1.2.pdf"
    s3_key_markdown TEXT,                   -- Markdown文件S3路径
    local_markdown_path TEXT,               -- 本地Markdown缓存路径（可选，可推导）
    file_size INTEGER,                      -- 文件大小（字节）
    page_count INTEGER,                     -- PDF页数
    status TEXT NOT NULL DEFAULT 'uploaded', -- uploaded | processing | completed | failed
    error_message TEXT,                     -- 处理失败时的错误信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX idx_documents_kb_id ON documents(kb_id);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_filename ON documents(filename);
```

**字段说明**：
- `s3_key_markdown`: 转换后的Markdown文件S3路径（必须），如 `prds/product-a/converted/doc-xxx/content.md`
- `local_markdown_path`: 本地Markdown缓存路径（可选），如 `/data/cache/documents/doc-xxx/content.md`
  - 用于记录文件是否已缓存到本地
  - 可为空，使用时可从`document_id`推导：`/data/cache/documents/{document_id}/content.md`
  - 优先使用此字段检查缓存，为空则从S3下载
- ~~`local_images_dir`~~: **已移除**（冗余字段）
  - 原因：每个图片chunk已有完整的`image_s3_key`和`image_local_path`
  - 图片目录可以从`document_id`推导：`/data/cache/documents/{document_id}/images/`
- `status` 状态流转：
  - `uploaded`: 已上传到S3，未处理
  - `processing`: 正在处理（Marker转换中）
  - `completed`: 处理完成，已向量化
  - `failed`: 处理失败

**路径推导规则**：
```python
# S3路径推导
def get_s3_paths(kb_prefix: str, document_id: str):
    return {
        "markdown": f"{kb_prefix}/converted/{document_id}/content.md",
        "images_dir": f"{kb_prefix}/converted/{document_id}/images/",
        # 具体图片路径存储在chunks表
    }

# 本地缓存路径推导
def get_local_paths(document_id: str):
    base_dir = f"/data/cache/documents/{document_id}"
    return {
        "markdown": f"{base_dir}/content.md",
        "images_dir": f"{base_dir}/images/",
        # 具体图片路径存储在chunks表
    }
```

**示例数据**：
```json
{
    "id": "doc-660e8400-e29b-41d4-a716-446655440001",
    "kb_id": "kb-550e8400-e29b-41d4-a716-446655440000",
    "filename": "PRD_登录注册_v1.2.pdf",
    "s3_key": "prds/product-a/PRD_登录注册_v1.2.pdf",
    "s3_key_markdown": "prds/product-a/converted/doc-660e8400/content.md",
    "local_markdown_path": "/data/cache/documents/doc-660e8400/content.md",
    "file_size": 2048576,
    "page_count": 15,
    "status": "completed",
    "error_message": null,
    "created_at": "2025-01-20T10:00:00Z",
    "updated_at": "2025-01-20T10:05:00Z"
}
```

**注意**：
- 图片相关路径不在documents表存储
- S3图片路径格式：`prds/product-a/converted/doc-660e8400/images/img_001.png`（存储在chunks表）
- 本地图片路径格式：`/data/cache/documents/doc-660e8400/images/img_001.png`（存储在chunks表）
```

---

#### 2.2.3 chunks - 文本/图片块表

```sql
CREATE TABLE chunks (
    id TEXT PRIMARY KEY,                    -- UUID格式，与OpenSearch的document ID一致
    document_id TEXT NOT NULL,              -- 关联文档ID
    kb_id TEXT NOT NULL,                    -- 关联知识库ID（冗余，便于查询）
    chunk_type TEXT NOT NULL,               -- 'text' | 'image'
    chunk_index INTEGER NOT NULL,           -- 在文档中的顺序（从0开始）

    -- 文本chunk字段
    content TEXT,                           -- 纯文本内容（仅文本chunk）
    content_with_context TEXT,              -- 包含上下文的完整内容（用于生成embedding）
    char_start INTEGER,                     -- 在原文档中的起始字符位置
    char_end INTEGER,                       -- 在原文档中的结束字符位置

    -- 图片chunk字段
    image_filename TEXT,                    -- 图片文件名（仅图片chunk）
    image_s3_key TEXT,                      -- 图片S3路径（持久化存储）
    image_local_path TEXT,                  -- 图片本地缓存路径（可能不存在）
    image_description TEXT,                 -- Claude生成的图片描述
    image_type TEXT,                        -- flowchart | prototype | mindmap | screenshot | diagram | other
    image_width INTEGER,                    -- 图片宽度（像素）
    image_height INTEGER,                   -- 图片高度（像素）

    token_count INTEGER,                    -- content_with_context的token数量
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX idx_chunks_document_id ON chunks(document_id);
CREATE INDEX idx_chunks_kb_id ON chunks(kb_id);
CREATE INDEX idx_chunks_type ON chunks(chunk_type);
CREATE INDEX idx_chunks_doc_index ON chunks(document_id, chunk_index);
```

**字段说明**：
- 文本chunk和图片chunk使用同一张表，通过`chunk_type`区分
- `content`: 仅文本chunk使用，存储原始文本片段
- `content_with_context`: 两种chunk都使用，图片chunk存储图片描述+上下文
- `char_start/char_end`: 仅文本chunk使用，用于定位原文位置
- `image_*`: 仅图片chunk使用
- `image_s3_key`: 图片的S3持久化路径（必须），格式如 `prds/product-a/converted/doc-xxx/images/img_001.png`
- `image_local_path`: 图片的本地缓存路径（可选），如果缓存不存在则从S3下载

**示例数据 - 文本chunk**：
```json
{
    "id": "chunk-770e8400-e29b-41d4-a716-446655440002",
    "document_id": "doc-660e8400-e29b-41d4-a716-446655440001",
    "kb_id": "kb-550e8400-e29b-41d4-a716-446655440000",
    "chunk_type": "text",
    "chunk_index": 5,
    "content": "v1.0版本支持手机号+短信验证码登录...",
    "content_with_context": "v1.0版本支持手机号+短信验证码登录...\n\n[参考流程图: 登录流程示意图]",
    "char_start": 1250,
    "char_end": 1450,
    "image_filename": null,
    "token_count": 85,
    "created_at": "2025-01-20T10:05:00Z"
}
```

**示例数据 - 图片chunk**：
```json
{
    "id": "chunk-880e8400-e29b-41d4-a716-446655440003",
    "document_id": "doc-660e8400-e29b-41d4-a716-446655440001",
    "kb_id": "kb-550e8400-e29b-41d4-a716-446655440000",
    "chunk_type": "image",
    "chunk_index": 6,
    "content": null,
    "content_with_context": "上文提到v1.0登录流程...\n\n图片描述：这是一张登录流程图，包含三个主要步骤：1.用户输入手机号 2.获取验证码 3.验证通过进入首页。流程图使用泳道图展示，包含用户端、服务端、短信网关三个角色。",
    "char_start": null,
    "char_end": null,
    "image_filename": "login_flow_v1.png",
    "image_s3_key": "prds/product-a/converted/PRD_登录注册_v1.2/images/login_flow_v1.png",
    "image_local_path": "/data/cache/documents/doc-660e8400/images/login_flow_v1.png",
    "image_description": "这是一张登录流程图，包含三个主要步骤：1.用户输入手机号...",
    "image_type": "flowchart",
    "image_width": 1200,
    "image_height": 800,
    "token_count": 120,
    "created_at": "2025-01-20T10:05:00Z"
}
```

---

#### 2.2.4 sync_tasks - 同步任务表

```sql
CREATE TABLE sync_tasks (
    id TEXT PRIMARY KEY,                    -- UUID格式
    kb_id TEXT NOT NULL,                    -- 关联知识库ID
    task_type TEXT NOT NULL,                -- full_sync | incremental | delete
    document_ids TEXT,                      -- JSON数组，需要同步的文档ID列表
    status TEXT NOT NULL DEFAULT 'pending', -- pending | running | completed | failed | partial_success
    progress INTEGER DEFAULT 0,             -- 进度百分比 0-100
    current_step TEXT,                      -- 当前步骤描述，如 "正在处理文档 3/10"
    total_documents INTEGER DEFAULT 0,      -- 总文档数
    processed_documents INTEGER DEFAULT 0,  -- 已处理文档数
    failed_documents INTEGER DEFAULT 0,     -- 失败文档数
    error_message TEXT,                     -- 任务级别错误信息
    started_at TIMESTAMP,                   -- 任务开始时间
    completed_at TIMESTAMP,                 -- 任务完成时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX idx_sync_tasks_kb_id ON sync_tasks(kb_id);
CREATE INDEX idx_sync_tasks_status ON sync_tasks(status);
CREATE INDEX idx_sync_tasks_created ON sync_tasks(created_at DESC);
```

**字段说明**：
- `task_type`:
  - `full_sync`: 全量同步（处理所有uploaded状态的文档）
  - `incremental`: 增量同步（处理指定的文档）
  - `delete`: 删除任务（清理文档相关数据）
- `document_ids`: JSON数组格式，如 `["doc-xxx", "doc-yyy"]`
- `status`:
  - `pending`: 待执行
  - `running`: 执行中
  - `completed`: 全部成功
  - `failed`: 任务失败
  - `partial_success`: 部分文档失败

**示例数据**：
```json
{
    "id": "task-990e8400-e29b-41d4-a716-446655440004",
    "kb_id": "kb-550e8400-e29b-41d4-a716-446655440000",
    "task_type": "full_sync",
    "document_ids": "[\"doc-660e8400-e29b-41d4-a716-446655440001\", \"doc-660e8400-e29b-41d4-a716-446655440002\"]",
    "status": "running",
    "progress": 65,
    "current_step": "正在向量化文档 2/3",
    "total_documents": 3,
    "processed_documents": 2,
    "failed_documents": 0,
    "error_message": null,
    "started_at": "2025-01-20T10:00:00Z",
    "completed_at": null,
    "created_at": "2025-01-20T09:59:00Z"
}
```

---

## 三、OpenSearch Index设计

### 3.1 Index Mapping

每个知识库对应一个独立的Index，Index名称格式：`kb_{kb_id}_index`

```json
{
    "settings": {
        "index": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "knn": true,
            "knn.algo_param.ef_search": 512
        }
    },
    "mappings": {
        "properties": {
            "chunk_id": {
                "type": "keyword"
            },
            "document_id": {
                "type": "keyword"
            },
            "kb_id": {
                "type": "keyword"
            },
            "chunk_type": {
                "type": "keyword"
            },
            "chunk_index": {
                "type": "integer"
            },
            "content": {
                "type": "text",
                "analyzer": "standard"
            },
            "content_with_context": {
                "type": "text",
                "analyzer": "standard"
            },
            "embedding": {
                "type": "knn_vector",
                "dimension": 1024,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "nmslib",
                    "parameters": {
                        "ef_construction": 512,
                        "m": 16
                    }
                }
            },
            "created_at": {
                "type": "date"
            }
        }
    }
}
```

**字段说明**：
- `chunk_id`: 与SQLite中的chunk.id一致
- `embedding`: 向量字段，维度取决于使用的Embedding模型
  - Amazon Titan Embeddings V2: 1024维
  - Cohere Embed: 1024维
- `content`: 用于BM25检索
- `content_with_context`: 用于生成embedding的完整内容

### 3.2 示例文档

**文本chunk**：
```json
{
    "chunk_id": "chunk-770e8400-e29b-41d4-a716-446655440002",
    "document_id": "doc-660e8400-e29b-41d4-a716-446655440001",
    "kb_id": "kb-550e8400-e29b-41d4-a716-446655440000",
    "chunk_type": "text",
    "chunk_index": 5,
    "content": "v1.0版本支持手机号+短信验证码登录...",
    "content_with_context": "v1.0版本支持手机号+短信验证码登录...\n\n[参考流程图: 登录流程示意图]",
    "embedding": [0.123, -0.456, 0.789, ...],  // 1024维向量
    "created_at": "2025-01-20T10:05:00Z"
}
```

**图片chunk**：
```json
{
    "chunk_id": "chunk-880e8400-e29b-41d4-a716-446655440003",
    "document_id": "doc-660e8400-e29b-41d4-a716-446655440001",
    "kb_id": "kb-550e8400-e29b-41d4-a716-446655440000",
    "chunk_type": "image",
    "chunk_index": 6,
    "content": "登录流程图",
    "content_with_context": "上文提到v1.0登录流程...\n\n图片描述：这是一张登录流程图，包含三个主要步骤...",
    "embedding": [0.234, -0.567, 0.890, ...],
    "created_at": "2025-01-20T10:05:00Z"
}
```

---

## 四、数据一致性保证

### 4.1 级联删除

删除知识库时，自动删除：
1. SQLite中的关联数据（通过FOREIGN KEY CASCADE）
2. OpenSearch中的Index
3. S3中的文件（需手动实现）
4. 本地缓存文件（需手动实现）

### 4.2 事务处理

**示例：文档删除事务**
```python
def delete_documents(kb_id: str, document_ids: List[str]):
    # 开始事务
    with db.transaction():
        # 1. 从SQLite删除（自动级联删除chunks）
        db.execute(
            "DELETE FROM documents WHERE id IN (?)",
            document_ids
        )

        # 2. 从OpenSearch删除
        chunk_ids = db.query(
            "SELECT id FROM chunks WHERE document_id IN (?)",
            document_ids
        )
        opensearch_client.bulk_delete(chunk_ids)

        # 3. 从S3删除
        for doc_id in document_ids:
            doc = db.get_document(doc_id)
            s3_client.delete_objects([
                doc.s3_key,
                doc.s3_key_markdown
            ])

        # 4. 删除本地缓存
        for doc_id in document_ids:
            shutil.rmtree(f"/data/cache/documents/{doc_id}")
```

### 4.3 数据备份

**SQLite备份**：
```bash
# 每日备份脚本
sqlite3 /data/aks-prd.db ".backup '/data/backups/aks-prd-$(date +%Y%m%d).db'"

# 保留最近7天的备份
find /data/backups -name "aks-prd-*.db" -mtime +7 -delete
```

---

## 五、查询优化

### 5.1 常用查询

**查询1：获取知识库的所有文档（分页）**
```sql
SELECT id, filename, status, file_size, page_count, created_at
FROM documents
WHERE kb_id = ? AND status != 'deleted'
ORDER BY created_at DESC
LIMIT ? OFFSET ?;
```

**查询2：获取文档的所有chunk（按顺序）**
```sql
SELECT id, chunk_type, chunk_index, content, image_filename
FROM chunks
WHERE document_id = ?
ORDER BY chunk_index ASC;
```

**查询3：正在运行的同步任务**
```sql
SELECT id, progress, current_step, total_documents, processed_documents
FROM sync_tasks
WHERE status = 'running'
ORDER BY started_at DESC;
```

### 5.2 性能考虑

- 所有外键字段都建立了索引
- 高频查询字段（status, created_at）建立索引
- 使用连接池避免频繁创建连接
- 读多写少的场景，考虑使用WAL模式

```python
# 启用WAL模式
db.execute("PRAGMA journal_mode=WAL")
```

---

## 六、数据迁移路径

### 6.1 从SQLite迁移到RDS（未来）

**迁移脚本示例**：
```python
def migrate_to_rds():
    sqlite_conn = sqlite3.connect('/data/aks-prd.db')
    pg_conn = psycopg2.connect(RDS_CONNECTION_STRING)

    # 迁移表结构（需调整SQLite特有语法）
    # 迁移数据
    tables = ['knowledge_bases', 'documents', 'chunks',
              'sync_tasks']

    for table in tables:
        rows = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()
        # 批量插入到PostgreSQL
        pg_conn.bulk_insert(table, rows)
```

**Schema调整**：
- `TEXT` → `VARCHAR` 或 `TEXT`
- `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` → `TIMESTAMP DEFAULT NOW()`
- 添加自增主键（可选）

---

## 七、维护建议

### 7.1 定期清理

**清理已完成的同步任务**（保留最近1个月）：
```sql
DELETE FROM sync_tasks
WHERE status IN ('completed', 'failed')
  AND completed_at < datetime('now', '-1 month');
```

### 7.2 数据统计

```sql
-- 知识库统计
SELECT
    kb.name,
    COUNT(DISTINCT d.id) as document_count,
    COUNT(c.id) as chunk_count,
    SUM(d.file_size) as total_size
FROM knowledge_bases kb
LEFT JOIN documents d ON kb.id = d.kb_id
LEFT JOIN chunks c ON d.id = c.document_id
WHERE kb.status = 'active'
GROUP BY kb.id;
```

---

## 八、附录

### 8.1 SQLite配置

```python
# 推荐配置
import sqlite3

conn = sqlite3.connect(
    '/data/aks-prd.db',
    check_same_thread=False,  # 允许多线程
    timeout=30.0              # 锁超时30秒
)

# 性能优化
conn.execute("PRAGMA journal_mode=WAL")          # 启用WAL
conn.execute("PRAGMA synchronous=NORMAL")        # 平衡性能和安全
conn.execute("PRAGMA cache_size=-64000")         # 64MB缓存
conn.execute("PRAGMA temp_store=MEMORY")         # 临时表在内存
conn.execute("PRAGMA mmap_size=268435456")       # 256MB内存映射
```

### 8.2 完整建表脚本

见附件：`database_schema.sql`
