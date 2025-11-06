"""
知识库管理API路由
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    KnowledgeBaseListResponse,
    KnowledgeBaseDetailResponse,
    PaginationMeta
)
from app.services.knowledge_base_service import KnowledgeBaseService

logger = get_logger(__name__)
router = APIRouter()


@router.post("", response_model=KnowledgeBaseResponse, status_code=201)
async def create_knowledge_base(
    kb_data: KnowledgeBaseCreate,
    db: Session = Depends(get_db)
):
    """
    创建知识库

    - 自动创建OpenSearch索引
    - 生成唯一的知识库ID
    """
    logger.info("api_create_knowledge_base", name=kb_data.name)

    kb = KnowledgeBaseService.create_knowledge_base(db, kb_data)
    return KnowledgeBaseResponse.model_validate(kb)


@router.get("", response_model=KnowledgeBaseListResponse)
async def list_knowledge_bases(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """
    列出所有知识库

    - 分页返回
    - 按创建时间倒序
    """
    logger.info("api_list_knowledge_bases", page=page, page_size=page_size)

    kbs, total = KnowledgeBaseService.list_knowledge_bases(db, page, page_size)

    total_pages = (total + page_size - 1) // page_size

    return KnowledgeBaseListResponse(
        items=[KnowledgeBaseResponse.model_validate(kb) for kb in kbs],
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages
        )
    )


@router.get("/{kb_id}", response_model=KnowledgeBaseDetailResponse)
async def get_knowledge_base(
    kb_id: str,
    db: Session = Depends(get_db)
):
    """
    获取知识库详情

    - 包含统计信息（文档数、chunk数、总大小）
    """
    logger.info("api_get_knowledge_base", kb_id=kb_id)

    kb = KnowledgeBaseService.get_knowledge_base(db, kb_id)
    stats = KnowledgeBaseService.get_knowledge_base_stats(db, kb_id)

    # 构造详情响应
    kb_dict = {
        **KnowledgeBaseResponse.model_validate(kb).model_dump(),
        "stats": stats
    }

    return KnowledgeBaseDetailResponse(**kb_dict)


@router.patch("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_id: str,
    kb_data: KnowledgeBaseUpdate,
    db: Session = Depends(get_db)
):
    """
    更新知识库

    - 可更新名称和描述
    - 名称不能与其他知识库重复
    """
    logger.info("api_update_knowledge_base", kb_id=kb_id)

    kb = KnowledgeBaseService.update_knowledge_base(db, kb_id, kb_data)
    return KnowledgeBaseResponse.model_validate(kb)


@router.delete("/{kb_id}", status_code=204)
async def delete_knowledge_base(
    kb_id: str,
    db: Session = Depends(get_db)
):
    """
    删除知识库

    - 软删除数据库记录
    - 真删除OpenSearch索引
    - 级联删除所有关联数据（documents, chunks, tasks, queries）
    """
    logger.info("api_delete_knowledge_base", kb_id=kb_id)

    KnowledgeBaseService.delete_knowledge_base(db, kb_id)
    return None
