"""
API v1路由聚合
"""
from fastapi import APIRouter, Request
from app.api.v1.auth.routes import router as auth_router
from app.api.v1.users.routes import router as users_router
from app.api.v1.knowledge_bases.routes import router as kb_router
from app.api.v1.documents.routes import router as doc_router
from app.api.v1.sync_tasks.routes import router as sync_router
from app.api.v1.query.routes import router as query_router
from app.api.v1.chunks.routes import router as chunks_router

api_router = APIRouter()

# 挂载认证路由（无需认证）
api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["认证"]
)

# 挂载用户管理路由（仅管理员）
api_router.include_router(
    users_router,
    prefix="/users",
    tags=["用户管理"]
)

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


@api_router.get("/debug/ip", tags=["系统"])
async def get_client_ip(request: Request):
    """
    调试接口：返回访问者的IP地址

    支持多种方式获取真实IP：
    - X-Forwarded-For: 代理服务器传递的原始客户端IP
    - X-Real-IP: Nginx等反向代理传递的真实IP
    - client.host: 直接连接的客户端IP
    """
    # 获取各种可能的IP来源
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    x_real_ip = request.headers.get("X-Real-IP")
    client_host = request.client.host if request.client else None

    # X-Forwarded-For可能包含多个IP，取第一个（最原始的客户端IP）
    forwarded_ip = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else None

    # 优先级：X-Real-IP > X-Forwarded-For第一个 > client.host
    real_ip = x_real_ip or forwarded_ip or client_host

    return {
        "real_ip": real_ip,
        "details": {
            "x_forwarded_for": x_forwarded_for,
            "x_real_ip": x_real_ip,
            "client_host": client_host,
            "all_headers": dict(request.headers)
        }
    }
