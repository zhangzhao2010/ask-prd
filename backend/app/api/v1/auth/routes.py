"""
认证API路由
包括登录和获取当前用户信息
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_password_hash
from app.core.dependencies import get_current_user
from app.models.database import User
from app.models.schemas import LoginRequest, LoginResponse, UserResponse, ChangePasswordRequest

router = APIRouter()


@router.post("/login", response_model=LoginResponse, summary="用户登录")
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    用户登录

    Args:
        request: 登录请求（用户名+密码）
        db: 数据库会话

    Returns:
        LoginResponse: 包含JWT Token和用户信息

    Raises:
        HTTPException: 401 用户名或密码错误
    """
    # 查询用户
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    # 验证密码
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    # 检查用户是否激活
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )

    # 创建JWT Token
    access_token = create_access_token(data={"sub": user.id})

    # 返回响应
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
async def get_me(current_user: User = Depends(get_current_user)):
    """
    获取当前登录用户信息

    Args:
        current_user: 当前用户（从JWT Token解析）

    Returns:
        UserResponse: 用户信息
    """
    return UserResponse.model_validate(current_user)


@router.put("/change-password", summary="修改密码")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    修改当前用户密码

    Args:
        request: 修改密码请求（旧密码+新密码）
        current_user: 当前用户（从JWT Token解析）
        db: 数据库会话

    Returns:
        成功消息

    Raises:
        HTTPException: 401 旧密码错误
    """
    # 验证旧密码
    if not verify_password(request.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="旧密码错误"
        )

    # 更新密码
    current_user.password_hash = get_password_hash(request.new_password)
    db.commit()

    return {"message": "密码修改成功"}
