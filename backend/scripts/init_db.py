"""
数据库初始化脚本
运行此脚本创建数据库表
"""
import sys
from pathlib import Path

# 添加app目录到Python路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import init_db
from app.core.config import settings


def main():
    """主函数"""
    print("=" * 60)
    print("ASK-PRD 数据库初始化")
    print("=" * 60)
    print(f"数据库路径: {settings.database_path}")
    print(f"Debug模式: {settings.debug}")
    print()

    try:
        init_db()
        print()
        print("✅ 数据库初始化成功！")
        print()
        print("数据库表:")
        print("  - knowledge_bases  (知识库)")
        print("  - documents        (文档)")
        print("  - chunks           (文本/图片块)")
        print("  - sync_tasks       (同步任务)")
        print("=" * 60)
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
