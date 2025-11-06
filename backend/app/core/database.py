"""
数据库连接和会话管理
"""
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from app.core.config import settings
from app.models.database import Base


# 创建数据库引擎
# 使用SQLite的WAL模式提升并发性能
engine = create_engine(
    settings.database_url,
    connect_args={
        "check_same_thread": False,  # 允许多线程
        "timeout": 30.0,  # 锁超时30秒
    },
    poolclass=StaticPool,  # SQLite使用StaticPool
    echo=settings.debug,  # debug模式下打印SQL
)


# 启用WAL模式和其他性能优化
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """设置SQLite性能优化参数"""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")  # 启用WAL
    cursor.execute("PRAGMA synchronous=NORMAL")  # 平衡性能和安全
    cursor.execute("PRAGMA cache_size=-64000")  # 64MB缓存
    cursor.execute("PRAGMA temp_store=MEMORY")  # 临时表在内存
    cursor.execute("PRAGMA mmap_size=268435456")  # 256MB内存映射
    cursor.execute("PRAGMA foreign_keys=ON")  # 启用外键约束
    cursor.close()


# 创建Session工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """初始化数据库，创建所有表"""
    # 确保数据目录存在
    db_dir = os.path.dirname(settings.database_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    # 创建所有表
    Base.metadata.create_all(bind=engine)
    print(f"✅ 数据库初始化完成: {settings.database_path}")


def get_db() -> Session:
    """
    获取数据库会话
    用于FastAPI依赖注入
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
