"""
用户管理API路由（仅管理员）
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_password_hash
from app.core.dependencies import require_admin
from app.models.database import User
from app.models.schemas import UserCreate, UserResponse, UserListResponse

router = APIRouter()


@router.get("", response_model=UserListResponse, summary="获取用户列表")
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    获取用户列表（仅管理员）

    Returns:
        UserListResponse: 用户列表
    """
    users = db.query(User).all()
    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=len(users)
    )


@router.post("", response_model=UserResponse, summary="创建普通用户", status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    创建普通用户（仅管理员）

    Args:
        request: 用户创建请求

    Returns:
        UserResponse: 创建的用户信息

    Raises:
        HTTPException: 400 用户名已存在
    """
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # 创建新用户
    new_user = User(
        username=request.username,
        password_hash=get_password_hash(request.password),
        role="user",
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserResponse.model_validate(new_user)


@router.get("/{user_id}", response_model=UserResponse, summary="获取用户详情")
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    获取用户详情（仅管理员）

    Args:
        user_id: 用户ID

    Returns:
        UserResponse: 用户信息

    Raises:
        HTTPException: 404 用户不存在
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除用户")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    删除用户（仅管理员）

    删除用户会级联删除：
    - 用户拥有的知识库（以及关联的文档、chunks等）
    - 用户的查询历史
    - 用户被授予的权限

    Args:
        user_id: 用户ID

    Raises:
        HTTPException: 404 用户不存在
        HTTPException: 400 不能删除管理员
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # 不允许删除管理员
    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete admin user"
        )

    # 删除用户（级联删除关联数据）
    db.delete(user)
    db.commit()

    return None
