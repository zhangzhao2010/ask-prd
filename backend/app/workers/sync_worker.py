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
from app.utils.s3_client import s3_client

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

            # Step 1: 下载PDF from S3
            logger.info("downloading_pdf", document_id=document_id)

            pdf_s3_key = document.s3_key
            pdf_local_path = Path(settings.cache_dir) / "pdfs" / f"{document_id}.pdf"
            pdf_local_path.parent.mkdir(parents=True, exist_ok=True)

            s3_client.download_file(pdf_s3_key, str(pdf_local_path))

            logger.info(
                "pdf_downloaded",
                document_id=document_id,
                local_path=str(pdf_local_path)
            )

            # Step 2: PDF → Markdown
            logger.info("converting_pdf", document_id=document_id)

            markdown_content, images_info = conversion_service.convert_pdf_to_markdown(
                db=db,
                document_id=document_id,
                pdf_local_path=str(pdf_local_path)
            )

            logger.info(
                "pdf_converted",
                document_id=document_id,
                markdown_length=len(markdown_content),
                images_count=len(images_info)
            )

            # Step 3: 生成图片描述
            if images_info:
                logger.info("generating_image_descriptions", document_id=document_id)

                images_info = conversion_service.generate_image_descriptions(
                    images_info=images_info,
                    document_id=document_id
                )

                logger.info(
                    "image_descriptions_generated",
                    document_id=document_id,
                    count=len(images_info)
                )

            # Step 4: 上传转换结果到S3
            logger.info("uploading_conversion_results", document_id=document_id)

            markdown_s3_key, image_s3_keys = conversion_service.upload_conversion_results(
                db=db,
                document_id=document_id,
                markdown_content=markdown_content,
                images_info=images_info
            )

            logger.info(
                "conversion_results_uploaded",
                document_id=document_id,
                markdown_s3_key=markdown_s3_key
            )

            # Step 5: 文本分块
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

            # Step 7: 更新图片chunk的S3路径
            if image_s3_keys:
                embedding_service.update_chunk_s3_paths(
                    db=db,
                    document_id=document_id,
                    image_s3_keys=image_s3_keys
                )

            # Step 8: 生成向量并索引
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

            # 清理下载的PDF
            if pdf_local_path.exists():
                pdf_local_path.unlink()

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
