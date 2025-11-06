"""
PDF转换服务
使用Marker将PDF转换为Markdown并提取图片
"""
import base64
from pathlib import Path
from typing import Dict, List, Tuple
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
from app.utils.s3_client import s3_client
from app.utils.bedrock_client import bedrock_client

logger = get_logger(__name__)


class ConversionService:
    """PDF转换服务"""

    @staticmethod
    def convert_pdf_to_markdown(
        db: Session,
        document_id: str,
        pdf_local_path: str
    ) -> Tuple[str, List[Dict]]:
        """
        转换PDF为Markdown并提取图片

        Args:
            db: 数据库会话
            document_id: 文档ID
            pdf_local_path: PDF本地路径

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
            # 创建临时输出目录
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
                renderer="pdf",  # PDF渲染器
                config=None  # 使用默认配置
            )

            # 执行转换
            logger.info("converting_pdf", document_id=document_id)
            rendered = converter(pdf_local_path)

            # 提取Markdown文本
            markdown_content = text_from_rendered(rendered)

            # 提取图片
            images_info = ConversionService._extract_images(
                rendered=rendered,
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
    def _extract_images(
        rendered: Dict,
        output_dir: Path,
        document_id: str
    ) -> List[Dict]:
        """
        从渲染结果中提取图片

        Args:
            rendered: Marker渲染结果
            output_dir: 输出目录
            document_id: 文档ID

        Returns:
            图片信息列表
        """
        images_info = []
        images_dir = output_dir / "images"
        images_dir.mkdir(exist_ok=True)

        # Marker的rendered结果包含图片数据
        # 格式可能类似: rendered['images'] 或 rendered['figures']
        # 这里需要根据实际的Marker输出结构调整

        images_data = rendered.get("images", [])
        if not images_data:
            logger.info("no_images_found", document_id=document_id)
            return images_info

        for idx, img_data in enumerate(images_data):
            try:
                # 生成图片文件名
                img_filename = f"img_{idx:03d}.png"
                img_path = images_dir / img_filename

                # 保存图片
                # 根据img_data的格式保存（可能是PIL Image或bytes）
                if hasattr(img_data, 'save'):
                    # PIL Image对象
                    img_data.save(img_path)
                elif isinstance(img_data, bytes):
                    # 字节数据
                    with open(img_path, 'wb') as f:
                        f.write(img_data)
                else:
                    logger.warning(
                        "unknown_image_format",
                        document_id=document_id,
                        index=idx,
                        type=type(img_data).__name__
                    )
                    continue

                images_info.append({
                    "filename": img_filename,
                    "path": str(img_path),
                    "index": idx,
                    "description": None  # 稍后生成
                })

                logger.debug(
                    "image_extracted",
                    document_id=document_id,
                    filename=img_filename
                )

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
    def upload_conversion_results(
        db: Session,
        document_id: str,
        markdown_content: str,
        images_info: List[Dict]
    ) -> Tuple[str, List[str]]:
        """
        上传转换结果到S3

        Args:
            db: 数据库会话
            document_id: 文档ID
            markdown_content: Markdown内容
            images_info: 图片信息列表

        Returns:
            (markdown_s3_key, image_s3_keys)

        Raises:
            DocumentNotFoundError: 文档不存在
        """
        logger.info(
            "start_uploading_conversion_results",
            document_id=document_id,
            images_count=len(images_info)
        )

        # 获取文档信息
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise DocumentNotFoundError(document_id)

        kb_prefix = doc.knowledge_base.s3_prefix

        try:
            # 1. 上传Markdown文件
            markdown_s3_key = f"{kb_prefix}converted/{document_id}/content.md"

            # 创建临时文件
            temp_md_path = Path(settings.cache_dir) / "temp" / f"{document_id}.md"
            temp_md_path.parent.mkdir(parents=True, exist_ok=True)
            temp_md_path.write_text(markdown_content, encoding="utf-8")

            # 上传到S3
            s3_client.upload_file(str(temp_md_path), markdown_s3_key)

            logger.info(
                "markdown_uploaded",
                document_id=document_id,
                s3_key=markdown_s3_key
            )

            # 2. 上传图片
            image_s3_keys = []
            for img_info in images_info:
                img_filename = img_info["filename"]
                img_local_path = img_info["path"]

                img_s3_key = f"{kb_prefix}converted/{document_id}/images/{img_filename}"

                # 上传图片
                s3_client.upload_file(img_local_path, img_s3_key)
                image_s3_keys.append(img_s3_key)

                logger.debug(
                    "image_uploaded",
                    document_id=document_id,
                    filename=img_filename,
                    s3_key=img_s3_key
                )

            # 3. 更新文档记录
            doc.s3_key_markdown = markdown_s3_key
            doc.local_markdown_path = str(temp_md_path)  # 保存本地缓存路径
            db.commit()

            logger.info(
                "conversion_results_uploaded",
                document_id=document_id,
                markdown_s3_key=markdown_s3_key,
                images_count=len(image_s3_keys)
            )

            return markdown_s3_key, image_s3_keys

        except Exception as e:
            logger.error(
                "upload_conversion_results_failed",
                document_id=document_id,
                error=str(e),
                exc_info=True
            )
            raise

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
