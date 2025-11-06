"""
FastAPI主应用
ASK-PRD API服务
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.database import init_db
from app.core.errors import ASKPRDException
from app.api.v1 import api_router

# 设置日志
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("app_starting", version="1.0.0", debug=settings.debug)

    # 初始化数据库
    try:
        init_db()
        logger.info("database_initialized", path=settings.database_path)
    except Exception as e:
        logger.error("database_init_failed", error=str(e))
        raise

    yield

    # 关闭时执行
    logger.info("app_shutdown")


# 创建FastAPI应用
app = FastAPI(
    title="ASK-PRD API",
    description="基于PRD的智能检索问答系统",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)


# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],  # 生产环境需要配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 异常处理器
@app.exception_handler(ASKPRDException)
async def ask_prd_exception_handler(request: Request, exc: ASKPRDException):
    """处理自定义异常"""
    logger.error(
        "api_error",
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        path=request.url.path,
        method=request.method,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """处理未捕获的异常"""
    logger.error(
        "unhandled_error",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "9999",
            "message": "服务器内部错误",
            "details": {"error": str(exc)} if settings.debug else {},
        },
    )


# 健康检查
@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "debug": settings.debug,
    }


# 根路径
@app.get("/", tags=["系统"])
async def root():
    """根路径"""
    return {
        "name": "ASK-PRD API",
        "version": "1.0.0",
        "docs": "/docs" if settings.debug else "disabled",
    }


# 挂载API路由
app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
