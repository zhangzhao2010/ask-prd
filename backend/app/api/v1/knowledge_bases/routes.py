"""
知识库管理API路由
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.dependencies import get_current_user
from app.core.permissions import check_kb_permission, check_kb_ownership, can_view_kb, PermissionType
from app.models.database import User, KnowledgeBase, KBPermission
from app.models.schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    KnowledgeBaseListResponse,
    KnowledgeBaseDetailResponse,
    KBVisibilityUpdate,
    KBPermissionCreate,
    KBPermissionUpdate,
    KBPermissionResponse,
    KBPermissionListResponse,
    PaginationMeta
)
from app.services.knowledge_base_service import KnowledgeBaseService

logger = get_logger(__name__)
router = APIRouter()


@router.post("", response_model=KnowledgeBaseResponse, status_code=201)
async def create_knowledge_base(
    kb_data: KnowledgeBaseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建知识库（需要登录）

    - 自动创建OpenSearch索引
    - 生成唯一的知识库ID
    - 设置当前用户为所有者
    - 默认可见性为private
    """
    logger.info("api_create_knowledge_base", name=kb_data.name, user_id=current_user.id)

    kb = KnowledgeBaseService.create_knowledge_base(db, kb_data, owner_id=current_user.id)
    return KnowledgeBaseResponse.model_validate(kb)


