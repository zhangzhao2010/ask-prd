"""
文档管理Service
业务逻辑层
"""
import uuid
from typing import List, Optional, Tuple, BinaryIO
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.database import KnowledgeBase, Document
from app.models.schemas import DocumentCreate, DocumentUpdate
from app.core.logging import get_logger
from app.core.errors import (
    DocumentNotFoundError,
    KnowledgeBaseNotFoundError,
    S3UploadError
)
from app.utils.s3_client import s3_client

logger = get_logger(__name__)


class DocumentService:
    """文档管理服务"""

    @staticmethod
    def upload_document(
        db: Session,
        kb_id: str,
        file: BinaryIO,
        filename: str,
        file_size: int,
        content_type: str = "application/pdf"
    ) -> Document:
        """
        上传文档到S3并创建记录

        Args:
            db: 数据库会话
            kb_id: 知识库ID
            file: 文件对象
            filename: 文件名
            file_size: 文件大小
            content_type: 文件MIME类型

        Returns:
            创建的文档对象

        Raises:
            KnowledgeBaseNotFoundError: 知识库不存在
            S3UploadError: S3上传失败
        """
        # 1. 检查知识库是否存在
        kb = db.query(KnowledgeBase).filter(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.status == "active"
        ).first()

        if not kb:
            raise KnowledgeBaseNotFoundError(kb_id)

        # 2. 生成文档ID和S3路径
        doc_id = f"doc-{uuid.uuid4()}"
        s3_key = f"{kb.s3_prefix}documents/{doc_id}/original/{filename}"

        logger.info(
            "uploading_document",
            doc_id=doc_id,
            kb_id=kb_id,
            filename=filename,
            file_size=file_size
        )

        try:
            # 3. 上传原始文件到S3
            s3_uri = s3_client.upload_file(
                file_obj=file,
                s3_key=s3_key,
                content_type=content_type
            )

            # 4. 创建数据库记录
            doc = Document(
                id=doc_id,
                kb_id=kb_id,
                filename=filename,
                file_size=file_size,
                s3_key=s3_key,
                status="uploaded"  # 初始状态：已上传
            )

            db.add(doc)
            db.commit()
            db.refresh(doc)

            logger.info(
                "document_uploaded",
                doc_id=doc_id,
                kb_id=kb_id,
                s3_uri=s3_uri
            )

            return doc

        except Exception as e:
            db.rollback()
            logger.error("document_upload_failed", doc_id=doc_id, error=str(e))
            # 尝试清理S3文件
            try:
                s3_client.delete_file(s3_key)
            except:
                pass
            raise S3UploadError({"error": str(e), "doc_id": doc_id, "filename": filename})

    @staticmethod
    def get_document(db: Session, doc_id: str) -> Document:
        """
        获取文档

        Args:
            db: 数据库会话
            doc_id: 文档ID

        Returns:
            文档对象

        Raises:
            DocumentNotFoundError: 文档不存在
        """
        doc = db.query(Document).filter(
            Document.id == doc_id,
            Document.status != "deleted"
        ).first()

        if not doc:
            raise DocumentNotFoundError(doc_id)

        return doc

    @staticmethod
    def list_documents(
        db: Session,
        kb_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None
    ) -> Tuple[List[Document], int]:
        """
        列出知识库中的文档

        Args:
            db: 数据库会话
            kb_id: 知识库ID
            page: 页码（从1开始）
            page_size: 每页数量
            status: 文档状态过滤（可选）

        Returns:
            (文档列表, 总数)

        Raises:
            KnowledgeBaseNotFoundError: 知识库不存在
        """
        # 检查知识库是否存在
        kb = db.query(KnowledgeBase).filter(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.status == "active"
        ).first()

        if not kb:
            raise KnowledgeBaseNotFoundError(kb_id)

        # 构建查询
        query = db.query(Document).filter(
            Document.kb_id == kb_id,
            Document.status != "deleted"
        )

        # 状态过滤
        if status:
            query = query.filter(Document.status == status)

        total = query.count()

        docs = query.order_by(
            Document.created_at.desc()
        ).offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        return docs, total

    @staticmethod
    def update_document(
        db: Session,
        doc_id: str,
        doc_data: DocumentUpdate
    ) -> Document:
        """
        更新文档（主要用于更新处理状态）

        Args:
            db: 数据库会话
            doc_id: 文档ID
            doc_data: 更新数据

        Returns:
            更新后的文档对象

        Raises:
            DocumentNotFoundError: 文档不存在
        """
        doc = DocumentService.get_document(db, doc_id)

        # 更新状态
        if doc_data.status:
            doc.status = doc_data.status

        # 更新Markdown路径
        if doc_data.s3_key_markdown:
            doc.s3_key_markdown = doc_data.s3_key_markdown

        if doc_data.local_markdown_path:
            doc.local_markdown_path = doc_data.local_markdown_path

        # 更新错误信息
        if doc_data.error_message is not None:
            doc.error_message = doc_data.error_message

        doc.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(doc)

        logger.info("document_updated", doc_id=doc_id, status=doc.status)
        return doc

    @staticmethod
    def delete_document(db: Session, doc_id: str) -> bool:
        """
        删除文档（软删除数据库，真删除S3）

        Args:
            db: 数据库会话
            doc_id: 文档ID

        Returns:
            是否删除成功

        Raises:
            DocumentNotFoundError: 文档不存在
        """
        doc = DocumentService.get_document(db, doc_id)

        try:
            # 1. 软删除数据库记录
            doc.status = "deleted"
            doc.updated_at = datetime.utcnow()

            # 2. 删除S3上的所有相关文件
            # 删除整个文档目录：documents/{doc_id}/
            kb = db.query(KnowledgeBase).filter(
                KnowledgeBase.id == doc.kb_id
            ).first()

            if kb:
                s3_prefix = f"{kb.s3_prefix}documents/{doc_id}/"
                deleted_count = s3_client.delete_prefix(s3_prefix)
                logger.info(
                    "s3_files_deleted",
                    doc_id=doc_id,
                    prefix=s3_prefix,
                    count=deleted_count
                )

            db.commit()

            logger.info("document_deleted", doc_id=doc_id)
            return True

        except Exception as e:
            db.rollback()
            logger.error("document_deletion_failed", doc_id=doc_id, error=str(e))
            raise

    @staticmethod
    def get_document_stats(db: Session, doc_id: str) -> dict:
        """
        获取文档统计信息

        Args:
            db: 数据库会话
            doc_id: 文档ID

        Returns:
            统计信息字典
        """
        from app.models.database import Chunk

        # Chunk数量
        chunk_count = db.query(func.count(Chunk.id)).filter(
            Chunk.document_id == doc_id
        ).scalar() or 0

        # 文本Chunk数量
        text_chunk_count = db.query(func.count(Chunk.id)).filter(
            Chunk.document_id == doc_id,
            Chunk.chunk_type == "text"
        ).scalar() or 0

        # 图片Chunk数量
        image_chunk_count = db.query(func.count(Chunk.id)).filter(
            Chunk.document_id == doc_id,
            Chunk.chunk_type == "image"
        ).scalar() or 0

        return {
            "chunk_count": chunk_count,
            "text_chunk_count": text_chunk_count,
            "image_chunk_count": image_chunk_count
        }
