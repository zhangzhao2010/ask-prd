"""
文档相关工具
提供给Sub-Agent读取文档内容和图片的能力
"""
from typing import List, Dict
from strands import tool

from app.core.logging import get_logger

logger = get_logger(__name__)


def create_document_reader_tool(document_content: str, images: List[Dict]):
    """
    创建文档阅读工具

    Args:
        document_content: 文档的Markdown内容
        images: 图片信息列表 [{"filename": "...", "description": "...", "type": "..."}]

    Returns:
        工具函数
    """

    @tool
    def read_document() -> str:
        """
        读取完整的文档内容

        Returns:
            文档的Markdown文本内容
        """
        logger.debug("tool_read_document_called", length=len(document_content))
        return document_content

    return read_document


def create_image_reader_tool(images: List[Dict]):
    """
    创建图片阅读工具

    Args:
        images: 图片信息列表

    Returns:
        工具函数
    """

    @tool
    def read_images() -> str:
        """
        读取文档中的所有图片及其描述

        Returns:
            图片列表的JSON字符串，包含文件名、类型和详细描述
        """
        logger.debug("tool_read_images_called", count=len(images))

        if not images:
            return "该文档不包含图片"

        # 构建图片信息文本
        result = f"该文档包含 {len(images)} 张图片：\n\n"

        for idx, img in enumerate(images, 1):
            result += f"## 图片 {idx}: {img.get('filename', 'unknown')}\n"
            result += f"- **类型**: {img.get('type', 'other')}\n"
            result += f"- **描述**: {img.get('description', '无描述')}\n\n"

        return result

    return read_images


def create_search_context_tool(context_text: str):
    """
    创建上下文搜索工具

    Args:
        context_text: 相关上下文文本

    Returns:
        工具函数
    """

    @tool
    def get_context() -> str:
        """
        获取与问题相关的上下文信息

        Returns:
            相关上下文文本
        """
        logger.debug("tool_get_context_called", length=len(context_text))
        return context_text

    return get_context
