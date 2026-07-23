# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from ..core.database import get_db
from ..core.security import get_current_active_user, require_role
from ..models.models import User, OperationLog
from ..schemas.schemas import UserResponse, UserUpdate

router = APIRouter(prefix="/api/users", tags=["用户管理"])

@router.get("/", response_model=List[UserResponse])
async def get_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role == "boss":
        result = await db.execute(select(User).order_by(User.created_at.desc()))
    else:
        result = await db.execute(
            select(User).where(User.id == current_user.id).order_by(User.created_at.desc())
        )
    users = result.scalars().all()
    return users

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role != "boss" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="您没有权限查看此用户")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role != "boss" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="您没有权限修改此用户")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if current_user.role != "boss":
        if user_data.role is not None or user_data.is_active is not None:
            raise HTTPException(status_code=403, detail="您没有权限修改此字段")

    update_data = user_data.model_dump(exclude_unset=True)
    changes = []
    for field, value in update_data.items():
        old_value = getattr(user, field)
        if old_value != value:
            changes.append(f"{field}: {old_value} -> {value}")
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    if changes:
        log = OperationLog(
            username=current_user.username,
            operation_type="更新用户",
            operation_content=f"更新用户 {user.username}，变更: {', '.join(changes)}"
        )
        db.add(log)
        await db.commit()

    return user

@router.delete("/{user_id}", status_code=200)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("boss"))
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    await db.delete(user)
    await db.commit()

    log = OperationLog(
        username=current_user.username,
        operation_type="删除用户",
        operation_content=f"删除用户 {user.username}"
    )
    db.add(log)
    await db.commit()

    return {"message": "用户删除成功"}
