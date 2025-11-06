"""
同步任务服务
管理PDF文档的异步处理任务
"""
import uuid
from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.config import settings
from app.core.logging import get_logger
from app.core.errors import (
    KnowledgeBaseNotFoundError,
    DocumentNotFoundError
)
from app.models.database import SyncTask, KnowledgeBase, Document

logger = get_logger(__name__)


class TaskService:
    """同步任务服务"""

    @staticmethod
    def create_sync_task(
        db: Session,
        kb_id: str,
        task_type: str,
        document_ids: Optional[List[str]] = None
    ) -> SyncTask:
        """
        创建同步任务

        Args:
            db: 数据库会话
            kb_id: 知识库ID
            task_type: 任务类型 (full_sync | incremental)
            document_ids: 文档ID列表（full_sync时为空）

        Returns:
            SyncTask对象

        Raises:
            KnowledgeBaseNotFoundError: 知识库不存在
        """
        logger.info(
            "creating_sync_task",
            kb_id=kb_id,
            task_type=task_type,
            document_count=len(document_ids) if document_ids else 0
        )

        # 验证知识库存在
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise KnowledgeBaseNotFoundError(kb_id)

        # 检查是否已有运行中的任务
        running_task = db.query(SyncTask).filter(
            SyncTask.kb_id == kb_id,
            SyncTask.status.in_(["pending", "running"])
        ).first()

        if running_task:
            logger.warning(
                "sync_task_already_running",
                kb_id=kb_id,
                running_task_id=running_task.id
            )
            from app.core.errors import ASKPRDException
            raise ASKPRDException(
                error_code="7002",
                message="该知识库已有同步任务在运行",
                details={"running_task_id": running_task.id},
                status_code=400
            )

        # 确定要处理的文档
        if task_type == "full_sync":
            # 全量同步：所有uploaded状态的文档
            documents = db.query(Document).filter(
                Document.kb_id == kb_id,
                Document.status == "uploaded"
            ).all()
            doc_ids = [doc.id for doc in documents]
        else:
            # 增量同步：指定的文档
            doc_ids = document_ids or []

            # 验证文档存在且属于该知识库
            if doc_ids:
                docs = db.query(Document).filter(
                    Document.id.in_(doc_ids),
                    Document.kb_id == kb_id
                ).all()

                if len(docs) != len(doc_ids):
                    found_ids = {doc.id for doc in docs}
                    missing_ids = set(doc_ids) - found_ids
                    raise DocumentNotFoundError(",".join(missing_ids))

        if not doc_ids:
            logger.warning("no_documents_to_sync", kb_id=kb_id)

        # 创建任务
        task_id = f"task-{uuid.uuid4()}"
        task = SyncTask(
            id=task_id,
            kb_id=kb_id,
            task_type=task_type,
            status="pending",
            total_documents=len(doc_ids),
            processed_documents=0,
            failed_documents=0,
            created_at=datetime.utcnow()
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        logger.info(
            "sync_task_created",
            task_id=task_id,
            kb_id=kb_id,
            total_documents=len(doc_ids)
        )

        return task

    @staticmethod
    def get_task(db: Session, task_id: str) -> Optional[SyncTask]:
        """
        获取任务详情

        Args:
            db: 数据库会话
            task_id: 任务ID

        Returns:
            SyncTask对象或None
        """
        return db.query(SyncTask).filter(SyncTask.id == task_id).first()

    @staticmethod
    def list_tasks(
        db: Session,
        kb_id: str,
        status: Optional[str] = None,
        limit: int = 10
    ) -> List[SyncTask]:
        """
        列出任务

        Args:
            db: 数据库会话
            kb_id: 知识库ID
            status: 过滤状态
            limit: 返回数量

        Returns:
            任务列表

        Raises:
            KnowledgeBaseNotFoundError: 知识库不存在
        """
        # 验证知识库存在
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise KnowledgeBaseNotFoundError(kb_id)

        query = db.query(SyncTask).filter(SyncTask.kb_id == kb_id)

        if status:
            query = query.filter(SyncTask.status == status)

        tasks = query.order_by(desc(SyncTask.created_at)).limit(limit).all()

        return tasks

    @staticmethod
    def update_task_status(
        db: Session,
        task_id: str,
        status: str,
        error_message: Optional[str] = None
    ):
        """
        更新任务状态

        Args:
            db: 数据库会话
            task_id: 任务ID
            status: 新状态
            error_message: 错误信息
        """
        task = db.query(SyncTask).filter(SyncTask.id == task_id).first()
        if not task:
            logger.warning("task_not_found", task_id=task_id)
            return

        task.status = status
        if error_message:
            task.error_message = error_message

        if status in ["completed", "failed", "partial_success"]:
            task.completed_at = datetime.utcnow()

        db.commit()

        logger.info(
            "task_status_updated",
            task_id=task_id,
            status=status
        )

    @staticmethod
    def update_task_progress(
        db: Session,
        task_id: str,
        processed: int,
        failed: int = 0
    ):
        """
        更新任务进度

        Args:
            db: 数据库会话
            task_id: 任务ID
            processed: 已处理数量
            failed: 失败数量
        """
        task = db.query(SyncTask).filter(SyncTask.id == task_id).first()
        if not task:
            logger.warning("task_not_found", task_id=task_id)
            return

        task.processed_documents = processed
        task.failed_documents = failed

        db.commit()

        logger.debug(
            "task_progress_updated",
            task_id=task_id,
            processed=processed,
            failed=failed,
            total=task.total_documents
        )

    @staticmethod
    def get_documents_to_process(
        db: Session,
        kb_id: str,
        task_type: str,
        document_ids: Optional[List[str]] = None
    ) -> List[Document]:
        """
        获取需要处理的文档列表

        Args:
            db: 数据库会话
            kb_id: 知识库ID
            task_type: 任务类型
            document_ids: 指定的文档ID列表

        Returns:
            文档列表
        """
        if task_type == "full_sync":
            # 全量同步：所有uploaded状态的文档
            documents = db.query(Document).filter(
                Document.kb_id == kb_id,
                Document.status == "uploaded"
            ).all()
        else:
            # 增量同步：指定的文档
            if not document_ids:
                return []

            documents = db.query(Document).filter(
                Document.id.in_(document_ids),
                Document.kb_id == kb_id
            ).all()

        logger.info(
            "documents_to_process",
            kb_id=kb_id,
            task_type=task_type,
            count=len(documents)
        )

        return documents

    @staticmethod
    def cancel_task(db: Session, task_id: str) -> bool:
        """
        取消任务（仅对pending状态有效）

        Args:
            db: 数据库会话
            task_id: 任务ID

        Returns:
            是否成功取消
        """
        task = db.query(SyncTask).filter(SyncTask.id == task_id).first()
        if not task:
            logger.warning("task_not_found", task_id=task_id)
            return False

        if task.status != "pending":
            logger.warning(
                "cannot_cancel_task",
                task_id=task_id,
                status=task.status
            )
            return False

        task.status = "cancelled"
        task.completed_at = datetime.utcnow()
        db.commit()

        logger.info("task_cancelled", task_id=task_id)
        return True


# 全局实例
task_service = TaskService()
