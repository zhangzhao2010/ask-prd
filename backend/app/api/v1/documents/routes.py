"""
文档管理API路由
"""
from fastapi import APIRouter, Depends, File, UploadFile, Query, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.schemas import (
    DocumentResponse,
    DocumentListResponse,
    DocumentDetailResponse,
    PaginationMeta
)
from app.services.document_service import DocumentService

logger = get_logger(__name__)
router = APIRouter()


@router.post("", response_model=DocumentResponse, status_code=201)
async def upload_document(
    kb_id: str = Query(..., description="知识库ID"),
    file: UploadFile = File(..., description="PDF文件"),
    db: Session = Depends(get_db)
):
    """
    上传文档到知识库

    - 文件自动上传到S3
    - 创建文档记录
    - 初始状态为uploaded
    """
    logger.info("api_upload_document", kb_id=kb_id, filename=file.filename)

    # 验证文件类型
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="只支持PDF文件"
        )

    # 获取文件大小
    content = await file.read()
    file_size = len(content)
    
    # 重置文件指针
    await file.seek(0)

    # 上传文档
    doc = DocumentService.upload_document(
        db=db,
        kb_id=kb_id,
        file=file.file,
        filename=file.filename,
        file_size=file_size,
        content_type=file.content_type or "application/pdf"
    )

    return DocumentResponse.model_validate(doc)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    kb_id: str = Query(..., description="知识库ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: str = Query(None, description="文档状态过滤"),
    db: Session = Depends(get_db)
):
    """
    列出知识库中的文档

    - 分页返回
    - 按创建时间倒序
    - 可按状态过滤
    """
    logger.info(
        "api_list_documents",
        kb_id=kb_id,
        page=page,
        page_size=page_size,
        status=status
    )

    docs, total = DocumentService.list_documents(
        db, kb_id, page, page_size, status
    )

    total_pages = (total + page_size - 1) // page_size

    return DocumentListResponse(
        items=[DocumentResponse.model_validate(doc) for doc in docs],
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages
        )
    )


@router.get("/{doc_id}", response_model=DocumentDetailResponse)
async def get_document(
    doc_id: str,
    db: Session = Depends(get_db)
):
    """
    获取文档详情

    - 包含统计信息（chunk数）
    """
    logger.info("api_get_document", doc_id=doc_id)

    doc = DocumentService.get_document(db, doc_id)
    stats = DocumentService.get_document_stats(db, doc_id)

    # 构造详情响应
    doc_dict = {
        **DocumentResponse.model_validate(doc).model_dump(),
        "stats": stats
    }

    return DocumentDetailResponse(**doc_dict)


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    doc_id: str,
    db: Session = Depends(get_db)
):
    """
    删除文档

    - 软删除数据库记录
    - 真删除S3文件
    """
    logger.info("api_delete_document", doc_id=doc_id)

    DocumentService.delete_document(db, doc_id)
    return None


@router.get("/{document_id}/images/{image_filename}")
async def get_document_image(
    document_id: str,
    image_filename: str,
    db: Session = Depends(get_db)
):
    """
    获取文档的图片（从本地缓存提供）

    - 优先使用本地缓存
    - 缓存不存在时从S3下载
    - 返回图片二进制数据
    """
    from pathlib import Path
    from fastapi.responses import FileResponse
    from app.core.config import settings
    from app.utils.s3_client import s3_client

    logger.info(
        "api_get_document_image",
        document_id=document_id,
        image_filename=image_filename
    )

    # 1. 构建本地路径
    local_path = Path(settings.cache_dir) / "documents" / document_id / image_filename

    # 2. 检查文件是否存在
    if not local_path.exists():
        # 尝试从S3下载
        logger.info(
            "image_not_in_cache_downloading",
            document_id=document_id,
            image_filename=image_filename
        )

        # 从数据库查询图片的S3路径
        from app.models.database import Chunk

        image_chunk = db.query(Chunk).filter(
            Chunk.document_id == document_id,
            Chunk.chunk_type == 'image',
            Chunk.image_filename == image_filename
        ).first()

        if not image_chunk or not image_chunk.image_s3_key:
            logger.warning(
                "image_not_found",
                document_id=document_id,
                image_filename=image_filename
            )
            raise HTTPException(404, "Image not found")

        # 从S3下载
        try:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            s3_client.download_file(image_chunk.image_s3_key, str(local_path))
            logger.info(
                "image_downloaded_from_s3",
                document_id=document_id,
                image_filename=image_filename
            )
        except Exception as e:
            logger.error(
                "image_download_failed",
                document_id=document_id,
                s3_key=image_chunk.image_s3_key,
                error=str(e)
            )
            raise HTTPException(500, f"Failed to download image: {str(e)}")

    # 3. 判断Content-Type
    ext = image_filename.split('.')[-1].lower()
    content_type_map = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'webp': 'image/webp'
    }
    content_type = content_type_map.get(ext, 'application/octet-stream')

    # 4. 返回图片
    return FileResponse(
        local_path,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"}
    )
