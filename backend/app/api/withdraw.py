# -*- coding: utf-8 -*-
"""
网店提现记录管理API
销售端：仅查看自己权限内的网店，可新增、编辑任意提现记录，无删除权限
老板端：查看全部网店及所有提现记录，可新增、编辑、删除任意提现记录
"""
import urllib.parse
from typing import Optional
from datetime import date, datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, Float
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_db
from ..core.security import get_current_active_user, ensure_data_permission
from ..models.models import Shop, ShopWithdrawRecord, OperationLog
from ..schemas.schemas import UserResponse

CST = timezone(timedelta(hours=8))

def to_cst_iso(dt):
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=CST)
    return dt.astimezone(CST).isoformat()

router = APIRouter(prefix="/api/withdraw", tags=["网店提现记录"])


@router.get("/shops")
async def get_withdraw_shops(
    keyword: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user)
):
    from ..models.models import User
    
    query = select(
        Shop.shop_id, 
        Shop.shop_name, 
        Shop.creator,
        User.real_name
    ).join(User, User.username == Shop.creator, isouter=True).where(Shop.status == "normal")

    if current_user.role != "boss":
        query = query.where(Shop.creator == current_user.username)

    if keyword:
        query = query.where(
            Shop.shop_id.like(f"%{keyword}%") | Shop.shop_name.like(f"%{keyword}%") |
            User.real_name.like(f"%{keyword}%")
        )

    query = query.order_by(User.real_name, Shop.shop_id)
    result = await db.execute(query)
    shops = result.all()

    grouped_shops = {}
    for s in shops:
        creator_name = s.real_name or s.creator
        if creator_name not in grouped_shops:
            grouped_shops[creator_name] = []
        grouped_shops[creator_name].append({
            "shop_id": s.shop_id,
            "shop_name": s.shop_name,
            "creator": s.creator
        })

    grouped_list = [
        {"creator": creator, "creator_name": creator, "shops": shops}
        for creator, shops in grouped_shops.items()
    ]

    return {"code": 200, "message": "success", "data": grouped_list}


@router.get("/records")
async def get_withdraw_records(
    shop_id: str = Query(..., description="网店ID"),
    withdraw_date_start: Optional[str] = None,
    withdraw_date_end: Optional[str] = None,
    amount_min: Optional[float] = None,
    amount_max: Optional[float] = None,
    create_operator_name: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user)
):
    if current_user.role != "boss":
        shop_result = await db.execute(
            select(Shop).where(Shop.shop_id == shop_id, Shop.creator == current_user.username)
        )
        if not shop_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="无权限查看此网店")

    query = select(ShopWithdrawRecord).where(ShopWithdrawRecord.shop_id == shop_id)

    if withdraw_date_start:
        query = query.where(ShopWithdrawRecord.withdraw_date >= withdraw_date_start)
    if withdraw_date_end:
        query = query.where(ShopWithdrawRecord.withdraw_date <= withdraw_date_end)
    if amount_min is not None:
        query = query.where(func.cast(ShopWithdrawRecord.withdraw_amount, Float) >= amount_min)
    if amount_max is not None:
        query = query.where(func.cast(ShopWithdrawRecord.withdraw_amount, Float) <= amount_max)
    if create_operator_name:
        query = query.where(ShopWithdrawRecord.create_operator_name.like(f"%{create_operator_name}%"))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(ShopWithdrawRecord.withdraw_date.desc(), ShopWithdrawRecord.create_time.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    records = (await db.execute(query)).scalars().all()

    record_list = []
    total_amount = 0
    for r in records:
        amt = float(r.withdraw_amount)
        total_amount += amt
        record_list.append({
            "id": r.id,
            "shop_id": r.shop_id,
            "withdraw_date": r.withdraw_date,
            "withdraw_amount": amt,
            "remark": r.remark,
            "create_operator_name": r.create_operator_name,
            "create_operator_id": r.create_operator_id,
            "update_operator_name": r.update_operator_name,
            "update_operator_id": r.update_operator_id,
            "create_time": to_cst_iso(r.create_time),
            "update_time": to_cst_iso(r.update_time)
        })

    return {
        "code": 200,
        "message": "success",
        "data": {
            "list": record_list,
            "total": total,
            "total_amount": round(total_amount, 2),
            "page": page,
            "page_size": page_size
        }
    }


@router.post("/records")
async def create_withdraw_record(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user)
):
    ensure_data_permission(current_user, '/account-withdrawal', 'add')
    shop_id = data.get("shop_id")
    withdraw_date = data.get("withdraw_date")
    withdraw_amount = data.get("withdraw_amount")
    remark = data.get("remark", "")

    if not shop_id or not withdraw_date or withdraw_amount is None:
        raise HTTPException(status_code=400, detail="网店ID、提现日期、提现金额为必填项")

    try:
        withdraw_amount_float = float(withdraw_amount)
        if withdraw_amount_float <= 0:
            raise HTTPException(status_code=400, detail="提现金额必须大于0")
        withdraw_amount_str = f"{withdraw_amount_float:.2f}"
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="提现金额格式不正确")

    if current_user.role != "boss":
        shop_result = await db.execute(
            select(Shop).where(Shop.shop_id == shop_id, Shop.creator == current_user.username)
        )
        if not shop_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="无权限为此网店创建记录")

    exists_count = (await db.execute(
        select(func.count(ShopWithdrawRecord.id)).where(
            ShopWithdrawRecord.shop_id == shop_id,
            ShopWithdrawRecord.withdraw_date == withdraw_date
        )
    )).scalar() or 0

    new_record = ShopWithdrawRecord(
        shop_id=shop_id,
        withdraw_date=withdraw_date,
        withdraw_amount=withdraw_amount_str,
        remark=remark,
        create_operator_name=current_user.real_name or current_user.username,
        create_operator_id=current_user.id,
        update_operator_name=current_user.real_name or current_user.username,
        update_operator_id=current_user.id
    )

    db.add(new_record)
    await db.commit()
    await db.refresh(new_record)

    shop_name = (await db.execute(select(Shop.shop_name).where(Shop.shop_id == shop_id))).scalar() or shop_id
    log = OperationLog(
        username=current_user.username,
        operation_type="新增提现记录",
        operation_content=f"网店【{shop_name}】新增提现 ¥{withdraw_amount_float:.2f}"
    )
    db.add(log)
    await db.commit()

    return {"code": 200, "message": "success", "data": {"id": new_record.id, "exists_same_day": exists_count > 0}}


