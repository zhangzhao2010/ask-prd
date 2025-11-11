"""
权限检查逻辑
包括知识库可见性和权限验证
"""
from enum import Enum
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.database import KnowledgeBase, KBPermission, User


class KBVisibility(str, Enum):
    """知识库可见性枚举"""
    PRIVATE = "private"  # 仅所有者可见
    PUBLIC = "public"    # 所有人可见
    SHARED = "shared"    # 指定人可见


class PermissionType(str, Enum):
    """权限类型枚举"""
    READ = "read"      # 只读权限（查看文档、问答）
    WRITE = "write"    # 管理权限（上传/删除文档、只读权限）
    DELETE = "delete"  # 删除权限（仅所有者，用于检查删除KB和管理权限的操作）


def check_kb_permission(
    kb_id: str,
    user: User,
    required_permission: PermissionType,
    db: Session
) -> KnowledgeBase:
    """
    检查用户对知识库的权限

    权限规则：
    1. 管理员拥有所有权限
    2. 所有者拥有所有权限
    3. 删除权限：仅所有者（管理员除外）
    4. private：仅所有者可见
    5. public：所有人只读，除非明确授予write权限
    6. shared：根据权限表检查

    Args:
        kb_id: 知识库ID
        user: 当前用户
        required_permission: 需要的权限（read/write/delete）
        db: 数据库会话

    Returns:
        KnowledgeBase: 知识库对象（如果有权限）

    Raises:
        HTTPException: 403/404（无权限或不存在）
    """
    # 查询知识库
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found"
        )

    # 1. 管理员拥有所有权限
    if user.role == "admin":
        return kb

    # 2. 所有者拥有所有权限
    if kb.owner_id == user.id:
        return kb

    # 3. 删除权限：仅所有者（管理员已在步骤1返回）
    if required_permission == PermissionType.DELETE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can perform this operation"
        )

    # 4. 检查知识库可见性
    if kb.visibility == KBVisibility.PRIVATE:
        # 私有知识库：仅所有者和管理员可见
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found"
        )

    elif kb.visibility == KBVisibility.PUBLIC:
        # 公开知识库：所有人只读
        if required_permission == PermissionType.READ:
            return kb
        else:  # WRITE权限
            # 检查是否有明确授予的写权限
            perm = db.query(KBPermission).filter(
                KBPermission.kb_id == kb_id,
                KBPermission.user_id == user.id
            ).first()
            if perm and perm.permission_type == "write":
                return kb
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Write permission required"
            )

    elif kb.visibility == KBVisibility.SHARED:
        # 共享知识库：检查权限表
        perm = db.query(KBPermission).filter(
            KBPermission.kb_id == kb_id,
            KBPermission.user_id == user.id
        ).first()
        if not perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        # 检查权限类型
        if required_permission == PermissionType.READ:
            return kb  # read或write权限都可以读
        elif required_permission == PermissionType.WRITE:
            if perm.permission_type == "write":
                return kb
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Write permission required"
            )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied"
    )


def check_kb_ownership(kb_id: str, user: User, db: Session) -> KnowledgeBase:
    """
    检查用户是否是知识库所有者或管理员
    用于修改可见性、管理权限等仅所有者可操作的场景

    Args:
        kb_id: 知识库ID
        user: 当前用户
        db: 数据库会话

    Returns:
        KnowledgeBase: 知识库对象

    Raises:
        HTTPException: 403/404（非所有者或不存在）
    """
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found"
        )

    # 管理员或所有者
    if user.role == "admin" or kb.owner_id == user.id:
        return kb

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only the owner can perform this operation"
    )


def can_view_kb(kb: KnowledgeBase, user: User, db: Session) -> bool:
    """
    判断用户是否可以看到知识库（用于列表过滤）

    Args:
        kb: 知识库对象
        user: 当前用户
        db: 数据库会话

    Returns:
        bool: 是否可见
    """
    # 管理员可以看到所有
    if user.role == "admin":
        return True

    # 所有者可以看到自己的
    if kb.owner_id == user.id:
        return True

    # public知识库所有人可见
    if kb.visibility == KBVisibility.PUBLIC:
        return True

    # shared知识库需要检查权限表
    if kb.visibility == KBVisibility.SHARED:
        perm = db.query(KBPermission).filter(
            KBPermission.kb_id == kb.id,
            KBPermission.user_id == user.id
        ).first()
        return perm is not None

    # private知识库仅所有者可见
    return False
