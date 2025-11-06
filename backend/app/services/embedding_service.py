"""
向量化服务
生成Embeddings并索引到OpenSearch
"""
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.errors import (
    DocumentNotFoundError,
    VectorizationError,
    OpenSearchConnectionError
)
from app.models.database import Document, Chunk
from app.utils.bedrock_client import bedrock_client
from app.utils.opensearch_client import opensearch_client

logger = get_logger(__name__)


class EmbeddingService:
    """向量化服务"""

    # 批量处理大小
    BATCH_SIZE = 25  # Bedrock Embedding API推荐的批量大小

    @staticmethod
    def generate_and_index_embeddings(
        db: Session,
        document_id: str,
        chunk_ids: List[str]
    ) -> int:
        """
        为chunks生成embeddings并索引到OpenSearch

        Args:
            db: 数据库会话
            document_id: 文档ID
            chunk_ids: chunk ID列表

        Returns:
            成功索引的chunk数量

        Raises:
            DocumentNotFoundError: 文档不存在
            VectorizationError: 向量化失败
            OpenSearchConnectionError: OpenSearch连接失败
        """
        logger.info(
            "start_vectorization",
            document_id=document_id,
            chunk_count=len(chunk_ids)
        )

        # 验证文档存在
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise DocumentNotFoundError(document_id)

        # 获取知识库的OpenSearch索引名
        kb = doc.knowledge_base
        index_name = kb.opensearch_index_name

        if not index_name:
            raise VectorizationError(
                details={
                    "document_id": document_id,
                    "kb_id": kb.id,
                    "reason": "OpenSearch索引未创建"
                }
            )

        try:
            # 获取所有chunks
            chunks = db.query(Chunk).filter(
                Chunk.id.in_(chunk_ids)
            ).order_by(Chunk.chunk_index).all()

            if not chunks:
                logger.warning("no_chunks_found", document_id=document_id)
                return 0

            # 批量处理
            indexed_count = 0
            total_batches = (len(chunks) + EmbeddingService.BATCH_SIZE - 1) // EmbeddingService.BATCH_SIZE

            for batch_idx in range(total_batches):
                start_idx = batch_idx * EmbeddingService.BATCH_SIZE
                end_idx = min(start_idx + EmbeddingService.BATCH_SIZE, len(chunks))
                batch_chunks = chunks[start_idx:end_idx]

                logger.info(
                    "processing_batch",
                    document_id=document_id,
                    batch=batch_idx + 1,
                    total_batches=total_batches,
                    batch_size=len(batch_chunks)
                )

                # 处理批次
                batch_count = EmbeddingService._process_batch(
                    db=db,
                    chunks=batch_chunks,
                    index_name=index_name
                )

                indexed_count += batch_count

            # 更新文档状态为completed
            doc.status = "completed"
            db.commit()

            logger.info(
                "vectorization_completed",
                document_id=document_id,
                indexed_count=indexed_count
            )

            return indexed_count

        except Exception as e:
            logger.error(
                "vectorization_failed",
                document_id=document_id,
                error=str(e),
                exc_info=True
            )

            # 更新文档状态为failed
            doc.status = "failed"
            doc.error_message = f"向量化失败: {str(e)}"
            db.commit()

            raise VectorizationError(
                details={
                    "document_id": document_id,
                    "error": str(e)
                }
            )

    @staticmethod
    def _process_batch(
        db: Session,
        chunks: List[Chunk],
        index_name: str
    ) -> int:
        """
        处理一个批次的chunks

        Args:
            db: 数据库会话
            chunks: chunk列表
            index_name: OpenSearch索引名

        Returns:
            成功索引的数量
        """
        # 1. 提取文本用于向量化
        texts = []
        for chunk in chunks:
            # 使用content_with_context生成更好的embedding
            text = chunk.content_with_context or chunk.content or ""
            texts.append(text)

        # 2. 生成embeddings
        try:
            embeddings = bedrock_client.generate_embeddings_batch(
                texts=texts,
                batch_size=len(texts),  # 已经是批次了
                normalize=True
            )

            logger.debug(
                "embeddings_generated",
                count=len(embeddings),
                dimension=len(embeddings[0]) if embeddings else 0
            )

        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            raise VectorizationError(
                details={"error": f"Embedding生成失败: {str(e)}"}
            )

        # 3. 构建OpenSearch文档
        documents = []
        for chunk, embedding in zip(chunks, embeddings):
            doc = EmbeddingService._build_opensearch_document(
                chunk=chunk,
                embedding=embedding
            )
            documents.append(doc)

        # 4. 批量索引到OpenSearch
        try:
            success_count = opensearch_client.bulk_index_documents(
                index_name=index_name,
                documents=documents
            )

            logger.debug(
                "batch_indexed",
                index_name=index_name,
                success_count=success_count
            )

            return success_count

        except Exception as e:
            logger.error("opensearch_indexing_failed", error=str(e))
            raise OpenSearchConnectionError(
                details={"error": f"OpenSearch索引失败: {str(e)}"}
            )

    @staticmethod
    def _build_opensearch_document(
        chunk: Chunk,
        embedding: List[float]
    ) -> Dict:
        """
        构建OpenSearch文档

        Args:
            chunk: Chunk对象
            embedding: 向量

        Returns:
            OpenSearch文档
        """
        # 基础字段
        doc = {
            "id": chunk.id,
            "document_id": chunk.document_id,
            "kb_id": chunk.kb_id,
            "chunk_type": chunk.chunk_type,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "content_with_context": chunk.content_with_context,
            "embedding": embedding
        }

        # 文本chunk特有字段
        if chunk.chunk_type == "text":
            doc.update({
                "char_start": chunk.char_start,
                "char_end": chunk.char_end
            })

        # 图片chunk特有字段
        elif chunk.chunk_type == "image":
            doc.update({
                "image_filename": chunk.image_filename,
                "image_description": chunk.image_description,
                "image_type": chunk.image_type
            })

        return doc

    @staticmethod
    def update_chunk_s3_paths(
        db: Session,
        document_id: str,
        image_s3_keys: List[str]
    ):
        """
        更新图片chunk的S3路径

        Args:
            db: 数据库会话
            document_id: 文档ID
            image_s3_keys: 图片S3路径列表
        """
        logger.info(
            "updating_chunk_s3_paths",
            document_id=document_id,
            images_count=len(image_s3_keys)
        )

        try:
            # 获取文档的图片chunks
            image_chunks = db.query(Chunk).filter(
                Chunk.document_id == document_id,
                Chunk.chunk_type == "image"
            ).order_by(Chunk.chunk_index).all()

            # 更新S3路径
            for chunk, s3_key in zip(image_chunks, image_s3_keys):
                chunk.image_s3_key = s3_key

            db.commit()

            logger.info(
                "chunk_s3_paths_updated",
                document_id=document_id,
                updated_count=len(image_chunks)
            )

        except Exception as e:
            db.rollback()
            logger.error(
                "update_s3_paths_failed",
                document_id=document_id,
                error=str(e)
            )
            raise

    @staticmethod
    def delete_chunks_from_index(
        db: Session,
        document_id: str
    ) -> int:
        """
        从OpenSearch索引中删除文档的所有chunks

        Args:
            db: 数据库会话
            document_id: 文档ID

        Returns:
            删除的chunk数量

        Raises:
            DocumentNotFoundError: 文档不存在
        """
        logger.info("deleting_chunks_from_index", document_id=document_id)

        # 验证文档存在
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise DocumentNotFoundError(document_id)

        # 获取索引名
        index_name = doc.knowledge_base.opensearch_index_name
        if not index_name:
            logger.warning("no_index_found", document_id=document_id)
            return 0

        try:
            # 获取所有chunk IDs
            chunk_ids = [
                chunk.id for chunk in
                db.query(Chunk.id).filter(Chunk.document_id == document_id).all()
            ]

            if not chunk_ids:
                logger.info("no_chunks_to_delete", document_id=document_id)
                return 0

            # 从OpenSearch删除
            deleted_count = opensearch_client.delete_documents_batch(
                index_name=index_name,
                doc_ids=chunk_ids
            )

            logger.info(
                "chunks_deleted_from_index",
                document_id=document_id,
                deleted_count=deleted_count
            )

            return deleted_count

        except Exception as e:
            logger.error(
                "delete_chunks_failed",
                document_id=document_id,
                error=str(e)
            )
            raise OpenSearchConnectionError(
                details={"error": f"删除chunks失败: {str(e)}"}
            )


# 全局实例
embedding_service = EmbeddingService()
