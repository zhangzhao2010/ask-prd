"""
完整的认证和授权功能测试脚本
测试所有用户系统、权限管理、数据隔离功能
"""
import sys
import os
import asyncio
import json
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from app.core.logging import get_logger

logger = get_logger(__name__)

# 测试配置
BASE_URL = "http://localhost:8000/api/v1"
TIMEOUT = 30.0

# 测试数据存储
test_data = {
    "admin_token": None,
    "user1_token": None,
    "user2_token": None,
    "user1_id": None,
    "user2_id": None,
    "kb_private_id": None,  # user1的私有知识库
    "kb_public_id": None,   # user1的公开知识库
    "kb_shared_id": None,   # user1的共享知识库
    "kb_user2_id": None,    # user2的私有知识库
}


class TestRunner:
    """测试运行器"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.total = 0

    async def run_test(self, name: str, test_func):
        """运行单个测试"""
        self.total += 1
        print(f"\n{'='*60}")
        print(f"测试 {self.total}: {name}")
        print(f"{'='*60}")

        try:
            await test_func()
            self.passed += 1
            print(f"✅ 通过")
            return True
        except Exception as e:
            self.failed += 1
            print(f"❌ 失败: {str(e)}")
            logger.error(f"test_failed", test=name, error=str(e), exc_info=True)
            return False

    def print_summary(self):
        """打印测试总结"""
        print(f"\n{'='*60}")
        print(f"测试总结")
        print(f"{'='*60}")
        print(f"总计: {self.total}")
        print(f"✅ 通过: {self.passed}")
        print(f"❌ 失败: {self.failed}")
        print(f"成功率: {self.passed/self.total*100:.1f}%")
        print(f"{'='*60}\n")


# ============ 测试函数 ============

async def test_admin_login():
    """测试1: 管理员登录"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            f"{BASE_URL}/auth/login",
            json={
                "username": "admin",
                "password": "admin123"
            }
        )

        assert response.status_code == 200, f"状态码错误: {response.status_code}"
        data = response.json()

        assert "access_token" in data, "响应中没有access_token"
        assert "user" in data, "响应中没有user"
        assert data["user"]["role"] == "admin", "角色不是admin"

        test_data["admin_token"] = data["access_token"]
        print(f"管理员token: {test_data['admin_token'][:20]}...")
        print(f"管理员信息: {data['user']}")


async def test_create_user1():
    """测试2: 创建普通用户1"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            f"{BASE_URL}/users",
            json={
                "username": "testuser1",
                "password": "password123"
            },
            headers={"Authorization": f"Bearer {test_data['admin_token']}"}
        )

        assert response.status_code == 201, f"状态码错误: {response.status_code}, {response.text}"
        data = response.json()

        assert data["username"] == "testuser1", "用户名不匹配"
        assert data["role"] == "user", "角色应该是user"

        test_data["user1_id"] = data["id"]
        print(f"用户1创建成功: ID={test_data['user1_id']}")


async def test_create_user2():
    """测试3: 创建普通用户2"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            f"{BASE_URL}/users",
            json={
                "username": "testuser2",
                "password": "password456"
            },
            headers={"Authorization": f"Bearer {test_data['admin_token']}"}
        )

        assert response.status_code == 201, f"状态码错误: {response.status_code}"
        data = response.json()

        test_data["user2_id"] = data["id"]
        print(f"用户2创建成功: ID={test_data['user2_id']}")


async def test_user1_login():
    """测试4: 普通用户1登录"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            f"{BASE_URL}/auth/login",
            json={
                "username": "testuser1",
                "password": "password123"
            }
        )

        assert response.status_code == 200, f"状态码错误: {response.status_code}"
        data = response.json()

        test_data["user1_token"] = data["access_token"]
        print(f"用户1 token: {test_data['user1_token'][:20]}...")


async def test_user2_login():
    """测试5: 普通用户2登录"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            f"{BASE_URL}/auth/login",
            json={
                "username": "testuser2",
                "password": "password456"
            }
        )

        assert response.status_code == 200, f"状态码错误: {response.status_code}"
        data = response.json()

        test_data["user2_token"] = data["access_token"]
        print(f"用户2 token: {test_data['user2_token'][:20]}...")


