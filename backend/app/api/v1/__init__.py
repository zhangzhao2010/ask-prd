"""
API v1路由聚合
"""
from fastapi import APIRouter
from app.api.v1.knowledge_bases.routes import router as kb_router
from app.api.v1.documents.routes import router as doc_router
from app.api.v1.sync_tasks.routes import router as sync_router
from app.api.v1.query.routes import router as query_router
from app.api.v1.chunks.routes import router as chunks_router

api_router = APIRouter()

# 挂载知识库路由
api_router.include_router(
    kb_router,
    prefix="/knowledge-bases",
    tags=["知识库管理"]
)

# 挂载文档路由
api_router.include_router(
    doc_router,
    prefix="/documents",
    tags=["文档管理"]
)

# 挂载同步任务路由
api_router.include_router(
    sync_router,
    prefix="/sync-tasks",
    tags=["同步任务"]
)

# 挂载查询路由
api_router.include_router(
    query_router,
    prefix="/query",
    tags=["智能问答"]
)

# 挂载chunks工具路由
api_router.include_router(
    chunks_router,
    prefix="/chunks",
    tags=["工具接口"]
)


@api_router.get("/", tags=["系统"])
async def api_root():
    """API根路径"""
    return {
        "message": "ASK-PRD API v1",
        "version": "1.0.0",
        "endpoints": {
            "knowledge_bases": "/api/v1/knowledge-bases",
            "documents": "/api/v1/documents",
            "sync_tasks": "/api/v1/sync-tasks",
            "query": "/api/v1/query",
        }
    }
