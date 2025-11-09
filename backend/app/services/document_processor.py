"""
DocumentProcessor模块
负责文档分段、标记和构建图文混排content
"""
import re
import os
from dataclasses import dataclass
from typing import List, Tuple, Dict

from app.core.logging import get_logger
from app.services.document_loader import DocumentContent

logger = get_logger(__name__)


@dataclass
class ProcessedDocument:
    """处理后的文档数据类"""
    doc_id: str                      # 完整document_id
    doc_name: str                    # 文档名称
    doc_short_id: str                # 短ID（前8位）
    content: List[Dict]              # Bedrock API格式的content
    references_map: Dict[str, str]   # {ref_id: 原文内容或图片路径}


class DocumentProcessor:
    """负责文档分段、标记和构建图文混排content"""

    def process(self, document_content: DocumentContent) -> ProcessedDocument:
        """
        处理文档：分段、标记、构建content

        Args:
            document_content: DocumentContent对象

        Returns:
            ProcessedDocument对象
        """
        logger.info(
            "processing_document",
            doc_id=document_content.doc_id,
            doc_name=document_content.doc_name
        )

        # 1. 生成doc_short_id（前8位UUID）
        doc_short_id = document_content.doc_id[:8]

        # 2. 构建图文混排content
        content, references_map = self.build_content(
            markdown_text=document_content.markdown_text,
            image_paths=document_content.image_paths,
            doc_short_id=doc_short_id
        )

        logger.info(
            "document_processed",
            doc_id=document_content.doc_id,
            content_blocks=len(content),
            references_count=len(references_map)
        )

        return ProcessedDocument(
            doc_id=document_content.doc_id,
            doc_name=document_content.doc_name,
            doc_short_id=doc_short_id,
            content=content,
            references_map=references_map
        )

    def split_into_paragraphs(self, text: str) -> List[str]:
        """
        智能分段：按空行和标题分割
        参考demo中的实现逻辑

        Args:
            text: 原始文本

        Returns:
            段落列表
        """
        paragraphs = []

        # 按空行分割
        blocks = re.split(r'\n\s*\n', text)

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            lines = block.split('\n')
            current_para = []

            for line in lines:
                # 检测标题行
                if re.match(r'^#{1,6}\s+', line):
                    # 保存之前的段落
                    if current_para:
                        paragraphs.append('\n'.join(current_para))
                        current_para = []
                    # 标题单独成段
                    paragraphs.append(line)
                else:
                    current_para.append(line)

            # 保存最后的段落
            if current_para:
                paragraphs.append('\n'.join(current_para))

        return [p for p in paragraphs if p.strip()]

    def build_content(
        self,
        markdown_text: str,
        image_paths: List[str],
        doc_short_id: str
    ) -> Tuple[List[Dict], Dict[str, str]]:
        """
        构建图文混排content
        按照Markdown中的顺序，交替插入文本段落和图片

        Args:
            markdown_text: Markdown文本
            image_paths: 图片本地路径列表
            doc_short_id: 文档短ID

        Returns:
            (content列表, references映射表)
        """
        logger.info(
            "building_content",
            doc_short_id=doc_short_id,
            text_length=len(markdown_text),
            image_count=len(image_paths)
        )

        content = []
        references_map = {}

        # 1. 解析Markdown中的图片位置和文件名
        # 匹配 ![](filename.ext) 格式
        image_pattern = r'!\[\]\(([^)]+\.(?:jpeg|jpg|png|gif|webp))\)'
        images_in_md = []

        for match in re.finditer(image_pattern, markdown_text):
            # 提取图片文件名（可能包含路径）
            img_ref = match.group(1)
            img_filename = os.path.basename(img_ref)
            position = match.start()
            images_in_md.append((position, img_filename, img_ref))

        logger.debug(
            "found_images_in_markdown",
            doc_short_id=doc_short_id,
            count=len(images_in_md)
        )

        # 2. 按位置交替插入文本和图片
        para_counter = 1
        img_counter = 1
        last_pos = 0

        for pos, img_filename, img_ref in images_in_md:
            # 处理图片前的文本
            text_before = markdown_text[last_pos:pos].strip()
            if text_before:
                # 分割成段落
                paragraphs = self.split_into_paragraphs(text_before)

                for para in paragraphs:
                    if not para.strip():
                        continue

                    # 生成段落标记
                    para_id = f"DOC-{doc_short_id}-PARA-{para_counter}"
                    labeled_para = f"[{para_id}]\n{para}"

                    # 保存到映射表
                    references_map[para_id] = para

                    # 添加到content
                    content.append({"text": labeled_para})

                    para_counter += 1

            # 处理图片
            # 查找对应的本地图片路径
            matching_path = None
            for img_path in image_paths:
                if os.path.basename(img_path) == img_filename:
                    matching_path = img_path
                    break

            if matching_path:
                # 生成图片标记
                img_id = f"DOC-{doc_short_id}-IMAGE-{img_counter}"
                img_label = f"[{img_id}: {img_filename}]"

                # 保存到映射表（存储文件名，供前端访问）
                references_map[img_id] = img_filename

                # 添加标记文本
                content.append({"text": img_label})

                # 添加图片
                try:
                    with open(matching_path, 'rb') as f:
                        img_bytes = f.read()

                    # 判断图片格式
                    img_format = img_filename.split('.')[-1].lower()
                    if img_format == 'jpg':
                        img_format = 'jpeg'

                    content.append({
                        "image": {
                            "format": img_format,
                            "source": {
                                "bytes": img_bytes
                            }
                        }
                    })

                    logger.debug(
                        "image_added_to_content",
                        doc_short_id=doc_short_id,
                        img_id=img_id,
                        filename=img_filename,
                        size=len(img_bytes)
                    )

                    img_counter += 1

                except Exception as e:
                    logger.error(
                        "failed_to_read_image",
                        doc_short_id=doc_short_id,
                        img_path=matching_path,
                        error=str(e),
                        exc_info=True
                    )
                    # 跳过失败的图片，继续处理
                    continue

            else:
                logger.warning(
                    "image_not_found_in_paths",
                    doc_short_id=doc_short_id,
                    img_filename=img_filename
                )

            # 更新位置（跳过图片引用的markdown语法）
            last_pos = pos + len(f"![]({img_ref})")

        # 处理最后剩余的文本
        text_after = markdown_text[last_pos:].strip()
        if text_after:
            paragraphs = self.split_into_paragraphs(text_after)

            for para in paragraphs:
                if not para.strip():
                    continue

                para_id = f"DOC-{doc_short_id}-PARA-{para_counter}"
                labeled_para = f"[{para_id}]\n{para}"

                references_map[para_id] = para
                content.append({"text": labeled_para})

                para_counter += 1

        logger.info(
            "content_built",
            doc_short_id=doc_short_id,
            paragraphs=para_counter - 1,
            images=img_counter - 1,
            content_blocks=len(content)
        )

        return content, references_map
