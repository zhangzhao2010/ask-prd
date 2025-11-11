"""
同步任务Worker
异步处理PDF文档的转换、分块、向量化流程
"""
import asyncio
from pathlib import Path
from typing import List
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.database import SessionLocal
from app.models.database import Document, SyncTask
from app.services.task_service import task_service
from app.services.conversion_service import conversion_service
from app.services.chunking_service import chunking_service
from app.services.embedding_service import embedding_service

logger = get_logger(__name__)


class SyncWorker:
    """同步任务Worker"""

    @staticmethod
    async def process_sync_task(task_id: str):
        """
        异步处理同步任务

        Args:
            task_id: 任务ID
        """
        db = SessionLocal()

        try:
            # 获取任务
            task = task_service.get_task(db, task_id)
            if not task:
                logger.error("task_not_found", task_id=task_id)
                return

            logger.info(
                "start_processing_sync_task",
                task_id=task_id,
                kb_id=task.kb_id,
                task_type=task.task_type,
                total_documents=task.total_documents
            )

            # 更新任务状态为running
            task_service.update_task_status(db, task_id, "running")

            # 获取要处理的文档
            documents = task_service.get_documents_to_process(
                db=db,
                kb_id=task.kb_id,
                task_type=task.task_type,
                document_ids=None  # TODO: 从任务中获取document_ids
            )

            if not documents:
                logger.warning("no_documents_to_process", task_id=task_id)
                task_service.update_task_status(db, task_id, "completed")
                return

            # 处理每个文档
            processed = 0
            failed = 0

            for doc in documents:
                try:
                    logger.info(
                        "processing_document",
                        task_id=task_id,
                        document_id=doc.id,
                        filename=doc.filename,
                        progress=f"{processed + 1}/{len(documents)}"
                    )

                    # 处理单个文档
                    success = await SyncWorker._process_single_document(
                        db=db,
                        document=doc
                    )

                    if success:
                        processed += 1
                    else:
                        failed += 1

                    # 更新进度
                    task_service.update_task_progress(
                        db=db,
                        task_id=task_id,
                        processed=processed,
                        failed=failed
                    )

                except Exception as e:
                    logger.error(
                        "document_processing_failed",
                        task_id=task_id,
                        document_id=doc.id,
                        error=str(e),
                        exc_info=True
                    )
                    failed += 1

                    # 更新进度
                    task_service.update_task_progress(
                        db=db,
                        task_id=task_id,
                        processed=processed,
                        failed=failed
                    )

            # 确定最终状态
            if failed == 0:
                final_status = "completed"
            elif processed == 0:
                final_status = "failed"
            else:
                final_status = "partial_success"

            # 更新任务状态
            task_service.update_task_status(
                db=db,
                task_id=task_id,
                status=final_status
            )

            logger.info(
                "sync_task_completed",
                task_id=task_id,
                status=final_status,
                processed=processed,
                failed=failed
            )

        except Exception as e:
            logger.error(
                "sync_task_failed",
                task_id=task_id,
                error=str(e),
                exc_info=True
            )

            # 更新任务状态为failed
            task_service.update_task_status(
                db=db,
                task_id=task_id,
                status="failed",
                error_message=str(e)
            )

        finally:
            db.close()

    @staticmethod
    async def _process_single_document(
        db: Session,
        document: Document
    ) -> bool:
        """
        处理单个文档

        流程：
        1. 下载PDF from S3
        2. PDF → Markdown (conversion_service)
        3. 文本分块 (chunking_service)
        4. 生成向量并索引 (embedding_service)
        5. 清理临时文件

        Args:
            db: 数据库会话
            document: 文档对象

        Returns:
            是否成功
        """
        document_id = document.id

        try:
            logger.info("start_document_processing", document_id=document_id)

            # Step 1: 获取本地PDF路径
            pdf_local_path = document.local_pdf_path
            if not pdf_local_path or not Path(pdf_local_path).exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_local_path}")

            logger.info(
                "pdf_path_verified",
                document_id=document_id,
                local_path=pdf_local_path
            )

            # Step 2: PDF → Markdown + 图片提取
            # 创建markdown输出目录（markdown和图片保存在同一目录）
            markdown_dir = Path(settings.markdown_dir) / document_id
            markdown_dir.mkdir(parents=True, exist_ok=True)

            logger.info("converting_pdf", document_id=document_id)

            # 将输出目录传给ConversionService
            markdown_content, images_info = conversion_service.convert_pdf_to_markdown(
                db=db,
                document_id=document_id,
                pdf_local_path=pdf_local_path,
                output_dir=markdown_dir
            )

            logger.info(
                "pdf_converted",
                document_id=document_id,
                markdown_length=len(markdown_content),
                images_count=len(images_info)
            )

            # Step 2.1: 立即保存原始markdown（Marker转换结果）
            content_markdown_path = markdown_dir / "content.md"
            with open(content_markdown_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            # 更新数据库记录（原始markdown已保存）
            document.local_markdown_path = str(content_markdown_path)
            db.commit()

            logger.info(
                "content_markdown_saved",
                document_id=document_id,
                path=str(content_markdown_path)
            )

            # Step 3: 生成带上下文的图片描述并替换markdown中的图片引用
            markdown_with_descriptions = conversion_service.generate_and_replace_images(
                markdown_content=markdown_content,
                doc_dir=str(markdown_dir),
                document_id=document_id
            )

            # Step 3.1: 保存纯文本版markdown（用于向量化，图片已替换为描述）
            text_markdown_path = Path(settings.text_markdown_dir) / f"{document_id}.md"
            text_markdown_path.parent.mkdir(parents=True, exist_ok=True)

            with open(text_markdown_path, 'w', encoding='utf-8') as f:
                f.write(markdown_with_descriptions)

            # 更新数据库记录（text markdown已保存）
            document.local_text_markdown_path = str(text_markdown_path)
            db.commit()

            logger.info(
                "text_markdown_saved",
                document_id=document_id,
                path=str(text_markdown_path)
            )

            # Step 4: 文本分块
            logger.info("chunking_text", document_id=document_id)

            text_chunks, image_chunks = chunking_service.chunk_markdown(
                db=db,
                document_id=document_id,
                markdown_content=markdown_content,
                images_info=images_info
            )

            logger.info(
                "text_chunked",
                document_id=document_id,
                text_chunks=len(text_chunks),
                image_chunks=len(image_chunks)
            )

            # Step 6: 保存chunks到数据库
            logger.info("saving_chunks", document_id=document_id)

            chunk_ids = chunking_service.save_chunks_to_db(
                db=db,
                document_id=document_id,
                text_chunks=text_chunks,
                image_chunks=image_chunks
            )

            logger.info(
                "chunks_saved",
                document_id=document_id,
                total_chunks=len(chunk_ids)
            )

            # Step 7: 生成向量并索引
            logger.info("generating_embeddings", document_id=document_id)

            indexed_count = embedding_service.generate_and_index_embeddings(
                db=db,
                document_id=document_id,
                chunk_ids=chunk_ids
            )

            logger.info(
                "embeddings_generated",
                document_id=document_id,
                indexed_count=indexed_count
            )

            # Step 9: 清理临时文件
            conversion_service.cleanup_temp_files(document_id)

            # 清理下载的PDF（本地存储模式下不需要清理PDF）
            # PDF是永久存储的，不是临时文件
            # if Path(pdf_local_path).exists():
            #     Path(pdf_local_path).unlink()

            logger.info(
                "document_processing_completed",
                document_id=document_id
            )

            return True

        except Exception as e:
            logger.error(
                "document_processing_failed",
                document_id=document_id,
                error=str(e),
                exc_info=True
            )
            return False

    @staticmethod
    def process_sync_task_sync(task_id: str):
        """
        同步方式处理任务（用于测试）

        Args:
            task_id: 任务ID
        """
        asyncio.run(SyncWorker.process_sync_task(task_id))


# 全局实例
sync_worker = SyncWorker()
