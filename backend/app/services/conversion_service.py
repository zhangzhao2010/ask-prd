"""
PDF转换服务
使用Marker将PDF转换为Markdown并提取图片
"""
import base64
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from sqlalchemy.orm import Session

from marker.models import create_model_dict
from marker.converters.pdf import PdfConverter
from marker.output import text_from_rendered

from app.core.config import settings
from app.core.logging import get_logger
from app.core.errors import (
    DocumentNotFoundError,
    PDFConversionError
)
from app.models.database import Document
from app.utils.bedrock_client import bedrock_client

logger = get_logger(__name__)


class ConversionService:
    """PDF转换服务"""

    @staticmethod
    def convert_pdf_to_markdown(
        db: Session,
        document_id: str,
        pdf_local_path: str,
        output_dir: Optional[Path] = None
    ) -> Tuple[str, List[Dict]]:
        """
        转换PDF为Markdown并提取图片

        Args:
            db: 数据库会话
            document_id: 文档ID
            pdf_local_path: PDF本地路径
            output_dir: 可选的输出目录，默认使用cache目录

        Returns:
            (markdown_content, images_info)
            - markdown_content: Markdown文本内容
            - images_info: 图片信息列表 [{"filename": "img_001.png", "path": "/path/to/img", "description": "..."}]

        Raises:
            DocumentNotFoundError: 文档不存在
            PDFConversionError: 转换失败
        """
        logger.info(
            "start_pdf_conversion",
            document_id=document_id,
            pdf_path=pdf_local_path
        )

        # 验证文档存在
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise DocumentNotFoundError(document_id)

        # 更新文档状态为processing
        doc.status = "processing"
        db.commit()

        try:
            # 创建输出目录（使用传入的output_dir或默认的cache目录）
            if output_dir is None:
                output_dir = Path(settings.cache_dir) / "conversions" / document_id
            output_dir.mkdir(parents=True, exist_ok=True)

            # 使用Marker转换PDF
            logger.info("initializing_marker_models", document_id=document_id)

            # 创建模型字典（包含检测、识别等模型）
            artifact_dict = create_model_dict()

            # 创建PDF转换器
            converter = PdfConverter(
                artifact_dict=artifact_dict,
                processor_list=None,  # 使用默认处理器
                renderer=None,  # 使用默认的MarkdownRenderer
                config=None  # 使用默认配置
            )

            # 执行转换
            logger.info("converting_pdf", document_id=document_id)
            rendered = converter(pdf_local_path)

            # 提取Markdown文本和图片
            # text_from_rendered返回三个值: (markdown_text, metadata, images_dict)
            markdown_content, _, images_dict = text_from_rendered(rendered)

            # 处理图片
            images_info = ConversionService._process_images(
                images_dict=images_dict,
                output_dir=output_dir,
                document_id=document_id
            )

            logger.info(
                "pdf_conversion_completed",
                document_id=document_id,
                markdown_length=len(markdown_content),
                images_count=len(images_info)
            )

            return markdown_content, images_info

        except Exception as e:
            logger.error(
                "pdf_conversion_failed",
                document_id=document_id,
                error=str(e),
                exc_info=True
            )

            # 更新文档状态为failed
            doc.status = "failed"
            doc.error_message = f"PDF转换失败: {str(e)}"
            db.commit()

            raise PDFConversionError(
                doc_id=document_id,
                reason=str(e)
            )

    @staticmethod
    def _process_images(
        images_dict: Dict[str, Any],
        output_dir: Path,
        document_id: str
    ) -> List[Dict]:
        """
        处理从text_from_rendered返回的图片字典
        图片直接保存到output_dir（与markdown同级目录）

        Args:
            images_dict: 图片字典，键是文件名（如'_page_1_Figure_8.jpeg'），值是PIL Image对象
            output_dir: 输出目录
            document_id: 文档ID

        Returns:
            图片信息列表
        """
        images_info = []

        if not images_dict:
            logger.info("no_images_found", document_id=document_id)
            return images_info

        logger.info(
            "processing_images",
            document_id=document_id,
            count=len(images_dict)
        )

        for idx, (original_filename, pil_image) in enumerate(images_dict.items()):
            try:
                img_filename = original_filename
                # 图片直接保存到output_dir，与markdown同目录
                img_path = output_dir / img_filename

                # 保存PIL Image对象
                pil_image.save(img_path)

                logger.debug(
                    "image_saved",
                    document_id=document_id,
                    filename=img_filename,
                    size=pil_image.size
                )

                images_info.append({
                    "filename": img_filename,
                    "path": str(img_path),
                    "index": idx,
                    "description": None  # 稍后生成
                })

            except Exception as e:
                logger.error(
                    "image_extraction_failed",
                    document_id=document_id,
                    index=idx,
                    error=str(e)
                )
                continue

        logger.info(
            "images_extraction_completed",
            document_id=document_id,
            count=len(images_info)
        )

        return images_info

    @staticmethod
    def generate_image_descriptions(
        images_info: List[Dict],
        document_id: str
    ) -> List[Dict]:
        """
        使用Bedrock Claude Vision生成图片描述

        Args:
            images_info: 图片信息列表
            document_id: 文档ID

        Returns:
            更新了description字段的图片信息列表
        """
        logger.info(
            "start_image_description_generation",
            document_id=document_id,
            images_count=len(images_info)
        )

        for img_info in images_info:
            try:
                img_path = img_info["path"]

                # 读取图片并转换为base64
                with open(img_path, "rb") as f:
                    img_bytes = f.read()
                img_base64 = base64.b64encode(img_bytes).decode("utf-8")

                # 使用Bedrock Claude Vision分析图片
                logger.debug(
                    "analyzing_image",
                    document_id=document_id,
                    filename=img_info["filename"]
                )

                # 调用Bedrock分析图片
                description = ConversionService._analyze_image_with_bedrock(
                    img_base64=img_base64,
                    filename=img_info["filename"]
                )

                # 更新描述
                img_info["description"] = description

                logger.info(
                    "image_description_generated",
                    document_id=document_id,
                    filename=img_info["filename"],
                    description_length=len(description)
                )

            except Exception as e:
                logger.error(
                    "image_description_failed",
                    document_id=document_id,
                    filename=img_info.get("filename"),
                    error=str(e)
                )
                # 失败时使用默认描述
                img_info["description"] = f"图片 {img_info.get('filename', 'unknown')}"

        return images_info

    @staticmethod
    def _analyze_image_with_bedrock(
        img_base64: str,
        filename: str
    ) -> str:
        """
        使用Bedrock Claude Vision分析图片

        Args:
            img_base64: 图片的base64编码
            filename: 图片文件名

        Returns:
            图片描述文本
        """
        # 构建提示词
        prompt = """请详细分析这张图片，描述图片的内容、类型和关键信息。

如果是流程图，请描述流程的各个步骤和逻辑关系。
如果是原型图，请描述界面布局和交互元素。
如果是脑图，请描述知识结构和层次关系。
如果是截图，请描述截图展示的内容。
如果是图表，请描述数据和趋势。

请用中文输出，格式清晰，重点突出。"""

        try:
            # 调用bedrock_client的analyze_image方法
            description = bedrock_client.analyze_image(
                image_base64=img_base64,
                prompt=prompt,
                media_type="image/png",
                max_tokens=1000,
                temperature=0.3
            )

            return description

        except Exception as e:
            logger.error(
                "bedrock_vision_api_failed",
                filename=filename,
                error=str(e)
            )
            # 返回默认描述
            return f"图片 {filename}（分析失败）"

    @staticmethod
    def _parse_markdown_content(markdown_text: str, doc_dir: str) -> List[Dict]:
        """
        解析markdown为文本块和图片块的序列

        Returns:
            [
                {"type": "text", "content": "段落1..."},
                {"type": "image", "filename": "img1.png", "path": "/path/to/img1.png"},
                ...
            ]
        """
        import re
        import os

        content_sequence = []

        # 按图片引用分割markdown
        pattern = r'!\[\]\(([^)]+\.(?:jpeg|jpg|png|gif|webp))\)'
        parts = re.split(pattern, markdown_text)

        for i, part in enumerate(parts):
            if i % 2 == 0:  # 文本部分
                if part.strip():
                    content_sequence.append({
                        "type": "text",
                        "content": part.strip()
                    })
            else:  # 图片文件名
                img_filename = part
                img_path = os.path.join(doc_dir, img_filename)
                content_sequence.append({
                    "type": "image",
                    "filename": img_filename,
                    "path": img_path,
                    "description": None,
                    "figure_type": None
                })

        return content_sequence

    @staticmethod
    def _generate_descriptions_with_context(content_sequence: List[Dict], document_id: str) -> None:
        """
        按顺序生成图片描述，传入上下文
        """
        for i, item in enumerate(content_sequence):
            if item["type"] != "image":
                continue

            # 获取上文（最多500字符）
            context_before = ""
            if i > 0:
                prev_item = content_sequence[i - 1]
                if prev_item["type"] == "text":
                    context_before = prev_item["content"][-500:]
                elif prev_item["type"] == "image" and prev_item.get("description"):
                    context_before = f"[上一张图片] {prev_item['description'][:200]}"

            # 获取下文（最多500字符）
            context_after = ""
            if i < len(content_sequence) - 1:
                next_item = content_sequence[i + 1]
                if next_item["type"] == "text":
                    context_after = next_item["content"][:500]

            # 调用Vision API
            try:
                description_result = ConversionService._generate_image_description_with_context(
                    img_path=item["path"],
                    context_before=context_before,
                    context_after=context_after
                )

                item["description"] = description_result["description"]
                item["figure_type"] = description_result["figure_type"]

                logger.info(
                    "image_description_generated_with_context",
                    document_id=document_id,
                    filename=item["filename"],
                    figure_type=item["figure_type"]
                )
            except Exception as e:
                logger.error(
                    "image_description_with_context_failed",
                    document_id=document_id,
                    filename=item["filename"],
                    error=str(e)
                )
                # 使用默认描述
                item["description"] = f"图片 {item['filename']}"
                item["figure_type"] = "Other"

    @staticmethod
    def _generate_image_description_with_context(
        img_path: str,
        context_before: str,
        context_after: str
    ) -> Dict[str, str]:
        """
        调用Bedrock Vision API，传入上下文
        """
        import re

        with open(img_path, 'rb') as f:
            img_bytes = f.read()

        img_base64 = base64.b64encode(img_bytes).decode()

        # 构建带上下文的prompt
        prompt = f"""你正在阅读一份产品文档，需要理解文档中的图片。

【上文】
{context_before if context_before else "（文档开头）"}

【当前图片】
[请分析下方图片]

【下文】
{context_after if context_after else "（文档结尾）"}

请结合上下文，详细描述这张图片的内容、类型和作用。

首先判断图片类型（Chart/Diagram/Logo/Icon/Natural Image/Screenshot/Other），
然后生成详细描述，包括：
- 图片的主要内容
- 图片在文档中的作用
- 关键信息和细节

输出格式：
<figure>
<figure_type>图片类型</figure_type>
<figure_description>详细描述...</figure_description>
</figure>
"""

        response = bedrock_client.analyze_image(
            image_base64=img_base64,
            prompt=prompt,
            media_type="image/png",
            max_tokens=1000,
            temperature=0.3
        )

        # 解析响应
        figure_type_match = re.search(r'<figure_type>(.*?)</figure_type>', response, re.DOTALL)
        description_match = re.search(r'<figure_description>(.*?)</figure_description>', response, re.DOTALL)

        figure_type = figure_type_match.group(1).strip() if figure_type_match else "Other"
        description = description_match.group(1).strip() if description_match else response

        return {
            "figure_type": figure_type,
            "description": description
        }

    @staticmethod
    def generate_and_replace_images(
        markdown_content: str,
        doc_dir: str,
        document_id: str
    ) -> str:
        """
        生成图片描述并替换markdown中的图片引用（带上下文）

        Returns:
            替换后的markdown文本
        """
        import re
        import os

        logger.info(
            "start_generate_and_replace_images",
            document_id=document_id
        )

        # 1. 解析markdown为内容序列
        content_sequence = ConversionService._parse_markdown_content(
            markdown_content, doc_dir
        )

        # 2. 按顺序生成图片描述（带上下文）
        ConversionService._generate_descriptions_with_context(content_sequence, document_id)

        # 3. 替换markdown中的图片引用
        def replace_image(match):
            img_ref = match.group(1)  # xxx.png
            img_filename = os.path.basename(img_ref)

            # 从content_sequence中查找图片信息
            img_item = next(
                (item for item in content_sequence
                 if item["type"] == "image" and item["filename"] == img_filename),
                None
            )

            if not img_item or not img_item.get("description"):
                return match.group(0)

            # 构建替换文本
            return (
                f"\n[IMAGE:{img_ref}]\n"
                f"<figure>\n"
                f"<figure_type>{img_item['figure_type']}</figure_type>\n"
                f"<figure_description>{img_item['description']}</figure_description>\n"
                f"</figure>\n"
            )

        pattern = r'!\[\]\(([^)]+\.(?:jpeg|jpg|png|gif|webp))\)'
        replaced = re.sub(pattern, replace_image, markdown_content)

        logger.info(
            "generate_and_replace_images_completed",
            document_id=document_id
        )

        return replaced

    @staticmethod
    def cleanup_temp_files(document_id: str):
        """
        清理临时文件

        Args:
            document_id: 文档ID
        """
        try:
            temp_dir = Path(settings.cache_dir) / "conversions" / document_id
            if temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir)
                logger.info("temp_files_cleaned", document_id=document_id)
        except Exception as e:
            logger.warning(
                "cleanup_temp_files_failed",
                document_id=document_id,
                error=str(e)
            )


# 全局实例
conversion_service = ConversionService()
