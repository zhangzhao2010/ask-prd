"""
查询API路由
智能问答接口
"""
import json
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.schemas import QueryHistoryListResponse, QueryHistoryResponse, PaginationMeta
from app.services.query_service import query_service
from app.models.database import QueryHistory

logger = get_logger(__name__)
router = APIRouter()


@router.post("/stream")
async def query_stream(
    kb_id: str = Query(..., description="知识库ID"),
    query: str = Query(..., min_length=1, max_length=1000, description="用户问题"),
    db: Session = Depends(get_db)
):
    """
    流式问答接口（SSE）

    - 实时返回答案生成过程
    - 支持状态更新、文本增量、完成事件
    - Content-Type: text/event-stream
    """
    logger.info(
        "api_query_stream",
        kb_id=kb_id,
        query=query[:100]
    )

    async def event_generator():
        """SSE事件生成器"""
        try:
            async for event in query_service.execute_query_stream(
                db=db,
                kb_id=kb_id,
                query_text=query
            ):
                # 构建SSE事件
                event_type = event.get("type", "unknown")

                # 格式化事件数据
                event_data = json.dumps(event, ensure_ascii=False)

                # SSE格式：event: type\ndata: json\n\n
                yield f"event: {event_type}\n"
                yield f"data: {event_data}\n\n"

        except Exception as e:
            logger.error(
                "query_stream_error",
                kb_id=kb_id,
                error=str(e),
                exc_info=True
            )

            # 发送错误事件
            error_event = {
                "type": "error",
                "message": f"查询失败: {str(e)}"
            }
            yield f"event: error\n"
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用nginx缓冲
        }
    )


@router.get("/history", response_model=QueryHistoryListResponse)
async def get_query_history(
    kb_id: str = Query(..., description="知识库ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """
    获取查询历史

    - 按创建时间倒序
    - 分页返回
    """
    logger.info(
        "api_get_query_history",
        kb_id=kb_id,
        page=page,
        page_size=page_size
    )

    # 查询总数
    total = db.query(QueryHistory).filter(
        QueryHistory.kb_id == kb_id
    ).count()

    # 分页查询
    offset = (page - 1) * page_size
    histories = db.query(QueryHistory).filter(
        QueryHistory.kb_id == kb_id
    ).order_by(QueryHistory.created_at.desc()).offset(offset).limit(page_size).all()

    # 转换为响应模型
    items = []
    for history in histories:
        items.append(QueryHistoryResponse(
            id=history.id,
            kb_id=history.kb_id,
            query_text=history.query_text,
            answer=history.answer,
            total_tokens=history.total_tokens,
            response_time_ms=history.response_time_ms,
            status=history.status,
            created_at=history.created_at
        ))

    total_pages = (total + page_size - 1) // page_size

    return QueryHistoryListResponse(
        items=items,
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages
        )
    )


@router.get("/history/{query_id}", response_model=QueryHistoryResponse)
async def get_query_detail(
    query_id: str,
    db: Session = Depends(get_db)
):
    """
    获取查询详情

    - 返回完整的查询记录
    """
    logger.info("api_get_query_detail", query_id=query_id)

    history = db.query(QueryHistory).filter(QueryHistory.id == query_id).first()

    if not history:
        from app.core.errors import ASKPRDException
        raise ASKPRDException(
            error_code="4001",
            message=f"查询记录不存在: {query_id}",
            details={"query_id": query_id},
            status_code=404
        )

    return QueryHistoryResponse(
        id=history.id,
        kb_id=history.kb_id,
        query_text=history.query_text,
        answer=history.answer,
        total_tokens=history.total_tokens,
        response_time_ms=history.response_time_ms,
        status=history.status,
        created_at=history.created_at
    )


@router.delete("/history/{query_id}")
async def delete_query_history(
    query_id: str,
    db: Session = Depends(get_db)
):
    """
    删除查询历史

    - 从数据库中删除指定的查询记录
    """
    logger.info("api_delete_query_history", query_id=query_id)

    history = db.query(QueryHistory).filter(QueryHistory.id == query_id).first()

    if not history:
        from app.core.errors import ASKPRDException
        raise ASKPRDException(
            error_code="4001",
            message=f"查询记录不存在: {query_id}",
            details={"query_id": query_id},
            status_code=404
        )

    try:
        db.delete(history)
        db.commit()

        logger.info("query_history_deleted", query_id=query_id)

        return {"message": "查询历史删除成功"}

    except Exception as e:
        db.rollback()
        logger.error("delete_query_history_failed", query_id=query_id, error=str(e), exc_info=True)
        from app.core.errors import ASKPRDException
        raise ASKPRDException(
            error_code="9999",
            message=f"删除查询历史失败: {str(e)}",
            details={"query_id": query_id}
        )
