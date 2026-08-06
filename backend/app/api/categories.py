# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from ..core.database import get_db
from ..core.security import get_current_active_user
from ..models.models import Category, OperationLog
from ..schemas.schemas import CategoryCreate, CategoryUpdate, CategoryResponse

router = APIRouter(prefix="/api/categories", tags=["类别管理"])


@router.get("/", response_model=List[CategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    result = await db.execute(select(Category).order_by(Category.category_code))
    return result.scalars().all()


@router.post("/", response_model=CategoryResponse)
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="您没有权限创建类别")

    cat = Category(category_name=data.category_name, created_by=current_user.username)
    db.add(cat)
    await db.flush()                 # 先拿到自增 id
    cat.category_code = cat.id       # 三位数字编码 = 自增主键（展示时补零）
    db.add(OperationLog(
        username=current_user.username,
        operation_type="创建类别",
        operation_content=f"创建类别 {data.category_name}"
    ))
    await db.commit()
    await db.refresh(cat)
    return cat


@router.put("/{cat_id}", response_model=CategoryResponse)
async def update_category(
    cat_id: int,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="您没有权限修改类别")

    result = await db.execute(select(Category).where(Category.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="类别不存在")

    if data.category_name is not None:
        cat.category_name = data.category_name

    await db.commit()
    await db.refresh(cat)
    return cat


@router.delete("/{cat_id}", status_code=200)
async def delete_category(
    cat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="您没有权限删除类别")

    result = await db.execute(select(Category).where(Category.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="类别不存在")

    db.add(OperationLog(
        username=current_user.username,
        operation_type="删除类别",
        operation_content=f"删除类别 {cat.category_name}"
    ))
    await db.delete(cat)
    await db.commit()
    return {"message": "类别删除成功"}
