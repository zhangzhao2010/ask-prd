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
from app.models.database import Chunk, Document

logger = get_logger(__name__)
router = APIRouter()


@router.get("/{chunk_id}/image")
async def get_chunk_image(
    chunk_id: str,
    db: Session = Depends(get_db)
):
    """
    获取chunk的图片（从本地文件系统）

    - 图片存储在 markdowns/{document_id}/ 目录
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

    # 获取文档的markdown路径
    doc = db.query(Document).filter(Document.id == chunk.document_id).first()
    if not doc or not doc.local_markdown_path:
        logger.error("document_not_found", chunk_id=chunk_id, document_id=chunk.document_id)
        raise HTTPException(status_code=404, detail="文档不存在")

    # 构建图片路径（与markdown同目录）
    markdown_dir = Path(doc.local_markdown_path).parent
    image_path = markdown_dir / chunk.image_filename

    if not image_path.exists():
        logger.error("image_not_found", chunk_id=chunk_id, path=str(image_path))
        raise HTTPException(status_code=404, detail="图片文件不存在")

    # 判断Content-Type
    ext = chunk.image_filename.split('.')[-1].lower()
    content_type_map = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'webp': 'image/webp'
    }
    content_type = content_type_map.get(ext, 'application/octet-stream')

    logger.info("serving_image", chunk_id=chunk_id, path=str(image_path))
    return FileResponse(
        path=str(image_path),
        media_type=content_type,
        filename=chunk.image_filename or f"{chunk_id}.png"
    )
