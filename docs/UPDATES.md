# 文档更新说明

本文档记录了设计文档与实际实现的差异，以及后续的架构调整。

## 2025-12-01: local_storage_path 字段移除

### 背景

在早期设计文档中（`requirements-local-storage.md`, `design-local-storage.md`, `api-local-storage.md`, `database-migration.md`），计划为 `knowledge_bases` 表添加 `local_storage_path` 字段，用于存储知识库的本地目录路径（如 `data/knowledge_bases/{kb_id}/`）。

### 实际实现

在实际开发过程中发现：

1. **知识库是逻辑概念**
   - 知识库主要关联 OpenSearch 索引
   - 不需要独立的物理存储目录

2. **文档缓存策略**
   - 采用了**文档级缓存**：`/data/cache/documents/{document_id}/`
   - 而不是知识库级缓存：`/data/knowledge_bases/{kb_id}/`

3. **S3 + 本地缓存混合架构**
   - S3 作为唯一真实数据源
   - 本地缓存用于加速访问，可安全清理
   - 详见 `CLAUDE.md` 中的"本地文件缓存策略"

### 最终决策

- ❌ **移除** `knowledge_bases.local_storage_path` 字段
- ✅ **保留** `documents.local_pdf_path` 和 `documents.local_markdown_path`（文档级缓存路径）
- ✅ **清理** `/data/knowledge_bases/` 目录下的空目录

### 影响的文档

以下文档中提到的 `local_storage_path` 字段已不再适用：

1. `docs/requirements-local-storage.md` - 第551行
2. `docs/design-local-storage.md` - 第75行
3. `docs/api-local-storage.md` - 第35行
4. `docs/database-migration.md` - 多处

**注意**: 这些文档保留作为历史设计参考，但实际实现以当前代码和 `CLAUDE.md` 为准。

### 迁移脚本

已执行的迁移脚本：
- `scripts/migrations/completed/migrate_remove_local_storage_path.py`
- 执行时间：2025-12-01 17:47:45
- 状态：✅ 成功完成

### 数据库当前Schema

`knowledge_bases` 表的最终字段列表：
```
- id
- name
- description
- opensearch_collection_id
- opensearch_index_name
- status
- owner_id
- visibility
- created_at
- updated_at
```

### 相关 Commit

- `e941307` - refactor(backend): 移除废弃的local_storage_path字段

---

## 最佳实践

在参考旧的设计文档时，请：

1. ✅ 优先参考 `CLAUDE.md` 和当前代码实现
2. ✅ 查看 `docs/UPDATES.md` 了解设计变更
3. ✅ 旧设计文档仅作为历史参考

---

*最后更新：2025-12-01*
