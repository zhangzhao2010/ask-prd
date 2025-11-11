"""
添加用户系统和知识库权限共享的数据库迁移脚本
警告：此脚本会删除所有现有数据！
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine
from app.models.database import Base, User
from sqlalchemy.orm import Session


def migrate(skip_confirm=False):
    """执行数据库迁移"""
    print("=" * 60)
    print("数据库迁移：添加用户系统和权限管理")
    print("=" * 60)
    print("\n⚠️  警告：此操作将删除所有现有数据！")
    print("包括：知识库、文档、chunks、同步任务、查询历史等\n")

    if not skip_confirm:
        confirm = input("请输入 'yes' 确认继续: ")
        if confirm != "yes":
            print("❌ 取消迁移")
            return

    print("\n开始迁移...")

    # 1. 删除所有表
    print("\n[1/3] 删除所有表...")
    Base.metadata.drop_all(bind=engine)
    print("✅ 所有表已删除")

    # 2. 重新创建表（包含新的users、knowledge_base_permissions、query_history表）
    print("\n[2/3] 创建新表...")
    Base.metadata.create_all(bind=engine)
    print("✅ 新表创建成功")
    print("   - users（用户表）")
    print("   - knowledge_bases（添加owner_id、visibility字段）")
    print("   - knowledge_base_permissions（权限表）")
    print("   - query_history（查询历史表）")
    print("   - documents、chunks、sync_tasks（保持不变）")

    # 3. 创建默认管理员账户
    print("\n[3/3] 创建默认管理员账户...")

    # 导入密码哈希函数
    from app.core.security import get_password_hash

    with Session(engine) as db:
        admin = User(
            username="admin",
            password_hash=get_password_hash("admin123"),
            role="admin",
            is_active=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"✅ 管理员创建成功！")
        print(f"   用户名: admin")
        print(f"   密码: admin123")
        print(f"   用户ID: {admin.id}")

    print("\n" + "=" * 60)
    print("✅ 迁移完成！")
    print("=" * 60)
    print("\n📌 重要提示：")
    print("1. 请立即登录系统修改默认管理员密码")
    print("2. 所有旧数据已清空，请重新上传文档")
    print("3. 现在可以使用 admin/admin123 登录系统")
    print("\n💡 下一步：")
    print("   cd backend")
    print("   python -m app.main")
    print("   # 然后访问 http://localhost:8000/docs 测试API\n")


if __name__ == "__main__":
    try:
        # 支持 --yes 参数跳过确认
        skip_confirm = len(sys.argv) > 1 and sys.argv[1] == "--yes"
        migrate(skip_confirm=skip_confirm)
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
