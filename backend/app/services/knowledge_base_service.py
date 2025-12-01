"""
知识库管理Service
业务逻辑层
"""
import uuid
from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.database import KnowledgeBase, Document, Chunk
from app.models.schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseStats
)
from app.core.logging import get_logger
from app.core.errors import (
    KnowledgeBaseNotFoundError,
    KnowledgeBaseAlreadyExistsError,
    OpenSearchConnectionError
)
from app.utils.opensearch_client import opensearch_client

logger = get_logger(__name__)


class KnowledgeBaseService:
    """知识库管理服务"""

    @staticmethod
    def create_knowledge_base(
        db: Session,
        kb_data: KnowledgeBaseCreate,
        owner_id: int
    ) -> KnowledgeBase:
        """
        创建知识库

        Args:
            db: 数据库会话
            kb_data: 知识库创建数据
            owner_id: 所有者用户ID

        Returns:
            创建的知识库对象

        Raises:
            KnowledgeBaseAlreadyExistsError: 知识库名称已存在
            OpenSearchConnectionError: OpenSearch操作失败
        """
        # 1. 检查名称是否已存在
        existing = db.query(KnowledgeBase).filter(
            KnowledgeBase.name == kb_data.name
        ).first()

        if existing:
            raise KnowledgeBaseAlreadyExistsError(kb_data.name)

        # 2. 生成ID
        kb_id = f"kb-{uuid.uuid4()}"
        index_name = f"kb_{kb_id.replace('-', '_')}_index"

        logger.info(
            "creating_knowledge_base",
            kb_id=kb_id,
            name=kb_data.name,
            index_name=index_name
        )

        try:
            # 3. 创建OpenSearch索引
            opensearch_client.create_index(index_name, embedding_dimension=1024)

            # 4. 创建数据库记录
            kb = KnowledgeBase(
                id=kb_id,
                name=kb_data.name,
                description=kb_data.description,
                opensearch_index_name=index_name,
                status="active",
                owner_id=owner_id,
                visibility="private"  # 默认为私有
            )

            db.add(kb)
            db.commit()
            db.refresh(kb)

            logger.info(
                "knowledge_base_created",
                kb_id=kb_id,
                name=kb_data.name
            )

            return kb

        except OpenSearchConnectionError as e:
            db.rollback()
            logger.error("knowledge_base_creation_failed", kb_id=kb_id, error=str(e))
            raise

        except Exception as e:
            db.rollback()
            logger.error("knowledge_base_creation_failed", kb_id=kb_id, error=str(e))
            # 尝试清理OpenSearch索引
            try:
                opensearch_client.delete_index(index_name)
            except:
                pass
            raise

    @staticmethod
    def get_knowledge_base(db: Session, kb_id: str) -> KnowledgeBase:
        """
        获取知识库

        Args:
            db: 数据库会话
            kb_id: 知识库ID

        Returns:
            知识库对象

        Raises:
            KnowledgeBaseNotFoundError: 知识库不存在
        """
        kb = db.query(KnowledgeBase).filter(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.status == "active"
        ).first()

        if not kb:
            raise KnowledgeBaseNotFoundError(kb_id)

        return kb

    @staticmethod
    def list_knowledge_bases(
        db: Session,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[KnowledgeBase], int]:
        """
        列出知识库

        Args:
            db: 数据库会话
            page: 页码（从1开始）
            page_size: 每页数量

        Returns:
            (知识库列表, 总数)
        """
        query = db.query(KnowledgeBase).filter(
            KnowledgeBase.status == "active"
        )

        total = query.count()

        kbs = query.order_by(
            KnowledgeBase.created_at.desc()
        ).offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        return kbs, total

    @staticmethod
    def update_knowledge_base(
        db: Session,
        kb_id: str,
        kb_data: KnowledgeBaseUpdate
    ) -> KnowledgeBase:
        """
        更新知识库

        Args:
            db: 数据库会话
            kb_id: 知识库ID
            kb_data: 更新数据

        Returns:
            更新后的知识库对象

        Raises:
            KnowledgeBaseNotFoundError: 知识库不存在
            KnowledgeBaseAlreadyExistsError: 名称已被占用
        """
        kb = KnowledgeBaseService.get_knowledge_base(db, kb_id)

        # 如果要更新名称，检查是否重复
        if kb_data.name and kb_data.name != kb.name:
            existing = db.query(KnowledgeBase).filter(
                KnowledgeBase.name == kb_data.name,
                KnowledgeBase.id != kb_id
            ).first()

            if existing:
                raise KnowledgeBaseAlreadyExistsError(kb_data.name)

            kb.name = kb_data.name

        if kb_data.description is not None:
            kb.description = kb_data.description

        kb.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(kb)

        logger.info("knowledge_base_updated", kb_id=kb_id)
        return kb

    @staticmethod
    def delete_knowledge_base(db: Session, kb_id: str) -> bool:
        """
        删除知识库（软删除）

        Args:
            db: 数据库会话
            kb_id: 知识库ID

        Returns:
            是否删除成功

        Raises:
            KnowledgeBaseNotFoundError: 知识库不存在
        """
        kb = KnowledgeBaseService.get_knowledge_base(db, kb_id)

        try:
            # 1. 软删除数据库记录
            kb.status = "deleted"
            kb.updated_at = datetime.utcnow()

            # 2. 删除OpenSearch索引（真删除）
            if kb.opensearch_index_name:
                opensearch_client.delete_index(kb.opensearch_index_name)

            db.commit()

            logger.info("knowledge_base_deleted", kb_id=kb_id)
            return True

        except Exception as e:
            db.rollback()
            logger.error("knowledge_base_deletion_failed", kb_id=kb_id, error=str(e))
            raise

    @staticmethod
    def get_knowledge_base_stats(db: Session, kb_id: str) -> KnowledgeBaseStats:
        """
        获取知识库统计信息

        Args:
            db: 数据库会话
            kb_id: 知识库ID

        Returns:
            统计信息
        """
        # 文档数量
        document_count = db.query(func.count(Document.id)).filter(
            Document.kb_id == kb_id,
            Document.status == "completed"
        ).scalar() or 0

        # Chunk数量
        chunk_count = db.query(func.count(Chunk.id)).filter(
            Chunk.kb_id == kb_id
        ).scalar() or 0

        # 总文件大小
        total_size = db.query(func.sum(Document.file_size)).filter(
            Document.kb_id == kb_id
        ).scalar() or 0

        return KnowledgeBaseStats(
            document_count=document_count,
            chunk_count=chunk_count,
            total_size_bytes=total_size
        )

    @staticmethod
    def list_knowledge_bases_for_user(
        db: Session,
        user,  # User对象
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[KnowledgeBase], int]:
        """
        根据用户权限列出知识库

        Args:
            db: 数据库会话
            user: 当前用户对象
            page: 页码（从1开始）
            page_size: 每页数量

        Returns:
            (知识库列表, 总数)
        """
        from app.models.database import KBPermission

        # 管理员可以看到所有
        if user.role == "admin":
            query = db.query(KnowledgeBase).filter(KnowledgeBase.status == "active")
            total = query.count()
            kbs = query.order_by(KnowledgeBase.created_at.desc()).offset(
                (page - 1) * page_size
            ).limit(page_size).all()
            return kbs, total

        # 普通用户：自己创建的 + public + 被共享的
        # 1. 自己创建的
        owned_query = db.query(KnowledgeBase).filter(
            KnowledgeBase.owner_id == user.id,
            KnowledgeBase.status == "active"
        )

        # 2. 公开的
        public_query = db.query(KnowledgeBase).filter(
            KnowledgeBase.visibility == "public",
            KnowledgeBase.status == "active"
        )

        # 3. 被共享的
        shared_kb_ids = db.query(KBPermission.kb_id).filter(
            KBPermission.user_id == user.id
        ).subquery()

        shared_query = db.query(KnowledgeBase).filter(
            KnowledgeBase.id.in_(shared_kb_ids),
            KnowledgeBase.status == "active"
        )

        # 合并查询（使用UNION）
        combined_query = owned_query.union(public_query, shared_query)

        # 获取总数和分页结果
        total = combined_query.count()
        kbs = combined_query.order_by(KnowledgeBase.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        return kbs, total