@router.get("", response_model=KnowledgeBaseListResponse)
async def list_knowledge_bases(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    列出知识库（需要登录，根据权限过滤）

    - 管理员：看到所有知识库
    - 普通用户：看到自己创建的 + public + 被共享的
    - 分页返回
    - 按创建时间倒序
    """
    logger.info("api_list_knowledge_bases", page=page, page_size=page_size, user_id=current_user.id)

    # 根据用户权限过滤知识库
    kbs, total = KnowledgeBaseService.list_knowledge_bases_for_user(db, current_user, page, page_size)

    total_pages = (total + page_size - 1) // page_size

    return KnowledgeBaseListResponse(
        items=[KnowledgeBaseResponse.model_validate(kb) for kb in kbs],
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages
        )
    )


@router.get("/{kb_id}", response_model=KnowledgeBaseDetailResponse)
async def get_knowledge_base(
    kb_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取知识库详情（需要读权限）

    - 包含统计信息（文档数、chunk数、总大小）
    - 检查用户是否有权限查看
    """
    logger.info("api_get_knowledge_base", kb_id=kb_id, user_id=current_user.id)

    # 检查读权限
    kb = check_kb_permission(kb_id, current_user, PermissionType.READ, db)
    stats = KnowledgeBaseService.get_knowledge_base_stats(db, kb_id)

    # 构造详情响应
    kb_dict = {
        **KnowledgeBaseResponse.model_validate(kb).model_dump(),
        "stats": stats
    }

    return KnowledgeBaseDetailResponse(**kb_dict)


@router.patch("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_id: str,
    kb_data: KnowledgeBaseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新知识库（需要写权限）

    - 可更新名称和描述
    - 名称不能与其他知识库重复
    - 需要写权限
    """
    logger.info("api_update_knowledge_base", kb_id=kb_id, user_id=current_user.id)

    # 检查写权限
    check_kb_permission(kb_id, current_user, PermissionType.WRITE, db)

    kb = KnowledgeBaseService.update_knowledge_base(db, kb_id, kb_data)
    return KnowledgeBaseResponse.model_validate(kb)


@router.delete("/{kb_id}", status_code=204)
async def delete_knowledge_base(
    kb_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除知识库（仅所有者和管理员）

    - 软删除数据库记录
    - 真删除OpenSearch索引
    - 级联删除所有关联数据（documents, chunks, tasks, queries）
    """
    logger.info("api_delete_knowledge_base", kb_id=kb_id, user_id=current_user.id)

    # 检查删除权限（仅所有者/管理员）
    check_kb_permission(kb_id, current_user, PermissionType.DELETE, db)

    KnowledgeBaseService.delete_knowledge_base(db, kb_id)
    return None


# ============ 知识库权限管理API ============

@router.put("/{kb_id}/visibility", response_model=KnowledgeBaseResponse, summary="修改知识库可见性")
async def update_kb_visibility(
    kb_id: str,
    visibility_data: KBVisibilityUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    修改知识库可见性（仅所有者和管理员）

    - private: 仅所有者可见
    - public: 所有人可见（只读，除非授予写权限）
    - shared: 指定人可见（通过权限表管理）
    """
    logger.info("api_update_kb_visibility", kb_id=kb_id, visibility=visibility_data.visibility, user_id=current_user.id)

    # 检查所有权
    kb = check_kb_ownership(kb_id, current_user, db)

    # 更新可见性
    kb.visibility = visibility_data.visibility
    db.commit()
    db.refresh(kb)

    return KnowledgeBaseResponse.model_validate(kb)


@router.get("/{kb_id}/permissions", response_model=KBPermissionListResponse, summary="查看知识库权限列表")
async def list_kb_permissions(
    kb_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    查看知识库的共享权限列表（仅所有者和管理员）

    返回被授予权限的用户列表
    """
    logger.info("api_list_kb_permissions", kb_id=kb_id, user_id=current_user.id)

    # 检查所有权
    check_kb_ownership(kb_id, current_user, db)

    # 查询权限列表
    permissions = db.query(KBPermission, User.username).join(
        User, KBPermission.user_id == User.id
    ).filter(
        KBPermission.kb_id == kb_id
    ).all()

    permission_list = [
        KBPermissionResponse(
            id=perm.id,
            kb_id=perm.kb_id,
            user_id=perm.user_id,
            username=username,
            permission_type=perm.permission_type,
            granted_by=perm.granted_by,
            created_at=perm.created_at
        )
        for perm, username in permissions
    ]

    return KBPermissionListResponse(permissions=permission_list)


@router.post("/{kb_id}/permissions", response_model=KBPermissionResponse, status_code=201, summary="添加知识库权限")
async def add_kb_permission(
    kb_id: str,
    perm_data: KBPermissionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    添加知识库共享权限（仅所有者和管理员）

    - 通过用户名指定用户
    - 权限类型：read（只读）或 write（管理）
    - 不能给所有者添加权限
    """
    logger.info("api_add_kb_permission", kb_id=kb_id, username=perm_data.username, user_id=current_user.id)

    # 检查所有权
    kb = check_kb_ownership(kb_id, current_user, db)

    # 查找目标用户
    target_user = db.query(User).filter(User.username == perm_data.username).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # 不能给所有者添加权限
    if target_user.id == kb.owner_id:
        raise HTTPException(status_code=400, detail="Cannot grant permission to owner")

    # 检查是否已存在权限
    existing = db.query(KBPermission).filter(
        KBPermission.kb_id == kb_id,
        KBPermission.user_id == target_user.id
    ).first()

    if existing:
        # 更新权限类型
        existing.permission_type = perm_data.permission_type
        db.commit()
        db.refresh(existing)
        return KBPermissionResponse(
            id=existing.id,
            kb_id=existing.kb_id,
            user_id=existing.user_id,
            username=target_user.username,
            permission_type=existing.permission_type,
            granted_by=existing.granted_by,
            created_at=existing.created_at
        )

    # 创建新权限
    new_perm = KBPermission(
        kb_id=kb_id,
        user_id=target_user.id,
        permission_type=perm_data.permission_type,
        granted_by=current_user.id
    )
    db.add(new_perm)
    db.commit()
    db.refresh(new_perm)

    return KBPermissionResponse(
        id=new_perm.id,
        kb_id=new_perm.kb_id,
        user_id=new_perm.user_id,
        username=target_user.username,
        permission_type=new_perm.permission_type,
        granted_by=new_perm.granted_by,
        created_at=new_perm.created_at
    )


@router.delete("/{kb_id}/permissions/{user_id}", status_code=204, summary="移除知识库权限")
async def remove_kb_permission(
    kb_id: str,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    移除知识库共享权限（仅所有者和管理员）

    删除指定用户的访问权限
    """
    logger.info("api_remove_kb_permission", kb_id=kb_id, target_user_id=user_id, user_id=current_user.id)

    # 检查所有权
    check_kb_ownership(kb_id, current_user, db)

    # 删除权限
    perm = db.query(KBPermission).filter(
        KBPermission.kb_id == kb_id,
        KBPermission.user_id == user_id
    ).first()

    if perm:
        db.delete(perm)
        db.commit()

    return None