async def test_user1_create_private_kb():
    """测试6: 用户1创建私有知识库"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            f"{BASE_URL}/knowledge-bases",
            json={
                "name": "用户1的私有知识库",
                "description": "这是一个私有知识库"
            },
            headers={"Authorization": f"Bearer {test_data['user1_token']}"}
        )

        assert response.status_code == 201, f"状态码错误: {response.status_code}, {response.text}"
        data = response.json()

        assert data["visibility"] == "private", "默认可见性应该是private"
        assert data["owner_id"] == test_data["user1_id"], "所有者ID不匹配"

        test_data["kb_private_id"] = data["id"]
        print(f"私有知识库创建成功: ID={test_data['kb_private_id']}")


async def test_user1_create_public_kb():
    """测试7: 用户1创建知识库并设为公开"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # 创建知识库
        response = await client.post(
            f"{BASE_URL}/knowledge-bases",
            json={
                "name": "用户1的公开知识库",
                "description": "这是一个公开知识库"
            },
            headers={"Authorization": f"Bearer {test_data['user1_token']}"}
        )

        assert response.status_code == 201, f"状态码错误: {response.status_code}"
        kb_id = response.json()["id"]

        # 修改为公开
        response = await client.put(
            f"{BASE_URL}/knowledge-bases/{kb_id}/visibility",
            json={"visibility": "public"},
            headers={"Authorization": f"Bearer {test_data['user1_token']}"}
        )

        assert response.status_code == 200, f"状态码错误: {response.status_code}"
        data = response.json()
        assert data["visibility"] == "public", "可见性应该是public"

        test_data["kb_public_id"] = kb_id
        print(f"公开知识库创建成功: ID={test_data['kb_public_id']}")


async def test_user1_create_shared_kb():
    """测试8: 用户1创建共享知识库并授权给用户2"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # 创建知识库
        response = await client.post(
            f"{BASE_URL}/knowledge-bases",
            json={
                "name": "用户1的共享知识库",
                "description": "这是一个共享知识库"
            },
            headers={"Authorization": f"Bearer {test_data['user1_token']}"}
        )

        assert response.status_code == 201, f"状态码错误: {response.status_code}"
        kb_id = response.json()["id"]

        # 修改为共享
        response = await client.put(
            f"{BASE_URL}/knowledge-bases/{kb_id}/visibility",
            json={"visibility": "shared"},
            headers={"Authorization": f"Bearer {test_data['user1_token']}"}
        )

        assert response.status_code == 200, f"状态码错误: {response.status_code}"

        # 授予用户2读权限
        response = await client.post(
            f"{BASE_URL}/knowledge-bases/{kb_id}/permissions",
            json={
                "username": "testuser2",
                "permission_type": "read"
            },
            headers={"Authorization": f"Bearer {test_data['user1_token']}"}
        )

        assert response.status_code == 201, f"状态码错误: {response.status_code}, {response.text}"
        data = response.json()
        assert data["permission_type"] == "read", "权限类型应该是read"

        test_data["kb_shared_id"] = kb_id
        print(f"共享知识库创建成功: ID={test_data['kb_shared_id']}")
        print(f"已授予用户2读权限")


async def test_user2_create_kb():
    """测试9: 用户2创建自己的私有知识库"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            f"{BASE_URL}/knowledge-bases",
            json={
                "name": "用户2的私有知识库",
                "description": "这是用户2的私有知识库"
            },
            headers={"Authorization": f"Bearer {test_data['user2_token']}"}
        )

        assert response.status_code == 201, f"状态码错误: {response.status_code}"
        data = response.json()

        test_data["kb_user2_id"] = data["id"]
        print(f"用户2的私有知识库创建成功: ID={test_data['kb_user2_id']}")


