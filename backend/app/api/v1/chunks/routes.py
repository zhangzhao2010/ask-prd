"""
Chunks API路由
提供chunk相关的工具接口，如图片访问
"""
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.database import Chunk
from app.utils.s3_client import s3_client

logger = get_logger(__name__)
router = APIRouter()


@router.get("/{chunk_id}/image")
async def get_chunk_image(
    chunk_id: str,
    db: Session = Depends(get_db)
):
    """
    获取chunk的图片

    - 支持从本地缓存或S3获取图片
    - 返回图片文件
    """
    logger.info("api_get_chunk_image", chunk_id=chunk_id)

    # 查询chunk
    chunk = db.query(Chunk).filter(Chunk.id == chunk_id).first()

    if not chunk:
        logger.error("chunk_not_found", chunk_id=chunk_id)
        raise HTTPException(status_code=404, detail=f"Chunk不存在: {chunk_id}")

    if chunk.chunk_type != "image":
        logger.error("chunk_not_image", chunk_id=chunk_id, chunk_type=chunk.chunk_type)
        raise HTTPException(status_code=400, detail=f"Chunk不是图片类型: {chunk.chunk_type}")

    # 尝试从本地缓存获取
    if chunk.image_local_path:
        local_path = Path(chunk.image_local_path)
        if local_path.exists():
            logger.info("serving_image_from_cache", chunk_id=chunk_id, path=str(local_path))
            return FileResponse(
                path=str(local_path),
                media_type="image/png",  # 根据实际类型调整
                filename=chunk.image_filename or f"{chunk_id}.png"
            )

    # 从S3下载
    if chunk.image_s3_key:
        try:
            import tempfile
            temp_file = Path(tempfile.gettempdir()) / f"{chunk_id}_{chunk.image_filename}"

            logger.info("downloading_image_from_s3", chunk_id=chunk_id, s3_key=chunk.image_s3_key)
            s3_client.download_file(chunk.image_s3_key, str(temp_file))

            # 更新本地缓存路径（可选）
            # chunk.image_local_path = str(temp_file)
            # db.commit()

            return FileResponse(
                path=str(temp_file),
                media_type="image/png",
                filename=chunk.image_filename or f"{chunk_id}.png"
            )

        except Exception as e:
            logger.error("download_image_failed", chunk_id=chunk_id, error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail=f"下载图片失败: {str(e)}")

    # 无法获取图片
    logger.error("image_not_available", chunk_id=chunk_id)
    raise HTTPException(status_code=404, detail="图片文件不可用")
