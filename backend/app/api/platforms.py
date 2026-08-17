# -*- coding: utf-8 -*-
"""平台管理（基础信息-平台管理）。

权限：仅 boss 角色可查看 / 新增 / 编辑 / 删除（其他角色看不到该菜单）。
平台表存储平台公共 API 配置，**不存放任何 AppKey/Token 等密钥**；
网店(Shop)通过 platform_id 关联本表，platform_id 为 NULL 表示手工录入网店。

platform_code：平台唯一编码（语义化，如 aliexpress / alibaba_icbu），用户填写，不可重复。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from ..core.database import get_db
from ..core.security import require_role
from ..models.models import Platform, Shop
from ..schemas.schemas import PlatformCreate, PlatformUpdate, PlatformResponse

router = APIRouter(prefix="/api/platforms", tags=["平台管理"])


@router.get("/", response_model=List[PlatformResponse])
async def get_platforms(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role(['boss']))
):
    result = await db.execute(select(Platform).order_by(Platform.platform_code))
    return result.scalars().all()


@router.post("/", response_model=PlatformResponse)
async def create_platform(
    data: PlatformCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role(['boss']))
):
    dup_code = await db.execute(select(Platform).where(Platform.platform_code == data.platform_code))
    if dup_code.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="平台编码已存在")
    dup_name = await db.execute(select(Platform).where(Platform.platform_name == data.platform_name))
    if dup_name.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="平台名称已存在")

    plat = Platform(
        platform_code=data.platform_code,
        platform_name=data.platform_name,
        remark=data.remark,
        status=data.status if data.status is not None else 1,
        api_gateway=data.api_gateway,
        api_version=data.api_version,
        api_global_max_qps=data.api_global_max_qps if data.api_global_max_qps is not None else 10,
        top_sign_type=data.top_sign_type,
        top_default_fields=data.top_default_fields,
        rest_auth_header=data.rest_auth_header,
        rest_token_prefix=data.rest_token_prefix,
        webhook_encrypt_type=data.webhook_encrypt_type,
    )
    db.add(plat)
    await db.commit()
    await db.refresh(plat)
    return plat


@router.put("/{platform_code}", response_model=PlatformResponse)
async def update_platform(
    platform_code: str,
    data: PlatformUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role(['boss']))
):
    result = await db.execute(select(Platform).where(Platform.platform_code == platform_code))
    plat = result.scalar_one_or_none()
    if not plat:
        raise HTTPException(status_code=404, detail="平台不存在")

    if data.platform_code is not None and data.platform_code != plat.platform_code:
        dup = await db.execute(select(Platform).where(Platform.platform_code == data.platform_code))
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="平台编码已存在")
        plat.platform_code = data.platform_code
    if data.platform_name is not None and data.platform_name != plat.platform_name:
        dup = await db.execute(select(Platform).where(
            Platform.platform_name == data.platform_name,
            Platform.platform_code != plat.platform_code
        ))
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="平台名称已存在")
        plat.platform_name = data.platform_name

    if data.remark is not None:
        plat.remark = data.remark
    if data.status is not None:
        plat.status = data.status
    if data.api_gateway is not None:
        plat.api_gateway = data.api_gateway
    if data.api_version is not None:
        plat.api_version = data.api_version
    if data.api_global_max_qps is not None:
        plat.api_global_max_qps = data.api_global_max_qps
    if data.top_sign_type is not None:
        plat.top_sign_type = data.top_sign_type
    if data.top_default_fields is not None:
        plat.top_default_fields = data.top_default_fields
    if data.rest_auth_header is not None:
        plat.rest_auth_header = data.rest_auth_header
    if data.rest_token_prefix is not None:
        plat.rest_token_prefix = data.rest_token_prefix
    if data.webhook_encrypt_type is not None:
        plat.webhook_encrypt_type = data.webhook_encrypt_type

    await db.commit()
    await db.refresh(plat)
    return plat


@router.delete("/{platform_code}", status_code=200)
async def delete_platform(
    platform_code: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role(['boss']))
):
    result = await db.execute(select(Platform).where(Platform.platform_code == platform_code))
    plat = result.scalar_one_or_none()
    if not plat:
        raise HTTPException(status_code=404, detail="平台不存在")

    # 已关联网店则禁止删除（避免网店 platform_id 悬空）
    shop_count = (await db.execute(
        select(func.count(Shop.id)).where(Shop.platform_id == plat.id)
    )).scalar() or 0
    if shop_count > 0:
        raise HTTPException(status_code=400, detail="该平台已关联网店，无法删除")

    await db.delete(plat)
    await db.commit()
    return {"message": "平台删除成功"}
