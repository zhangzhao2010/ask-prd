# 数据库Schema迁移文档

## 1. 变更概览

### 1.1 变更目标
将数据库Schema从S3存储改为本地存储路径。

### 1.2 影响范围
- **KnowledgeBase表**：移除`s3_bucket`和`s3_prefix`，新增`local_storage_path`
- **Document表**：移除`s3_key`和`s3_key_markdown`，新增`local_pdf_path`、`local_markdown_path`、`local_text_markdown_path`
- **Chunk表**：无变更

### 1.3 数据兼容性
- **新部署**：直接使用新Schema
- **现有数据**：需要执行数据迁移脚本（如果有S3数据需要迁移到本地）

## 2. Schema变更详情

### 2.1 KnowledgeBase表

**移除列**：
```sql
ALTER TABLE knowledge_bases DROP COLUMN s3_bucket;
ALTER TABLE knowledge_bases DROP COLUMN s3_prefix;
```

**新增列**：
```sql
ALTER TABLE knowledge_bases ADD COLUMN local_storage_path VARCHAR;
```

**更新后的DDL**：
```sql
CREATE TABLE knowledge_bases (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    description TEXT,
    local_storage_path VARCHAR,  -- 新增
    opensearch_collection_id VARCHAR,
    opensearch_index_name VARCHAR,
    status VARCHAR NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 Document表

**移除列**：
```sql
ALTER TABLE documents DROP COLUMN s3_key;
ALTER TABLE documents DROP COLUMN s3_key_markdown;
```

**新增列**：
```sql
ALTER TABLE documents ADD COLUMN local_pdf_path VARCHAR;
ALTER TABLE documents ADD COLUMN local_markdown_path VARCHAR;
ALTER TABLE documents ADD COLUMN local_text_markdown_path VARCHAR;
```

**更新后的DDL**：
```sql
CREATE TABLE documents (
    id VARCHAR PRIMARY KEY,
    kb_id VARCHAR NOT NULL,
    filename VARCHAR NOT NULL,
    local_pdf_path VARCHAR,              -- 新增
    local_markdown_path VARCHAR,         -- 新增
    local_text_markdown_path VARCHAR,    -- 新增
    file_size INTEGER,
    page_count INTEGER,
    status VARCHAR NOT NULL DEFAULT 'uploaded',
    error_message TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE
);
```

### 2.3 Chunk表（无变更）

Chunk表Schema保持不变，但以下字段将不再使用：
- `image_s3_key`：图片S3路径（废弃）
- `image_local_path`：图片本地路径（废弃）
- `image_filename`：图片文件名（废弃）
- `image_description`：图片描述（废弃）

原因：图片描述已融入text chunk的content中。

## 3. 迁移脚本

### 3.1 Alembic迁移脚本

**生成迁移脚本**：
```bash
alembic revision --autogenerate -m "Remove S3 columns and add local storage paths"
```

**手动编辑迁移脚本**（`alembic/versions/xxx_remove_s3.py`）：

```python
"""Remove S3 columns and add local storage paths

Revision ID: xxx
Revises: yyy
Create Date: 2025-11-11 10:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = 'xxx'
down_revision = 'yyy'

def upgrade():
    # KnowledgeBase表
    op.add_column('knowledge_bases', sa.Column('local_storage_path', sa.String(), nullable=True))
    op.drop_column('knowledge_bases', 's3_bucket')
    op.drop_column('knowledge_bases', 's3_prefix')

    # Document表
    op.add_column('documents', sa.Column('local_pdf_path', sa.String(), nullable=True))
    op.add_column('documents', sa.Column('local_markdown_path', sa.String(), nullable=True))
    op.add_column('documents', sa.Column('local_text_markdown_path', sa.String(), nullable=True))
    op.drop_column('documents', 's3_key')
    op.drop_column('documents', 's3_key_markdown')

def downgrade():
    # 回滚：恢复S3列
    op.add_column('knowledge_bases', sa.Column('s3_bucket', sa.String(), nullable=True))
    op.add_column('knowledge_bases', sa.Column('s3_prefix', sa.String(), nullable=True))
    op.drop_column('knowledge_bases', 'local_storage_path')

    op.add_column('documents', sa.Column('s3_key', sa.String(), nullable=True))
    op.add_column('documents', sa.Column('s3_key_markdown', sa.String(), nullable=True))
    op.drop_column('documents', 'local_pdf_path')
    op.drop_column('documents', 'local_markdown_path')
    op.drop_column('documents', 'local_text_markdown_path')
```

### 3.2 数据迁移脚本（如有现有数据）

**场景**：如果生产环境已有数据存储在S3，需要执行迁移。

**脚本**：`scripts/migrate_s3_to_local.py`

```python
"""
将S3数据迁移到本地存储
"""
import os
from sqlalchemy.orm import Session
from app.models.database import KnowledgeBase, Document
from app.utils.s3_client import s3_client
from app.core.config import settings

def migrate_s3_to_local(db: Session):
    """
    迁移S3数据到本地

    步骤：
    1. 遍历所有KnowledgeBase，更新local_storage_path
    2. 遍历所有Document，下载PDF和Markdown到本地
    3. 更新数据库记录
    """
    print("开始迁移...")

    # 1. 迁移KnowledgeBase
    kbs = db.query(KnowledgeBase).all()
    for kb in kbs:
        kb.local_storage_path = f"data/knowledge_bases/{kb.id}/"
        print(f"KnowledgeBase {kb.id}: {kb.local_storage_path}")

    db.commit()

    # 2. 迁移Documents
    docs = db.query(Document).all()
    for doc in docs:
        print(f"\n处理文档: {doc.id} - {doc.filename}")

        # 下载PDF
        if doc.s3_key:
            local_pdf_path = f"data/documents/pdfs/{doc.id}.pdf"
            os.makedirs(os.path.dirname(local_pdf_path), exist_ok=True)

            try:
                s3_client.download_file(doc.s3_key, local_pdf_path)
                doc.local_pdf_path = local_pdf_path
                print(f"  ✓ PDF下载成功: {local_pdf_path}")
            except Exception as e:
                print(f"  ✗ PDF下载失败: {e}")
                continue

        # 下载Markdown
        if doc.s3_key_markdown:
            local_md_dir = f"data/documents/markdowns/{doc.id}/"
            local_md_path = f"{local_md_dir}content.md"
            os.makedirs(local_md_dir, exist_ok=True)

            try:
                s3_client.download_file(doc.s3_key_markdown, local_md_path)
                doc.local_markdown_path = local_md_path
                print(f"  ✓ Markdown下载成功: {local_md_path}")

                # 下载图片（如果有）
                # 假设S3路径格式：prefix/converted/{doc_id}/images/*.png
                s3_prefix = doc.s3_key_markdown.rsplit('/', 1)[0] + "/images/"
                images = s3_client.list_objects(s3_prefix)

                for img_s3_key in images:
                    img_filename = os.path.basename(img_s3_key)
                    # 图片下载到与markdown同级目录
                    local_img_path = f"{local_md_dir}{img_filename}"

                    s3_client.download_file(img_s3_key, local_img_path)
                    print(f"  ✓ 图片下载成功: {img_filename}")

            except Exception as e:
                print(f"  ✗ Markdown下载失败: {e}")

    db.commit()
    print("\n迁移完成！")

if __name__ == "__main__":
    from app.core.database import get_db
    db = next(get_db())
    migrate_s3_to_local(db)
```

## 4. 回滚方案

### 4.1 Schema回滚

```bash
alembic downgrade -1
```

### 4.2 数据回滚

**前提**：S3数据未删除

**操作**：
1. 执行Schema回滚
2. 手动删除本地文件：`rm -rf data/documents/`
3. 重启服务，恢复S3模式

**注意**：一旦S3数据被删除，回滚将不可行。

## 5. 迁移步骤

### 5.1 新部署（无现有数据）

1. 创建目录结构：
   ```bash
   mkdir -p data/documents/{pdfs,markdowns,text_markdowns}
   mkdir -p data/cache/{conversions,temp}
   ```

2. 初始化数据库：
   ```bash
   alembic upgrade head
   ```

3. 启动服务

### 5.2 现有部署（有S3数据需迁移）

**迁移前检查**：
```bash
# 检查S3数据
aws s3 ls s3://your-bucket/prds/ --recursive

# 备份数据库
cp data/ask-prd.db data/ask-prd.db.backup.$(date +%Y%m%d)
```

**执行迁移**：
```bash
# 1. 停止服务
systemctl stop ask-prd-backend

# 2. 创建目录
mkdir -p data/documents/{pdfs,markdowns,text_markdowns}

# 3. 执行Schema迁移
alembic upgrade head

# 4. 执行数据迁移
python scripts/migrate_s3_to_local.py

# 5. 验证迁移
python scripts/verify_migration.py

# 6. 启动服务
systemctl start ask-prd-backend
```

### 5.3 验证脚本

`scripts/verify_migration.py`：
```python
"""验证迁移是否成功"""
import os
from sqlalchemy.orm import Session
from app.models.database import Document
from app.core.database import get_db

def verify_migration(db: Session):
    docs = db.query(Document).all()
    success = 0
    failed = 0

    for doc in docs:
        print(f"\n文档: {doc.id} - {doc.filename}")

        # 检查PDF
        if doc.local_pdf_path and os.path.exists(doc.local_pdf_path):
            print(f"  ✓ PDF存在: {doc.local_pdf_path}")
            success += 1
        else:
            print(f"  ✗ PDF不存在: {doc.local_pdf_path}")
            failed += 1

        # 检查Markdown
        if doc.local_markdown_path and os.path.exists(doc.local_markdown_path):
            print(f"  ✓ Markdown存在: {doc.local_markdown_path}")
        else:
            print(f"  ✗ Markdown不存在: {doc.local_markdown_path}")

    print(f"\n总计: {len(docs)} 个文档")
    print(f"成功: {success}")
    print(f"失败: {failed}")

    return failed == 0

if __name__ == "__main__":
    db = next(get_db())
    success = verify_migration(db)
    exit(0 if success else 1)
```

---

**数据库迁移文档完成！**

## 总结

所有4份文档已完成：
1. ✅ `requirements-local-storage.md` - 需求文档
2. ✅ `design-local-storage.md` - 技术设计文档
3. ✅ `api-local-storage.md` - API接口文档
4. ✅ `database-migration.md` - 数据库迁移文档

**下一步**：开始编码实现。
