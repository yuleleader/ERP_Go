# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import List
from ..core.database import get_db
from ..core.security import get_current_active_user, require_role, get_password_hash
from ..models.models import User, OperationLog
from ..schemas.schemas import UserResponse, UserUpdate

router = APIRouter(prefix="/api/users", tags=["用户管理"])

@router.get("/", response_model=List[UserResponse])
async def get_users(
    keyword: str = Query(None, description="按用户名/真实姓名模糊搜索"),
    role: str = Query(None, description="按角色筛选（boss/sales/factory/shipping）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """用户列表：支持关键字（用户名/真实姓名模糊）与角色筛选，二者可组合。"""
    if current_user.role == "boss":
        query = select(User)
    else:
        # 非老板端仅能查看自己
        query = select(User).where(User.id == current_user.id)

    if keyword:
        like = f"%{keyword.strip()}%"
        query = query.where(
            or_(User.username.like(like), User.real_name.like(like))
        )
    if role:
        query = query.where(User.role == role)

    query = query.order_by(User.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()

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

    # 密码单独处理：非空则直接重置（无需原密码），并移除以免 setattr 出错
    new_password = update_data.pop("password", None)
    if new_password:
        user.password_hash = get_password_hash(new_password)
        changes.append("密码已重置")

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

    # 保护：不能删除当前登录账号
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录的账号")

    # 保护：不能删除最后一个老板账号，避免系统无管理员
    if user.role == "boss":
        boss_count = (await db.execute(
            select(func.count(User.id)).where(User.role == "boss", User.is_active == True)
        )).scalar() or 0
        if boss_count <= 1:
            raise HTTPException(status_code=400, detail="不能删除最后一个老板账号，否则系统将无管理员")

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