async def test_user1_list_kb():
    """测试10: 用户1列出知识库（应该看到自己的3个）"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            f"{BASE_URL}/knowledge-bases",
            headers={"Authorization": f"Bearer {test_data['user1_token']}"}
        )

        assert response.status_code == 200, f"状态码错误: {response.status_code}"
        data = response.json()

        assert data["meta"]["total"] == 3, f"用户1应该看到3个知识库，实际: {data['meta']['total']}"
        print(f"用户1可见知识库数量: {data['meta']['total']}")


async def test_user2_list_kb():
    """测试11: 用户2列出知识库（应该看到：自己的1个 + 公开的1个 + 共享的1个 = 3个）"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            f"{BASE_URL}/knowledge-bases",
            headers={"Authorization": f"Bearer {test_data['user2_token']}"}
        )

        assert response.status_code == 200, f"状态码错误: {response.status_code}"
        data = response.json()

        assert data["meta"]["total"] == 3, f"用户2应该看到3个知识库（自己的+公开的+共享的），实际: {data['meta']['total']}"
        print(f"用户2可见知识库数量: {data['meta']['total']}")


async def test_admin_list_kb():
    """测试12: 管理员列出知识库（应该看到所有4个）"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            f"{BASE_URL}/knowledge-bases",
            headers={"Authorization": f"Bearer {test_data['admin_token']}"}
        )

        assert response.status_code == 200, f"状态码错误: {response.status_code}"
        data = response.json()

        assert data["meta"]["total"] == 4, f"管理员应该看到所有4个知识库，实际: {data['meta']['total']}"
        print(f"管理员可见知识库数量: {data['meta']['total']}")


async def test_user2_access_private_kb_denied():
    """测试13: 用户2访问用户1的私有知识库（应该被拒绝）"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            f"{BASE_URL}/knowledge-bases/{test_data['kb_private_id']}",
            headers={"Authorization": f"Bearer {test_data['user2_token']}"}
        )

        assert response.status_code == 404, f"应该返回404，实际: {response.status_code}"
        print("✓ 用户2无法访问用户1的私有知识库")


async def test_user2_access_public_kb_success():
    """测试14: 用户2访问用户1的公开知识库（应该成功）"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            f"{BASE_URL}/knowledge-bases/{test_data['kb_public_id']}",
            headers={"Authorization": f"Bearer {test_data['user2_token']}"}
        )

        assert response.status_code == 200, f"状态码错误: {response.status_code}"
        print("✓ 用户2可以访问公开知识库")


async def test_user2_access_shared_kb_success():
    """测试15: 用户2访问共享知识库（应该成功，因为有读权限）"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            f"{BASE_URL}/knowledge-bases/{test_data['kb_shared_id']}",
            headers={"Authorization": f"Bearer {test_data['user2_token']}"}
        )

        assert response.status_code == 200, f"状态码错误: {response.status_code}"
        print("✓ 用户2可以访问共享知识库（有读权限）")


async def test_user2_write_public_kb_denied():
    """测试16: 用户2尝试修改公开知识库（应该被拒绝）"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.patch(
            f"{BASE_URL}/knowledge-bases/{test_data['kb_public_id']}",
            json={"name": "试图修改公开知识库"},
            headers={"Authorization": f"Bearer {test_data['user2_token']}"}
        )

        assert response.status_code == 403, f"应该返回403，实际: {response.status_code}"
        print("✓ 用户2无法修改公开知识库（仅有读权限）")


async def test_user1_grant_write_permission():
    """测试17: 用户1授予用户2对共享知识库的写权限"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            f"{BASE_URL}/knowledge-bases/{test_data['kb_shared_id']}/permissions",
            json={
                "username": "testuser2",
                "permission_type": "write"
            },
            headers={"Authorization": f"Bearer {test_data['user1_token']}"}
        )

        # 接受200（更新）或201（创建）作为成功响应
        assert response.status_code in [200, 201], f"状态码错误: {response.status_code}"
        data = response.json()
        assert data["permission_type"] == "write", "权限类型应该更新为write"
        print("✓ 用户2的权限已升级为写权限")


