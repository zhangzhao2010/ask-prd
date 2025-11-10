"""
数据库迁移脚本：删除query_history表

完全移除查询历史功能，删除整个query_history表及其索引
"""
import sys
import sqlite3
from pathlib import Path

# 添加app目录到Python路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings


def drop_query_history_table(db_path: str):
    """
    删除query_history表及其索引

    Args:
        db_path: 数据库文件路径
    """
    print(f"连接数据库: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='query_history'
        """)
        if not cursor.fetchone():
            print("✅ query_history表不存在，无需删除")
            return

        print("开始删除query_history表...")

        # 2. 删除相关索引（如果存在）
        indexes = [
            'idx_query_history_kb_id',
            'idx_query_history_created',
            'idx_query_history_status'
        ]

        for index_name in indexes:
            try:
                cursor.execute(f"DROP INDEX IF EXISTS {index_name}")
                print(f"✓ 删除索引: {index_name}")
            except Exception as e:
                print(f"⚠️  删除索引失败 {index_name}: {e}")

        # 3. 删除表
        cursor.execute("DROP TABLE IF EXISTS query_history")
        print("✓ 删除表: query_history")

        # 4. 提交事务
        conn.commit()
        print("✅ 删除成功！")

        # 5. 验证表已删除
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='query_history'
        """)
        if cursor.fetchone():
            print("❌ 警告: 表仍然存在")
        else:
            print("✓ 验证: query_history表已成功删除")

    except Exception as e:
        conn.rollback()
        print(f"❌ 删除失败: {e}")
        raise
    finally:
        conn.close()


def main():
    """主函数"""
    print("=" * 60)
    print("数据库迁移：删除query_history表")
    print("=" * 60)
    print()
    print("此操作将:")
    print("  1. 删除所有查询历史数据")
    print("  2. 删除query_history表")
    print("  3. 删除相关索引")
    print()

    db_path = settings.database_path

    if not Path(db_path).exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        print("请先运行 init_db.py 初始化数据库")
        sys.exit(1)

    # 备份提示
    print(f"⚠️  请确保已备份数据库文件:")
    print(f"   {db_path}")
    print()

    response = input("是否继续删除query_history表? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("取消删除")
        sys.exit(0)

    print()

    try:
        drop_query_history_table(db_path)
        print()
        print("=" * 60)
        print("✅ 迁移完成！")
        print("=" * 60)
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ 迁移失败: {e}")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
