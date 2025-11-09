"""
DocumentLoader模块
负责从S3或本地缓存加载文档内容（Markdown + 图片）
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.errors import DocumentNotFoundError
from app.models.database import Document, Chunk
from app.utils.s3_client import S3Client

logger = get_logger(__name__)


@dataclass
class DocumentContent:
    """文档内容数据类"""
    doc_id: str              # 完整document_id
    doc_name: str            # 文档名称
    markdown_path: str       # Markdown本地路径
    markdown_text: str       # Markdown文本内容
    image_paths: List[str]   # 图片本地路径列表


class DocumentLoader:
    """负责从S3或本地缓存加载文档内容"""

    def __init__(
        self,
        db_session: Session,
        s3_client: S3Client,
        cache_dir: str = None
    ):
        """
        初始化DocumentLoader

        Args:
            db_session: 数据库会话
            s3_client: S3客户端实例
            cache_dir: 本地缓存目录（默认使用settings.cache_dir）
        """
        self.db = db_session
        self.s3_client = s3_client
        self.cache_dir = cache_dir or settings.cache_dir

        logger.info("document_loader_initialized", cache_dir=self.cache_dir)

    def load_document(self, document_id: str) -> DocumentContent:
        """
        加载文档的Markdown和图片

        Args:
            document_id: 文档ID

        Returns:
            DocumentContent对象

        Raises:
            DocumentNotFoundError: 文档不存在
        """
        logger.info("loading_document", document_id=document_id)

        # 1. 查询文档元数据
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise DocumentNotFoundError(document_id)

        if not doc.s3_key_markdown:
            raise ValueError(f"Document {document_id} has no markdown s3_key")

        # 2. 获取Markdown文件
        markdown_path, markdown_text = self._get_markdown(
            document_id=document_id,
            s3_key=doc.s3_key_markdown
        )

        # 3. 获取图片文件
        image_paths = self._get_images(document_id)

        logger.info(
            "document_loaded",
            document_id=document_id,
            markdown_size=len(markdown_text),
            image_count=len(image_paths)
        )

        return DocumentContent(
            doc_id=document_id,
            doc_name=doc.filename,
            markdown_path=markdown_path,
            markdown_text=markdown_text,
            image_paths=image_paths
        )

    def _get_markdown(self, document_id: str, s3_key: str) -> Tuple[str, str]:
        """
        获取Markdown文件（优先本地缓存）

        Args:
            document_id: 文档ID
            s3_key: S3路径

        Returns:
            (本地路径, 文本内容)
        """
        # 1. 构建本地路径
        local_path = os.path.join(
            self.cache_dir,
            "documents",
            document_id,
            "content.md"
        )

        # 2. 检查本地缓存
        if os.path.exists(local_path):
            logger.debug("markdown_cache_hit", document_id=document_id, local_path=local_path)
            with open(local_path, 'r', encoding='utf-8') as f:
                text = f.read()
            return local_path, text

        # 3. 从S3下载
        logger.info("downloading_markdown_from_s3", document_id=document_id, s3_key=s3_key)
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.s3_client.download_file(s3_key, local_path)

            # 4. 读取内容
            with open(local_path, 'r', encoding='utf-8') as f:
                text = f.read()

            logger.info("markdown_downloaded", document_id=document_id, size=len(text))
            return local_path, text

        except Exception as e:
            logger.error(
                "markdown_download_failed",
                document_id=document_id,
                s3_key=s3_key,
                error=str(e),
                exc_info=True
            )
            raise

    def _get_images(self, document_id: str) -> List[str]:
        """
        获取文档的所有图片

        Args:
            document_id: 文档ID

        Returns:
            图片本地路径列表
        """
        # 1. 从数据库查询该文档的所有图片chunks
        image_chunks = (
            self.db.query(Chunk)
            .filter(
                Chunk.document_id == document_id,
                Chunk.chunk_type == 'image'
            )
            .order_by(Chunk.chunk_index)
            .all()
        )

        logger.info(
            "found_image_chunks",
            document_id=document_id,
            count=len(image_chunks)
        )

        image_paths = []

        # 2. 逐个下载图片
        for chunk in image_chunks:
            if not chunk.image_s3_key or not chunk.image_filename:
                logger.warning(
                    "image_chunk_missing_info",
                    chunk_id=chunk.id,
                    has_s3_key=bool(chunk.image_s3_key),
                    has_filename=bool(chunk.image_filename)
                )
                continue

            # 构建本地路径（与Markdown同目录）
            # 图片文件名从chunk.image_filename获取
            local_path = os.path.join(
                self.cache_dir,
                "documents",
                document_id,
                chunk.image_filename
            )

            # 检查本地缓存
            if os.path.exists(local_path):
                logger.debug("image_cache_hit", chunk_id=chunk.id, local_path=local_path)
                image_paths.append(local_path)
                continue

            # 从S3下载
            try:
                logger.info(
                    "downloading_image_from_s3",
                    chunk_id=chunk.id,
                    s3_key=chunk.image_s3_key
                )
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                self.s3_client.download_file(chunk.image_s3_key, local_path)

                image_paths.append(local_path)
                logger.debug("image_downloaded", chunk_id=chunk.id, local_path=local_path)

            except Exception as e:
                logger.error(
                    "image_download_failed",
                    chunk_id=chunk.id,
                    s3_key=chunk.image_s3_key,
                    error=str(e),
                    exc_info=True
                )
                # 跳过失败的图片，继续处理其他图片
                continue

        logger.info(
            "images_loaded",
            document_id=document_id,
            total_chunks=len(image_chunks),
            downloaded=len(image_paths)
        )

        return image_paths
