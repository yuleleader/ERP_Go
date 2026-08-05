# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from ..core.database import get_db
from ..core.security import verify_password, get_password_hash, create_access_token, get_current_active_user
from ..models.models import User, LoginLog, OperationLog
from ..schemas.schemas import Token, UserCreate, UserResponse, UserUpdate
from pydantic import BaseModel, Field


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=1)

router = APIRouter(prefix="/api/auth", tags=["认证"])

@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(select(User).where(User.username == form_data.username))
        user = result.scalar_one_or_none()

        if not user or not verify_password(form_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户已被禁用"
            )

        access_token = create_access_token(data={"sub": user.username})
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        # 捕获所有非预期的运行时错误，返回友好的错误信息而非 500
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"登录异常: username={form_data.username}, error={str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录服务暂时不可用，请稍后重试或联系管理员"
        )

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_active_user)):
    return {
        "username": current_user.username,
        "real_name": current_user.real_name,
        "role": current_user.role,
    }


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="只有老板端可以创建账号")

    result = await db.execute(select(User).where(User.username == user_data.username))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")

    if user_data.role == "sales" and not user_data.commission_rate:
        raise HTTPException(status_code=400, detail="销售端账号必须设置提成比例")

    # 校验角色值
    ALLOWED_ROLES = {"boss", "sales", "factory", "shipping"}
    if user_data.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail=f"无效的角色值，允许的角色: {', '.join(sorted(ALLOWED_ROLES))}")

    new_user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        real_name=user_data.real_name,
        role=user_data.role,
        commission_rate=user_data.commission_rate,
        is_active=user_data.is_active
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    log = OperationLog(
        username=current_user.username,
        operation_type="创建账号",
        operation_content=f"创建用户 {user_data.username}，角色: {user_data.role}"
    )
    db.add(log)
    await db.commit()

    return new_user

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    return current_user

@router.put("/password", status_code=200)
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if not verify_password(body.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")

    current_user.password_hash = get_password_hash(body.new_password)
    await db.commit()

    log = OperationLog(
        username=current_user.username,
        operation_type="修改密码",
        operation_content="用户修改了自己的密码"
    )
    db.add(log)
    await db.commit()

    return {"message": "密码修改成功"}

@router.post("/reset-password/{user_id}", status_code=200)
async def reset_user_password(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="只有老板端可以重置密码")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 生成随机强密码（不落日志明文），由接口一次性返回给操作人转交
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits
    new_password = "".join(secrets.choice(alphabet) for _ in range(10))

    user.password_hash = get_password_hash(new_password)
    await db.commit()

    log = OperationLog(
        username=current_user.username,
        operation_type="重置密码",
        operation_content=f"已重置用户 {user.username} 的密码（新密码已返回给操作人，未记录明文）"
    )
    db.add(log)
    await db.commit()

    return {"message": "密码已重置", "new_password": new_password}
