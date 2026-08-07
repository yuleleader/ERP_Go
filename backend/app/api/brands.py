# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from ..core.database import get_db
from ..core.security import get_current_active_user, ensure_data_permission
from ..models.models import Brand, Product, OperationLog
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
    ensure_data_permission(current_user, 'brand', 'add')

    # 三位数字编码自增（=当前最大编码 +1），在构造时即赋值以满足 NOT NULL 约束
    result = await db.execute(select(func.max(Brand.brand_code)))
    max_code = result.scalar() or 0
    next_code = max_code + 1

    brand = Brand(brand_code=next_code, brand_name=data.brand_name, created_by=current_user.username)
    db.add(brand)
    db.add(OperationLog(
        username=current_user.username,
        operation_type="创建品牌",
        operation_content=f"创建品牌 {next_code} {data.brand_name}"
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
    ensure_data_permission(current_user, 'brand', 'edit')

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
    ensure_data_permission(current_user, 'brand', 'delete')

    result = await db.execute(select(Brand).where(Brand.id == brand_id))
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="品牌不存在")

    # 检查是否有商品引用该品牌，防止产生孤儿数据
    product_ref = await db.execute(select(Product.id).where(Product.brand_id == brand_id).limit(1))
    if product_ref.scalars().first():
        raise HTTPException(status_code=400, detail="该品牌下存在关联商品，无法删除。请先移除或转移商品")

    db.add(OperationLog(
        username=current_user.username,
        operation_type="删除品牌",
        operation_content=f"删除品牌 {brand.brand_name}"
    ))
    await db.delete(brand)
    await db.commit()
    return {"message": "品牌删除成功"}
