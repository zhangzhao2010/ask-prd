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
from app.services.query_service import query_service

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
            # 使用新的Two-Stage执行器
            async for event in query_service.execute_query_two_stage(
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
            try:
                error_event = {
                    "type": "error",
                    "message": f"查询失败: {str(e)}"
                }
                yield f"event: error\n"
                yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
            except Exception as inner_e:
                logger.error("failed_to_send_error_event", error=str(inner_e))

        finally:
            # 确保流正确关闭
            try:
                # 发送一个完成事件
                done_event = {
                    "type": "done"
                }
                yield f"event: done\n"
                yield f"data: {json.dumps(done_event, ensure_ascii=False)}\n\n"
            except Exception:
                pass  # 忽略关闭时的错误

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用nginx缓冲
        }
    )
