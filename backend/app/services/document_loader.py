"""
DocumentLoader模块
负责从本地文件系统加载文档内容（Markdown + 图片）
"""
import os
import glob
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.errors import DocumentNotFoundError
from app.models.database import Document

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
    """负责从本地文件系统加载文档内容"""

    def __init__(
        self,
        db_session: Session
    ):
        """
        初始化DocumentLoader

        Args:
            db_session: 数据库会话
        """
        self.db = db_session

        logger.info("document_loader_initialized")

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

        if not doc.local_markdown_path:
            raise ValueError(f"Document {document_id} has no local_markdown_path")

        # 2. 获取Markdown文件
        markdown_path, markdown_text = self._get_markdown(
            document_id=document_id,
            local_markdown_path=doc.local_markdown_path
        )

        # 3. 获取图片文件（扫描markdown同级目录）
        image_paths = self._get_images(document_id, markdown_path)

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

    def _get_markdown(self, document_id: str, local_markdown_path: str) -> Tuple[str, str]:
        """
        获取Markdown文件（从本地路径读取）

        Args:
            document_id: 文档ID
            local_markdown_path: 本地Markdown路径

        Returns:
            (本地路径, 文本内容)
        """
        if not os.path.exists(local_markdown_path):
            raise FileNotFoundError(f"Markdown file not found: {local_markdown_path}")

        logger.debug("reading_markdown", document_id=document_id, path=local_markdown_path)

        with open(local_markdown_path, 'r', encoding='utf-8') as f:
            text = f.read()

        logger.info("markdown_loaded", document_id=document_id, size=len(text))
        return local_markdown_path, text

    def _get_images(self, document_id: str, markdown_path: str) -> List[str]:
        """
        获取文档的所有图片（扫描markdown同级目录）

        Args:
            document_id: 文档ID
            markdown_path: Markdown文件路径

        Returns:
            图片本地路径列表
        """
        # 获取markdown所在目录
        doc_dir = os.path.dirname(markdown_path)

        # 扫描支持的图片格式
        image_paths = []
        for ext in ['*.png', '*.jpeg', '*.jpg', '*.gif', '*.webp']:
            pattern = os.path.join(doc_dir, ext)
            image_paths.extend(glob.glob(pattern))

        # 按文件名排序
        image_paths.sort()

        logger.info(
            "images_loaded",
            document_id=document_id,
            doc_dir=doc_dir,
            count=len(image_paths)
        )

        return image_paths