async def test_user2_write_shared_kb_success():
    """测试18: 用户2修改共享知识库（现在应该成功）"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.patch(
            f"{BASE_URL}/knowledge-bases/{test_data['kb_shared_id']}",
            json={"description": "用户2修改了这个描述"},
            headers={"Authorization": f"Bearer {test_data['user2_token']}"}
        )

        assert response.status_code == 200, f"状态码错误: {response.status_code}"
        print("✓ 用户2成功修改了共享知识库（有写权限）")


async def test_user2_delete_kb_denied():
    """测试19: 用户2尝试删除共享知识库（应该被拒绝，只有所有者能删除）"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.delete(
            f"{BASE_URL}/knowledge-bases/{test_data['kb_shared_id']}",
            headers={"Authorization": f"Bearer {test_data['user2_token']}"}
        )

        assert response.status_code == 403, f"应该返回403，实际: {response.status_code}"
        print("✓ 用户2无法删除知识库（只有所有者能删除）")


async def test_user1_list_permissions():
    """测试20: 用户1查看共享知识库的权限列表"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            f"{BASE_URL}/knowledge-bases/{test_data['kb_shared_id']}/permissions",
            headers={"Authorization": f"Bearer {test_data['user1_token']}"}
        )

        assert response.status_code == 200, f"状态码错误: {response.status_code}"
        data = response.json()

        assert len(data["permissions"]) == 1, "应该有1个权限记录"
        assert data["permissions"][0]["username"] == "testuser2", "用户名应该是testuser2"
        assert data["permissions"][0]["permission_type"] == "write", "权限类型应该是write"
        print(f"✓ 权限列表正确: {data['permissions']}")


async def test_user1_revoke_permission():
    """测试21: 用户1撤销用户2的权限"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.delete(
            f"{BASE_URL}/knowledge-bases/{test_data['kb_shared_id']}/permissions/{test_data['user2_id']}",
            headers={"Authorization": f"Bearer {test_data['user1_token']}"}
        )

        assert response.status_code == 204, f"状态码错误: {response.status_code}"
        print("✓ 用户2的权限已撤销")


async def test_user2_access_shared_kb_denied():
    """测试22: 用户2访问共享知识库（权限撤销后应该被拒绝）"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            f"{BASE_URL}/knowledge-bases/{test_data['kb_shared_id']}",
            headers={"Authorization": f"Bearer {test_data['user2_token']}"}
        )

        assert response.status_code == 403, f"应该返回403，实际: {response.status_code}"
        print("✓ 权限撤销后，用户2无法访问共享知识库")


async def test_admin_access_all_kb():
    """测试23: 管理员访问所有知识库（应该全部成功）"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        kb_ids = [
            test_data['kb_private_id'],
            test_data['kb_public_id'],
            test_data['kb_shared_id'],
            test_data['kb_user2_id']
        ]

        for kb_id in kb_ids:
            response = await client.get(
                f"{BASE_URL}/knowledge-bases/{kb_id}",
                headers={"Authorization": f"Bearer {test_data['admin_token']}"}
            )
            assert response.status_code == 200, f"管理员访问 {kb_id} 失败: {response.status_code}"

        print("✓ 管理员可以访问所有知识库")


async def test_no_auth_access_denied():
    """测试24: 未认证访问（应该被拒绝）"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(f"{BASE_URL}/knowledge-bases")

        assert response.status_code == 403, f"应该返回403，实际: {response.status_code}"
        print("✓ 未认证请求被正确拒绝")


async def test_invalid_token_denied():
    """测试25: 无效token访问（应该被拒绝）"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            f"{BASE_URL}/knowledge-bases",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

        assert response.status_code == 401, f"应该返回401，实际: {response.status_code}"
        print("✓ 无效token被正确拒绝")


