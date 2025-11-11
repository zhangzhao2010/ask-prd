"""
SQLAlchemy数据库模型
基于docs/database.md设计
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, Text, DateTime, ForeignKey, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class KnowledgeBase(Base):
    """知识库表"""
    __tablename__ = "knowledge_bases"

    id = Column(String, primary_key=True)  # UUID格式
    name = Column(String, nullable=False, unique=True)
    description = Column(Text)
    local_storage_path = Column(String)  # 本地存储路径，例如: data/knowledge_bases/{kb_id}/
    opensearch_collection_id = Column(String)
    opensearch_index_name = Column(String)
    status = Column(String, nullable=False, default="active")  # active | deleted
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # 关系
    documents = relationship("Document", back_populates="knowledge_base", cascade="all, delete-orphan")
    chunks = relationship("Chunk", back_populates="knowledge_base", cascade="all, delete-orphan")
    sync_tasks = relationship("SyncTask", back_populates="knowledge_base", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<KnowledgeBase(id={self.id}, name={self.name})>"


# 索引
Index("idx_kb_status", KnowledgeBase.status)


class Document(Base):
    """文档表"""
    __tablename__ = "documents"

    id = Column(String, primary_key=True)  # UUID格式
    kb_id = Column(String, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    local_pdf_path = Column(String)  # 本地PDF路径: data/documents/pdfs/{document_id}.pdf
    local_markdown_path = Column(String)  # 本地原始Markdown路径: data/documents/markdowns/{document_id}/content.md
    local_text_markdown_path = Column(String)  # 本地纯文本Markdown路径: data/documents/text_markdowns/{document_id}.md
    file_size = Column(Integer)  # 文件大小（字节）
    page_count = Column(Integer)  # PDF页数
    status = Column(String, nullable=False, default="uploaded")  # uploaded | processing | completed | failed
    error_message = Column(Text)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # 关系
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document(id={self.id}, filename={self.filename}, status={self.status})>"


# 索引
Index("idx_documents_kb_id", Document.kb_id)
Index("idx_documents_status", Document.status)
Index("idx_documents_filename", Document.filename)


class Chunk(Base):
    """文本/图片块表（统一）"""
    __tablename__ = "chunks"

    id = Column(String, primary_key=True)  # UUID格式，与OpenSearch的document ID一致
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    kb_id = Column(String, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False)  # 冗余，便于查询
    chunk_type = Column(String, nullable=False)  # 'text' | 'image'
    chunk_index = Column(Integer, nullable=False)  # 在文档中的顺序（从0开始）

    # 文本chunk字段
    content = Column(Text)  # 纯文本内容（仅文本chunk）
    content_with_context = Column(Text)  # 包含上下文的完整内容（用于生成embedding）
    char_start = Column(Integer)  # 在原文档中的起始字符位置
    char_end = Column(Integer)  # 在原文档中的结束字符位置

    # 图片chunk字段
    image_filename = Column(String)  # 图片文件名（仅图片chunk）
    image_s3_key = Column(String)  # 图片S3路径（持久化存储）
    image_local_path = Column(String)  # 图片本地缓存路径（可选）
    image_description = Column(Text)  # Claude生成的图片描述
    image_type = Column(String)  # flowchart | prototype | mindmap | screenshot | diagram | other
    image_width = Column(Integer)  # 图片宽度（像素）
    image_height = Column(Integer)  # 图片高度（像素）

    token_count = Column(Integer)  # content_with_context的token数量
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # 关系
    document = relationship("Document", back_populates="chunks")
    knowledge_base = relationship("KnowledgeBase", back_populates="chunks")

    def __repr__(self):
        return f"<Chunk(id={self.id}, type={self.chunk_type}, index={self.chunk_index})>"


# 索引
Index("idx_chunks_document_id", Chunk.document_id)
Index("idx_chunks_kb_id", Chunk.kb_id)
Index("idx_chunks_type", Chunk.chunk_type)
Index("idx_chunks_doc_index", Chunk.document_id, Chunk.chunk_index)


class SyncTask(Base):
    """同步任务表"""
    __tablename__ = "sync_tasks"

    id = Column(String, primary_key=True)  # UUID格式
    kb_id = Column(String, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    task_type = Column(String, nullable=False)  # full_sync | incremental | delete
    document_ids = Column(Text)  # JSON数组，需要同步的文档ID列表
    status = Column(String, nullable=False, default="pending")  # pending | running | completed | failed | partial_success
    progress = Column(Integer, default=0)  # 进度百分比 0-100
    current_step = Column(String)  # 当前步骤描述
    total_documents = Column(Integer, default=0)
    processed_documents = Column(Integer, default=0)
    failed_documents = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # 关系
    knowledge_base = relationship("KnowledgeBase", back_populates="sync_tasks")

    def __repr__(self):
        return f"<SyncTask(id={self.id}, type={self.task_type}, status={self.status})>"


# 索引
Index("idx_sync_tasks_kb_id", SyncTask.kb_id)
Index("idx_sync_tasks_status", SyncTask.status)
Index("idx_sync_tasks_created", SyncTask.created_at.desc())
