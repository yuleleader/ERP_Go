# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from ..core.database import get_db
from ..core.security import get_current_active_user
from ..models.models import Brand, OperationLog
from ..schemas.schemas import BrandCreate, BrandUpdate, BrandResponse

router = APIRouter(prefix="/api/brands", tags=["品牌管理"])


@router.get("/", response_model=List[BrandResponse])
async def list_brands(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    result = await db.execute(select(Brand).order_by(Brand.brand_code))
    return result.scalars().all()


@router.post("/", response_model=BrandResponse)
async def create_brand(
    data: BrandCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="您没有权限创建品牌")

    brand = Brand(brand_name=data.brand_name, created_by=current_user.username)
    db.add(brand)
    await db.flush()                 # 先拿到自增 id
    brand.brand_code = brand.id      # 三位数字编码 = 自增主键（展示时补零）
    db.add(OperationLog(
        username=current_user.username,
        operation_type="创建品牌",
        operation_content=f"创建品牌 {data.brand_name}"
    ))
    await db.commit()
    await db.refresh(brand)
    return brand


@router.put("/{brand_id}", response_model=BrandResponse)
async def update_brand(
    brand_id: int,
    data: BrandUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="您没有权限修改品牌")

    result = await db.execute(select(Brand).where(Brand.id == brand_id))
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="品牌不存在")

    if data.brand_name is not None:
        brand.brand_name = data.brand_name

    await db.commit()
    await db.refresh(brand)
    return brand


@router.delete("/{brand_id}", status_code=200)
async def delete_brand(
    brand_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="您没有权限删除品牌")

    result = await db.execute(select(Brand).where(Brand.id == brand_id))
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="品牌不存在")

    db.add(OperationLog(
        username=current_user.username,
        operation_type="删除品牌",
        operation_content=f"删除品牌 {brand.brand_name}"
    ))
    await db.delete(brand)
    await db.commit()
    return {"message": "品牌删除成功"}