async def test_admin_delete_user():
    """测试26: 管理员删除用户（级联删除）"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # 删除用户2
        response = await client.delete(
            f"{BASE_URL}/users/{test_data['user2_id']}",
            headers={"Authorization": f"Bearer {test_data['admin_token']}"}
        )

        assert response.status_code == 204, f"状态码错误: {response.status_code}"

        # 验证用户2的知识库也被删除（级联）
        response = await client.get(
            f"{BASE_URL}/knowledge-bases/{test_data['kb_user2_id']}",
            headers={"Authorization": f"Bearer {test_data['admin_token']}"}
        )

        assert response.status_code == 404, "用户2的知识库应该被级联删除"
        print("✓ 用户删除成功，知识库已级联删除")


async def test_user1_delete_own_kb():
    """测试27: 用户1删除自己的知识库"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.delete(
            f"{BASE_URL}/knowledge-bases/{test_data['kb_private_id']}",
            headers={"Authorization": f"Bearer {test_data['user1_token']}"}
        )

        assert response.status_code == 204, f"状态码错误: {response.status_code}"
        print("✓ 用户1成功删除自己的知识库")


# ============ 主函数 ============

async def main():
    """运行所有测试"""
    runner = TestRunner()

    print(f"\n{'='*60}")
    print(f"开始测试认证和授权系统")
    print(f"{'='*60}\n")

    # 认证测试
    await runner.run_test("管理员登录", test_admin_login)
    await runner.run_test("创建普通用户1", test_create_user1)
    await runner.run_test("创建普通用户2", test_create_user2)
    await runner.run_test("普通用户1登录", test_user1_login)
    await runner.run_test("普通用户2登录", test_user2_login)

    # 知识库创建和可见性测试
    await runner.run_test("用户1创建私有知识库", test_user1_create_private_kb)
    await runner.run_test("用户1创建公开知识库", test_user1_create_public_kb)
    await runner.run_test("用户1创建共享知识库并授权", test_user1_create_shared_kb)
    await runner.run_test("用户2创建私有知识库", test_user2_create_kb)

    # 数据隔离测试
    await runner.run_test("用户1列出知识库", test_user1_list_kb)
    await runner.run_test("用户2列出知识库", test_user2_list_kb)
    await runner.run_test("管理员列出所有知识库", test_admin_list_kb)

    # 权限验证测试
    await runner.run_test("用户2访问私有知识库被拒绝", test_user2_access_private_kb_denied)
    await runner.run_test("用户2访问公开知识库成功", test_user2_access_public_kb_success)
    await runner.run_test("用户2访问共享知识库成功", test_user2_access_shared_kb_success)
    await runner.run_test("用户2修改公开知识库被拒绝", test_user2_write_public_kb_denied)

    # 权限管理测试
    await runner.run_test("用户1授予写权限", test_user1_grant_write_permission)
    await runner.run_test("用户2修改共享知识库成功", test_user2_write_shared_kb_success)
    await runner.run_test("用户2删除知识库被拒绝", test_user2_delete_kb_denied)
    await runner.run_test("用户1查看权限列表", test_user1_list_permissions)
    await runner.run_test("用户1撤销用户2权限", test_user1_revoke_permission)
    await runner.run_test("权限撤销后访问被拒绝", test_user2_access_shared_kb_denied)

    # 管理员权限测试
    await runner.run_test("管理员访问所有知识库", test_admin_access_all_kb)

    # 安全测试
    await runner.run_test("未认证访问被拒绝", test_no_auth_access_denied)
    await runner.run_test("无效token被拒绝", test_invalid_token_denied)

    # 删除测试
    await runner.run_test("管理员删除用户（级联）", test_admin_delete_user)
    await runner.run_test("用户1删除自己的知识库", test_user1_delete_own_kb)

    # 打印总结
    runner.print_summary()

    # 返回退出码
    return 0 if runner.failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
