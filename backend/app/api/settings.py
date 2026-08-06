# -*- coding: utf-8 -*-
"""
系统参数 API
提供系统参数的读取与更新（持久化到 system_settings 表）。

默认参数在 DEFAULT_SETTINGS 中定义；GET 时若库中无对应记录则回填默认值，
保证前端始终能拿到一个完整、可用的参数集合。
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from ..core.database import get_db
from ..core.security import get_current_active_user
from ..models.models import SystemSetting

router = APIRouter(prefix="/api/settings", tags=["系统参数"])

DEFAULT_SETTINGS = {
    "default_commission_rate": {"value": "10", "description": "默认提成比例(%)"},
    "temp_image_retention_hours": {"value": "24", "description": "临时图片保留时间(小时)"},
    "overdue_order_days": {"value": "7", "description": "超期订单天数：下单超过该天数未完成的订单视为超期"},
}


async def read_setting(db: AsyncSession, key: str, default: Optional[str] = None) -> Optional[str]:
    """读取单个系统参数值（库内不存在返回 default）"""
    row = (await db.execute(
        select(SystemSetting).where(SystemSetting.key == key)
    )).scalar_one_or_none()
    if row is None:
        return default
    return row.value


class SettingItem(BaseModel):
    key: str
    value: str
    description: Optional[str] = None


class SettingsUpdate(BaseModel):
    items: list[SettingItem]


@router.get("")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """获取全部系统参数（缺失项用默认值补齐）"""
    rows = (await db.execute(select(SystemSetting))).scalars().all()
    store = {r.key: r for r in rows}

    result = {}
    for key, meta in DEFAULT_SETTINGS.items():
        if key in store:
            result[key] = store[key].value
        else:
            result[key] = meta["value"]
    # 库里存在但不在默认值表中的参数也一并返回
    for r in rows:
        if r.key not in result:
            result[r.key] = r.value
    return result


@router.post("")
async def update_settings(
    payload: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """批量更新系统参数（仅老板端）"""
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="权限不足，仅老板端可修改系统参数")

    for item in payload.items:
        row = (await db.execute(
            select(SystemSetting).where(SystemSetting.key == item.key)
        )).scalar_one_or_none()
        if row is None:
            row = SystemSetting(key=item.key, value=item.value, description=item.description)
            db.add(row)
        else:
            row.value = item.value
            if item.description is not None:
                row.description = item.description
    await db.commit()

    # 返回更新后的全部参数
    return await get_settings(db, current_user)
