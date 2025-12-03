"""
数据库初始化脚本
运行此脚本创建数据库表并创建默认管理员账户
"""
import sys
from pathlib import Path

# 添加app目录到Python路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import init_db, engine
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.database import User
from sqlalchemy.orm import Session


def create_default_admin():
    """创建默认管理员账户"""
    with Session(engine) as db:
        # 检查是否已存在admin账户
        existing_admin = db.query(User).filter(User.username == "admin").first()

        if existing_admin:
            print("ℹ️  管理员账户已存在，跳过创建")
            print(f"   用户名: admin")
            print(f"   用户ID: {existing_admin.id}")
            return False

        # 创建新的admin账户
        admin = User(
            username="admin",
            password_hash=get_password_hash("admin123"),
            role="admin",
            is_active=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        print("✅ 默认管理员账户创建成功！")
        print(f"   用户名: admin")
        print(f"   密码: admin123")
        print(f"   用户ID: {admin.id}")
        print()
        print("⚠️  重要提示：请在生产环境中立即修改默认密码！")
        return True


def main():
    """主函数"""
    print("=" * 60)
    print("ASK-PRD 数据库初始化")
    print("=" * 60)
    print(f"数据库路径: {settings.database_path}")
    print(f"Debug模式: {settings.debug}")
    print()

    try:
        # 1. 初始化数据库表
        print("[1/2] 创建数据库表...")
        init_db()
        print("✅ 数据库表创建成功！")
        print()
        print("数据库表:")
        print("  - users            (用户)")
        print("  - knowledge_bases  (知识库)")
        print("  - documents        (文档)")
        print("  - chunks           (文本/图片块)")
        print("  - sync_tasks       (同步任务)")
        print("  - knowledge_base_permissions  (权限)")
        print("  - query_history    (查询历史)")
        print()

        # 2. 创建默认管理员账户
        print("[2/2] 创建默认管理员账户...")
        create_default_admin()
        print()

        print("=" * 60)
        print("✅ 数据库初始化完成！")
        print("=" * 60)
        print()
        print("💡 下一步：")
        print("   cd backend")
        print("   python -m app.main")
        print("   # 访问 http://localhost:8000/docs")
        print("   # 使用 admin/admin123 登录")
        print()

    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
