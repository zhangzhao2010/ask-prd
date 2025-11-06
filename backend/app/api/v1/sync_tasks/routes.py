"""
同步任务API路由
"""
import asyncio
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.schemas import (
    SyncTaskCreate,
    SyncTaskResponse,
    SyncTaskListResponse,
    PaginationMeta
)
from app.services.task_service import task_service
from app.workers.sync_worker import sync_worker

logger = get_logger(__name__)
router = APIRouter()


@router.post("", response_model=SyncTaskResponse, status_code=201)
async def create_sync_task(
    task_data: SyncTaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    创建同步任务

    - 创建任务记录
    - 在后台异步执行处理流程
    - 任务类型：
      - full_sync: 同步知识库中所有uploaded状态的文档
      - incremental: 同步指定的文档
    """
    logger.info(
        "api_create_sync_task",
        kb_id=task_data.kb_id,
        task_type=task_data.task_type
    )

    # 创建任务
    task = task_service.create_sync_task(
        db=db,
        kb_id=task_data.kb_id,
        task_type=task_data.task_type,
        document_ids=task_data.document_ids
    )

    # 添加后台任务
    background_tasks.add_task(
        sync_worker.process_sync_task_sync,
        task.id
    )

    # 计算进度
    progress = 0
    if task.total_documents > 0:
        progress = int((task.processed_documents / task.total_documents) * 100)

    return SyncTaskResponse(
        id=task.id,
        kb_id=task.kb_id,
        task_type=task.task_type,
        status=task.status,
        progress=progress,
        current_step=None,
        total_documents=task.total_documents,
        processed_documents=task.processed_documents,
        failed_documents=task.failed_documents,
        error_message=task.error_message,
        started_at=task.started_at,
        completed_at=task.completed_at,
        created_at=task.created_at
    )


@router.get("", response_model=SyncTaskListResponse)
async def list_sync_tasks(
    kb_id: str = Query(..., description="知识库ID"),
    status: str = Query(None, description="过滤状态"),
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    db: Session = Depends(get_db)
):
    """
    列出同步任务

    - 按创建时间倒序
    - 支持按状态过滤
    """
    logger.info(
        "api_list_sync_tasks",
        kb_id=kb_id,
        status=status,
        limit=limit
    )

    tasks = task_service.list_tasks(
        db=db,
        kb_id=kb_id,
        status=status,
        limit=limit
    )

    # 转换为响应模型
    items = []
    for task in tasks:
        progress = 0
        if task.total_documents > 0:
            progress = int((task.processed_documents / task.total_documents) * 100)

        items.append(SyncTaskResponse(
            id=task.id,
            kb_id=task.kb_id,
            task_type=task.task_type,
            status=task.status,
            progress=progress,
            current_step=task.current_step,
            total_documents=task.total_documents,
            processed_documents=task.processed_documents,
            failed_documents=task.failed_documents,
            error_message=task.error_message,
            started_at=task.started_at,
            completed_at=task.completed_at,
            created_at=task.created_at
        ))

    return SyncTaskListResponse(
        items=items,
        meta=PaginationMeta(
            page=1,
            page_size=limit,
            total=len(items),
            total_pages=1
        )
    )


@router.get("/{task_id}", response_model=SyncTaskResponse)
async def get_sync_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    获取同步任务详情

    - 返回任务当前状态和进度
    """
    logger.info("api_get_sync_task", task_id=task_id)

    task = task_service.get_task(db, task_id)
    if not task:
        from app.core.errors import ASKPRDException
        raise ASKPRDException(
            error_code="7001",
            message=f"同步任务不存在: {task_id}",
            details={"task_id": task_id},
            status_code=404
        )

    # 计算进度
    progress = 0
    if task.total_documents > 0:
        progress = int((task.processed_documents / task.total_documents) * 100)

    return SyncTaskResponse(
        id=task.id,
        kb_id=task.kb_id,
        task_type=task.task_type,
        status=task.status,
        progress=progress,
        current_step=task.current_step,
        total_documents=task.total_documents,
        processed_documents=task.processed_documents,
        failed_documents=task.failed_documents,
        error_message=task.error_message,
        started_at=task.started_at,
        completed_at=task.completed_at,
        created_at=task.created_at
    )


@router.delete("/{task_id}", status_code=204)
async def cancel_sync_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    取消同步任务

    - 只能取消pending状态的任务
    - running状态的任务无法取消
    """
    logger.info("api_cancel_sync_task", task_id=task_id)

    success = task_service.cancel_task(db, task_id)

    if not success:
        from app.core.errors import ASKPRDException
        raise ASKPRDException(
            error_code="7003",
            message="无法取消该任务（任务不存在或已开始执行）",
            details={"task_id": task_id},
            status_code=400
        )

    return None
