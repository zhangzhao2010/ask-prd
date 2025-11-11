"""
文本分块服务
使用LangChain对Markdown文本进行智能分块
"""
import uuid
import re
from pathlib import Path
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.core.logging import get_logger
from app.core.errors import DocumentNotFoundError
from app.models.database import Document, Chunk

logger = get_logger(__name__)


class ChunkingService:
    """文本分块服务"""

    # 分块参数
    CHUNK_SIZE = 1000  # 每个chunk的字符数
    CHUNK_OVERLAP = 200  # chunk之间的重叠字符数

    # 中文优化的分隔符
    SEPARATORS = [
        "\n\n",  # 段落
        "\n",    # 行
        "。",    # 句号
        "！",    # 感叹号
        "？",    # 问号
        "；",    # 分号
        "，",    # 逗号
        " ",     # 空格
        "",      # 字符
    ]

    @staticmethod
    def chunk_markdown(
        db: Session,
        document_id: str,
        markdown_content: str,
        images_info: List[Dict]
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        对Markdown文本进行分块，并处理图片chunk

        Args:
            db: 数据库会话
            document_id: 文档ID
            markdown_content: Markdown文本内容
            images_info: 图片信息列表 [{"filename": "...", "path": "...", "description": "..."}]

        Returns:
            (text_chunks, image_chunks)
            - text_chunks: 文本chunk列表
            - image_chunks: 图片chunk列表

        Raises:
            DocumentNotFoundError: 文档不存在
        """
        logger.info(
            "start_chunking",
            document_id=document_id,
            markdown_length=len(markdown_content),
            images_count=len(images_info)
        )

        # 验证文档存在
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise DocumentNotFoundError(document_id)

        # 1. 处理文本分块
        text_chunks = ChunkingService._chunk_text(
            markdown_content=markdown_content,
            document_id=document_id
        )

        # 2. 处理图片分块
        image_chunks = ChunkingService._create_image_chunks(
            images_info=images_info,
            document_id=document_id,
            markdown_content=markdown_content
        )

        logger.info(
            "chunking_completed",
            document_id=document_id,
            text_chunks_count=len(text_chunks),
            image_chunks_count=len(image_chunks)
        )

        return text_chunks, image_chunks

    @staticmethod
    def _chunk_text(
        markdown_content: str,
        document_id: str
    ) -> List[Dict]:
        """
        使用LangChain对文本进行分块

        Args:
            markdown_content: Markdown文本
            document_id: 文档ID

        Returns:
            文本chunk列表
        """
        logger.info("start_text_chunking", document_id=document_id)

        # 创建分块器
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=ChunkingService.CHUNK_SIZE,
            chunk_overlap=ChunkingService.CHUNK_OVERLAP,
            separators=ChunkingService.SEPARATORS,
            length_function=len,
            is_separator_regex=False
        )

        # 分块
        chunks = text_splitter.split_text(markdown_content)

        # 构建chunk数据
        text_chunks = []
        char_position = 0

        for idx, chunk_text in enumerate(chunks):
            # 查找chunk在原文中的位置
            char_start = markdown_content.find(chunk_text, char_position)
            if char_start == -1:
                # 如果找不到（可能因为分隔符处理），使用估算位置
                char_start = char_position
            char_end = char_start + len(chunk_text)

            # 提取chunk上下文（包含前后内容，用于更好的向量化）
            context_start = max(0, char_start - 100)
            context_end = min(len(markdown_content), char_end + 100)
            content_with_context = markdown_content[context_start:context_end]

            # 检查是否包含图片引用
            image_references = ChunkingService._extract_image_references(chunk_text)

            chunk_data = {
                "chunk_index": idx,
                "content": chunk_text.strip(),
                "content_with_context": content_with_context.strip(),
                "char_start": char_start,
                "char_end": char_end,
                "has_image_refs": len(image_references) > 0,
                "image_refs": image_references
            }

            text_chunks.append(chunk_data)

            # 更新字符位置
            char_position = char_end

        logger.info(
            "text_chunking_completed",
            document_id=document_id,
            chunks_count=len(text_chunks)
        )

        return text_chunks

    @staticmethod
    def _extract_image_references(text: str) -> List[str]:
        """
        从文本中提取图片引用

        Args:
            text: 文本内容

        Returns:
            图片文件名列表
        """
        # Markdown图片语法: ![alt](image.png)
        # 或者: ![alt](images/image.png)
        pattern = r'!\[.*?\]\((.*?\.(?:png|jpg|jpeg|gif|svg))\)'
        matches = re.findall(pattern, text, re.IGNORECASE)

        # 提取文件名
        filenames = []
        for match in matches:
            filename = Path(match).name
            filenames.append(filename)

        return filenames

    @staticmethod
    def _create_image_chunks(
        images_info: List[Dict],
        document_id: str,
        markdown_content: str
    ) -> List[Dict]:
        """
        创建图片chunk

        Args:
            images_info: 图片信息列表
            document_id: 文档ID
            markdown_content: Markdown内容（用于提取上下文）

        Returns:
            图片chunk列表
        """
        logger.info(
            "creating_image_chunks",
            document_id=document_id,
            images_count=len(images_info)
        )

        image_chunks = []

        for idx, img_info in enumerate(images_info):
            filename = img_info["filename"]
            description = img_info.get("description", "")

            # 尝试从Markdown中提取图片周围的上下文
            context = ChunkingService._extract_image_context(
                markdown_content,
                filename
            )

            # 分析图片类型（基于描述）
            image_type = ChunkingService._infer_image_type(description)

            chunk_data = {
                "chunk_index": idx,
                "image_filename": filename,
                "image_path": img_info.get("path", ""),
                "image_description": description,
                "image_type": image_type,
                "context": context,
                # 对于图片chunk，使用description作为content用于向量化
                "content": description,
                "content_with_context": f"{context}\n\n{description}" if context else description
            }

            image_chunks.append(chunk_data)

        logger.info(
            "image_chunks_created",
            document_id=document_id,
            count=len(image_chunks)
        )

        return image_chunks

    @staticmethod
    def _extract_image_context(markdown_content: str, filename: str) -> str:
        """
        提取图片周围的上下文文本

        Args:
            markdown_content: Markdown内容
            filename: 图片文件名

        Returns:
            上下文文本
        """
        # 查找图片引用位置
        pattern = rf'!\[.*?\]\(.*?{re.escape(filename)}.*?\)'
        match = re.search(pattern, markdown_content, re.IGNORECASE)

        if not match:
            return ""

        # 提取图片前后的文本（各200字符）
        img_pos = match.start()
        context_start = max(0, img_pos - 200)
        context_end = min(len(markdown_content), match.end() + 200)

        context = markdown_content[context_start:context_end]

        # 移除图片引用本身
        context = re.sub(pattern, "[图片]", context, flags=re.IGNORECASE)

        return context.strip()

    @staticmethod
    def _infer_image_type(description: str) -> str:
        """
        根据描述推断图片类型

        Args:
            description: 图片描述

        Returns:
            图片类型 (flowchart | prototype | mindmap | screenshot | diagram | other)
        """
        # 处理None或空描述
        if not description:
            return "other"

        description_lower = description.lower()

        # 关键词映射
        type_keywords = {
            "flowchart": ["流程图", "流程", "步骤", "workflow", "flow"],
            "prototype": ["原型", "界面", "ui", "页面", "prototype", "wireframe"],
            "mindmap": ["脑图", "思维导图", "知识", "mind map", "mindmap"],
            "screenshot": ["截图", "屏幕", "screenshot"],
            "diagram": ["图表", "架构图", "diagram", "chart", "架构"]
        }

        # 检查关键词
        for img_type, keywords in type_keywords.items():
            for keyword in keywords:
                if keyword in description_lower:
                    return img_type

        return "other"

    @staticmethod
    def save_chunks_to_db(
        db: Session,
        document_id: str,
        text_chunks: List[Dict],
        image_chunks: List[Dict]
    ) -> List[str]:
        """
        保存chunks到数据库

        Args:
            db: 数据库会话
            document_id: 文档ID
            text_chunks: 文本chunk列表
            image_chunks: 图片chunk列表

        Returns:
            chunk_ids列表

        Raises:
            DocumentNotFoundError: 文档不存在
        """
        logger.info(
            "saving_chunks_to_db",
            document_id=document_id,
            text_chunks=len(text_chunks),
            image_chunks=len(image_chunks)
        )

        # 验证文档存在
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise DocumentNotFoundError(document_id)

        chunk_ids = []

        try:
            # 保存文本chunks
            for chunk_data in text_chunks:
                chunk_id = str(uuid.uuid4())

                chunk = Chunk(
                    id=chunk_id,
                    document_id=document_id,
                    kb_id=doc.kb_id,
                    chunk_type="text",
                    chunk_index=chunk_data["chunk_index"],
                    content=chunk_data["content"],
                    content_with_context=chunk_data["content_with_context"],
                    char_start=chunk_data.get("char_start"),
                    char_end=chunk_data.get("char_end")
                )

                db.add(chunk)
                chunk_ids.append(chunk_id)

            # 保存图片chunks
            for chunk_data in image_chunks:
                chunk_id = str(uuid.uuid4())

                chunk = Chunk(
                    id=chunk_id,
                    document_id=document_id,
                    kb_id=doc.kb_id,
                    chunk_type="image",
                    chunk_index=chunk_data["chunk_index"],
                    content=chunk_data["content"],  # description
                    content_with_context=chunk_data["content_with_context"],
                    image_filename=chunk_data["image_filename"],
                    image_local_path=chunk_data.get("image_path"),
                    image_description=chunk_data["image_description"],
                    image_type=chunk_data["image_type"]
                )

                db.add(chunk)
                chunk_ids.append(chunk_id)

            db.commit()

            logger.info(
                "chunks_saved_to_db",
                document_id=document_id,
                total_chunks=len(chunk_ids)
            )

            return chunk_ids

        except Exception as e:
            db.rollback()
            logger.error(
                "save_chunks_failed",
                document_id=document_id,
                error=str(e),
                exc_info=True
            )
            raise


# 全局实例
chunking_service = ChunkingService()