@router.put("/records/{record_id}")
async def update_withdraw_record(
    record_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user)
):
    ensure_data_permission(current_user, '/account-withdrawal', 'edit')
    record = (await db.execute(select(ShopWithdrawRecord).where(ShopWithdrawRecord.id == record_id))).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    if current_user.role != "boss":
        shop_result = await db.execute(
            select(Shop).where(Shop.shop_id == record.shop_id, Shop.creator == current_user.username)
        )
        if not shop_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="无权限编辑此记录")

    if data.get("withdraw_date"):
        record.withdraw_date = data["withdraw_date"]

    if data.get("withdraw_amount") is not None:
        try:
            amt = float(data["withdraw_amount"])
            if amt <= 0:
                raise HTTPException(status_code=400, detail="金额必须大于0")
            record.withdraw_amount = f"{amt:.2f}"
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="金额格式不正确")

    if "remark" in data:
        record.remark = data["remark"]

    record.update_operator_name = current_user.real_name or current_user.username
    record.update_operator_id = current_user.id

    await db.commit()

    shop_name = (await db.execute(select(Shop.shop_name).where(Shop.shop_id == record.shop_id))).scalar() or record.shop_id
    log = OperationLog(
        username=current_user.username,
        operation_type="编辑提现记录",
        operation_content=f"网店【{shop_name}】编辑提现记录"
    )
    db.add(log)
    await db.commit()

    return {"code": 200, "message": "success"}


@router.delete("/records/{record_id}")
async def delete_withdraw_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user)
):
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="只有老板端可以删除")
    ensure_data_permission(current_user, '/account-withdrawal', 'delete')

    record = (await db.execute(select(ShopWithdrawRecord).where(ShopWithdrawRecord.id == record_id))).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    shop_name = (await db.execute(select(Shop.shop_name).where(Shop.shop_id == record.shop_id))).scalar() or record.shop_id
    withdraw_amount = record.withdraw_amount

    await db.delete(record)
    await db.commit()

    log = OperationLog(
        username=current_user.username,
        operation_type="删除提现记录",
        operation_content=f"网店【{shop_name}】删除提现记录 ¥{withdraw_amount}"
    )
    db.add(log)
    await db.commit()

    return {"code": 200, "message": "success"}


@router.get("/records/export")
async def export_withdraw_records(
    shop_id: str = Query(...),
    withdraw_date_start: Optional[str] = None,
    withdraw_date_end: Optional[str] = None,
    amount_min: Optional[float] = None,
    amount_max: Optional[float] = None,
    create_operator_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user)
):
    if current_user.role != "boss":
        shop_result = await db.execute(
            select(Shop).where(Shop.shop_id == shop_id, Shop.creator == current_user.username)
        )
        if not shop_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="无权限导出")

    shop_name = (await db.execute(select(Shop.shop_name).where(Shop.shop_id == shop_id))).scalar() or shop_id

    query = select(ShopWithdrawRecord).where(ShopWithdrawRecord.shop_id == shop_id)

    if withdraw_date_start:
        query = query.where(ShopWithdrawRecord.withdraw_date >= withdraw_date_start)
    if withdraw_date_end:
        query = query.where(ShopWithdrawRecord.withdraw_date <= withdraw_date_end)
    if amount_min is not None:
        query = query.where(func.cast(ShopWithdrawRecord.withdraw_amount, Float) >= amount_min)
    if amount_max is not None:
        query = query.where(func.cast(ShopWithdrawRecord.withdraw_amount, Float) <= amount_max)
    if create_operator_name:
        query = query.where(ShopWithdrawRecord.create_operator_name.like(f"%{create_operator_name}%"))

    query = query.order_by(ShopWithdrawRecord.withdraw_date.desc())
    records = (await db.execute(query)).scalars().all()

    import io
    from openpyxl import Workbook
    from fastapi.responses import StreamingResponse

    wb = Workbook()
    ws = wb.active
    ws.title = "提现记录"
    ws.append(["平台", "网店ID", "提现日期", "提现金额", "备注", "创建人"])

    total = 0
    for r in records:
        amt = float(r.withdraw_amount)
        total += amt
        ws.append([
            shop_name,
            r.shop_id,
            r.withdraw_date or "",
            amt,
            r.remark or "",
            r.create_operator_name
        ])

    ws.append([])
    ws.append(["", "", "", f"合计：¥{total:.2f}", "", ""])

    date_range = f"{withdraw_date_start or ''}_至_{withdraw_date_end or ''}".strip("_至_")
    filename = f"网店【{shop_name}】提现流水_{date_range}.xlsx"

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    encoded_filename = urllib.parse.quote(filename)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={encoded_filename}; filename*=UTF-8''{encoded_filename}"},
    )