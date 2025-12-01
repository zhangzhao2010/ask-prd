#!/usr/bin/env python3
"""
数据库迁移脚本：删除 knowledge_bases 表的 local_storage_path 字段

运行方式:
    python scripts/migrate_remove_local_storage_path.py
"""
import sqlite3
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def migrate_database():
    """执行数据库迁移"""
    db_path = settings.database_path

    logger.info("starting_migration", db_path=db_path)

    # 检查数据库文件是否存在
    if not Path(db_path).exists():
        logger.error("database_not_found", db_path=db_path)
        print(f"❌ 数据库文件不存在: {db_path}")
        return False

    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. 检查字段是否存在
        cursor.execute("PRAGMA table_info(knowledge_bases)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        logger.info("current_columns", columns=column_names)

        if "local_storage_path" not in column_names:
            logger.info("column_already_removed")
            print("✅ local_storage_path 字段已经不存在，无需迁移")
            return True

        print(f"📋 当前 knowledge_bases 表的字段: {column_names}")
        print(f"🔧 准备删除 local_storage_path 字段...")

        # 2. SQLite不支持直接删除字段，需要重建表
        # 步骤：
        # a. 创建新表（不包含 local_storage_path）
        # b. 复制数据
        # c. 删除旧表
        # d. 重命名新表

        # a. 创建新表
        cursor.execute("""
            CREATE TABLE knowledge_bases_new (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                opensearch_collection_id TEXT,
                opensearch_index_name TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                owner_id INTEGER NOT NULL,
                visibility TEXT NOT NULL DEFAULT 'private',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        logger.info("new_table_created")
        print("✅ 创建新表 knowledge_bases_new")

        # b. 复制数据（排除 local_storage_path）
        cursor.execute("""
            INSERT INTO knowledge_bases_new
            (id, name, description, opensearch_collection_id, opensearch_index_name,
             status, owner_id, visibility, created_at, updated_at)
            SELECT id, name, description, opensearch_collection_id, opensearch_index_name,
                   status, owner_id, visibility, created_at, updated_at
            FROM knowledge_bases
        """)
        rows_copied = cursor.rowcount
        logger.info("data_copied", rows=rows_copied)
        print(f"✅ 复制数据: {rows_copied} 行")

        # c. 删除旧表
        cursor.execute("DROP TABLE knowledge_bases")
        logger.info("old_table_dropped")
        print("✅ 删除旧表 knowledge_bases")

        # d. 重命名新表
        cursor.execute("ALTER TABLE knowledge_bases_new RENAME TO knowledge_bases")
        logger.info("table_renamed")
        print("✅ 重命名新表为 knowledge_bases")

        # e. 重建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_status ON knowledge_bases(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_owner_id ON knowledge_bases(owner_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_visibility ON knowledge_bases(visibility)")
        logger.info("indexes_recreated")
        print("✅ 重建索引")

        # 提交事务
        conn.commit()

        # 验证迁移结果
        cursor.execute("PRAGMA table_info(knowledge_bases)")
        new_columns = cursor.fetchall()
        new_column_names = [col[1] for col in new_columns]

        logger.info("migration_completed", new_columns=new_column_names)
        print(f"\n✅ 迁移完成！")
        print(f"📋 新的字段列表: {new_column_names}")

        if "local_storage_path" in new_column_names:
            logger.error("migration_failed_column_still_exists")
            print("❌ 错误：local_storage_path 字段仍然存在")
            return False

        return True

    except Exception as e:
        logger.error("migration_failed", error=str(e), exc_info=True)
        print(f"❌ 迁移失败: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("数据库迁移：删除 knowledge_bases.local_storage_path 字段")
    print("=" * 60)
    print()

    success = migrate_database()

    if success:
        print("\n🎉 迁移成功完成！")
        sys.exit(0)
    else:
        print("\n❌ 迁移失败，请查看日志")
        sys.exit(1)
