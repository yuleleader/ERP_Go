# -*- coding: utf-8 -*-
"""财务模块-非交易收支：账务代码字典 + 收支流水 + 统计报表。

- 账务代码（accounting_codes）：非交易收入(income)/非交易支出(expense)类型字典，老板端维护。
  代码自动生成：收入 SR001、支出 ZC001（按类型递增）。
- 非交易收支流水（non_trade_transactions）：每人录入自己的数据（账务代码 + 关联自己创建的网店(可选)
  + 收入/支出 + 金额 + 备注）；销售只能看/改/删自己的，老板可看全部并可代管。
- 统计报表：仅老板端，按账务代码维度 + 按人员维度汇总收入/支出。
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, case, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.security import get_current_active_user
from ..models.models import AccountingCode, NonTradeTransaction, Shop, User, OperationLog

router = APIRouter(tags=["非交易收支"])


# ==================== Schema ====================
class AccountingCodeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code_type: str = "expense"  # income / expense
    remark: str = ""


class AccountingCodeUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code_type: str = "expense"
    remark: str = ""


class NonTradeCreate(BaseModel):
    code_id: int
    shop_id: str = ""
    trans_type: str = "expense"  # income / expense
    amount: float = Field(..., gt=0, description="金额必须大于0")
    remark: str = ""


class NonTradeUpdate(BaseModel):
    code_id: int
    shop_id: str = ""
    trans_type: str = "expense"
    amount: float = Field(..., gt=0, description="金额必须大于0")
    remark: str = ""


# ==================== 工具 ====================
def _check_boss(current_user):
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="权限不足，仅老板端可操作")


def _check_perm(current_user):
    if current_user.role not in ("boss", "sales"):
        raise HTTPException(status_code=403, detail="权限不足，仅老板端/销售端可使用")


async def _gen_code(db: AsyncSession, code_type: str) -> str:
    """生成账务代码：income → SR{3位递增}，expense → ZC{3位递增}"""
    prefix = "SR" if code_type == "income" else "ZC"
    result = await db.execute(
        select(func.max(AccountingCode.code)).where(AccountingCode.code.like(f"{prefix}%"))
    )
    max_code = result.scalar()
    seq = 1
    if max_code:
        try:
            seq = int(str(max_code)[2:]) + 1
        except ValueError:
            seq = 1
    return f"{prefix}{seq:03d}"


async def _code_map(db: AsyncSession):
    codes = (await db.execute(select(AccountingCode))).scalars().all()
    return {c.id: c for c in codes}


def _code_to_dict(c: AccountingCode) -> dict:
    return {
        "id": c.id,
        "code": c.code,
        "name": c.name,
        "code_type": c.code_type,
        "code_type_text": "非交易收入" if c.code_type == "income" else "非交易支出",
        "remark": c.remark or "",
        "created_by": c.created_by or "",
        "created_at": c.created_at.strftime("%Y-%m-%d %H:%M:%S") if c.created_at else None,
    }


async def _tx_to_dict(db: AsyncSession, t: NonTradeTransaction, codes=None, shops=None, users=None) -> dict:
    codes = codes if codes is not None else await _code_map(db)
    code = codes.get(t.code_id)
    return {
        "id": t.id,
        "code_id": t.code_id,
        "code": code.code if code else "",
        "code_name": code.name if code else "（已删除的账务代码）",
        "code_type": code.code_type if code else "",
        "shop_id": t.shop_id or "",
        "shop_name": (shops or {}).get(t.shop_id or "", "") if t.shop_id else "",
        "trans_type": t.trans_type,
        "trans_type_text": "收入" if t.trans_type == "income" else "支出",
        "amount": round(t.amount or 0, 2),
        "remark": t.remark or "",
        "created_by": t.created_by or "",
        "created_by_name": (users or {}).get(t.created_by or "", t.created_by or ""),
        "create_time": t.create_time.strftime("%Y-%m-%d %H:%M:%S") if t.create_time else None,
        "update_by": t.update_by or "",
        "updated_at": t.updated_at.strftime("%Y-%m-%d %H:%M:%S") if t.updated_at else None,
    }


# ==================== 账务代码（老板维护） ====================
@router.get("/api/accounting-codes/")
async def list_accounting_codes(
    code_type: str = Query(None, description="income=非交易收入 / expense=非交易支出，空=全部"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """账务代码列表（登录即可查看，供录入下拉使用）。"""
    _check_perm(current_user)
    query = select(AccountingCode)
    if code_type in ("income", "expense"):
        query = query.where(AccountingCode.code_type == code_type)
    rows = (await db.execute(query.order_by(AccountingCode.code))).scalars().all()
    return {"items": [_code_to_dict(c) for c in rows]}


@router.post("/api/accounting-codes/")
async def create_accounting_code(
    payload: AccountingCodeCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """新增账务代码（老板端）。代码自动生成。"""
    _check_boss(current_user)
    if payload.code_type not in ("income", "expense"):
        raise HTTPException(status_code=400, detail="code_type 只能是 income 或 expense")
    code = await _gen_code(db, payload.code_type)
    row = AccountingCode(
        code=code,
        name=payload.name.strip(),
        code_type=payload.code_type,
        remark=(payload.remark or "").strip(),
        created_by=current_user.username,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    db.add(OperationLog(
        username=current_user.username,
        operation_type="账务代码新增",
        operation_content=f"新增账务代码 {code}（{row.name}，{'非交易收入' if row.code_type == 'income' else '非交易支出'}）",
    ))
    await db.commit()
    return _code_to_dict(row)


@router.put("/api/accounting-codes/{code_id}")
async def update_accounting_code(
    code_id: int,
    payload: AccountingCodeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """编辑账务代码（老板端）。"""
    _check_boss(current_user)
    row = (await db.execute(select(AccountingCode).where(AccountingCode.id == code_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="账务代码不存在")
    if payload.code_type not in ("income", "expense"):
        raise HTTPException(status_code=400, detail="code_type 只能是 income 或 expense")
    row.name = payload.name.strip()
    row.code_type = payload.code_type
    row.remark = (payload.remark or "").strip()
    await db.commit()
    db.add(OperationLog(
        username=current_user.username,
        operation_type="账务代码修改",
        operation_content=f"修改账务代码 {row.code}（{row.name}）",
    ))
    await db.commit()
    return _code_to_dict(row)


@router.delete("/api/accounting-codes/{code_id}")
async def delete_accounting_code(
    code_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """删除账务代码（老板端）。已被收支流水引用时禁止删除。"""
    _check_boss(current_user)
    row = (await db.execute(select(AccountingCode).where(AccountingCode.id == code_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="账务代码不存在")
    ref_count = (await db.execute(
        select(func.count()).select_from(NonTradeTransaction).where(NonTradeTransaction.code_id == code_id)
    )).scalar() or 0
    if ref_count:
        raise HTTPException(status_code=400, detail=f"该账务代码已被 {ref_count} 条收支记录引用，无法删除")
    await db.delete(row)
    await db.commit()
    db.add(OperationLog(
        username=current_user.username,
        operation_type="账务代码删除",
        operation_content=f"删除账务代码 {row.code}（{row.name}）",
    ))
    await db.commit()
    return {"message": "删除成功"}


# ==================== 非交易收支流水 ====================
@router.get("/api/non-trade-transactions/my-shops")
async def list_my_shops(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """当前用户自己创建的网店（供录入时"关联网店"下拉使用）。"""
    _check_perm(current_user)
    rows = (await db.execute(
        select(Shop).where(Shop.creator == current_user.username).order_by(Shop.shop_name)
    )).scalars().all()
    return {"items": [{"shop_id": s.shop_id, "shop_name": s.shop_name} for s in rows]}


@router.get("/api/non-trade-transactions/")
async def list_non_trade_transactions(
    code_id: int = Query(None),
    trans_type: str = Query(None, description="income=收入 / expense=支出"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    created_by: str = Query(None, description="录入人（仅老板端可按人员筛选）"),
    keyword: str = Query(None, description="账务代码/名称/备注 模糊"),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """收支流水列表：销售只看自己录入的，老板可看全部并按人员筛选。"""
    _check_perm(current_user)
    query = select(NonTradeTransaction)
    if current_user.role != "boss":
        query = query.where(NonTradeTransaction.created_by == current_user.username)
    else:
        if created_by:
            query = query.where(NonTradeTransaction.created_by == created_by)
    if code_id:
        query = query.where(NonTradeTransaction.code_id == code_id)
    if trans_type in ("income", "expense"):
        query = query.where(NonTradeTransaction.trans_type == trans_type)
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.where(NonTradeTransaction.create_time >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="start_date 格式应为 YYYY-MM-DD")
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.where(NonTradeTransaction.create_time < end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="end_date 格式应为 YYYY-MM-DD")
    if keyword:
        kw = keyword.strip()
        codes = await _code_map(db)
        match_ids = [cid for cid, c in codes.items() if kw in (c.name or "") or kw in (c.code or "")]
        conds = [NonTradeTransaction.remark.like(f"%{kw}%")]
        if match_ids:
            conds.append(NonTradeTransaction.code_id.in_(match_ids))
        query = query.where(or_(*conds))

    # 取全部（带筛选）行，用于汇总合计；再按分页截取当前页
    rows_all = (await db.execute(query.order_by(NonTradeTransaction.id.desc()))).scalars().all()
    total = len(rows_all)
    income_total = round(sum((r.amount or 0) for r in rows_all if r.trans_type == "income"), 2)
    expense_total = round(sum((r.amount or 0) for r in rows_all if r.trans_type == "expense"), 2)
    rows = rows_all[skip: skip + limit]

    codes = await _code_map(db)
    shop_ids = {t.shop_id for t in rows if t.shop_id}
    shops = {}
    if shop_ids:
        for s in (await db.execute(select(Shop).where(Shop.shop_id.in_(shop_ids)))).scalars().all():
            shops[s.shop_id] = s.shop_name
    user_map = {}
    for u in (await db.execute(select(User))).scalars().all():
        user_map[u.username] = u.real_name or u.username

    return {
        "total": total,
        "income_total": income_total,
        "expense_total": expense_total,
        "items": [await _tx_to_dict(db, t, codes, shops, user_map) for t in rows],
    }


@router.post("/api/non-trade-transactions/")
async def create_non_trade_transaction(
    payload: NonTradeCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """录入非交易收入/支出（本人数据）。"""
    _check_perm(current_user)
    code = (await db.execute(select(AccountingCode).where(AccountingCode.id == payload.code_id))).scalar_one_or_none()
    if not code:
        raise HTTPException(status_code=400, detail="账务代码不存在")
    if payload.trans_type not in ("income", "expense"):
        raise HTTPException(status_code=400, detail="trans_type 只能是 income 或 expense")
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="金额必须大于0")
    shop_id = (payload.shop_id or "").strip()
    if shop_id:
        shop = (await db.execute(select(Shop).where(Shop.shop_id == shop_id))).scalar_one_or_none()
        if not shop:
            raise HTTPException(status_code=400, detail="关联的网店不存在")
        if current_user.role != "boss" and shop.creator != current_user.username:
            raise HTTPException(status_code=403, detail="只能关联自己创建的网店")

    row = NonTradeTransaction(
        code_id=payload.code_id,
        shop_id=shop_id or None,
        trans_type=payload.trans_type,
        amount=round(payload.amount, 2),
        remark=(payload.remark or "").strip(),
        created_by=current_user.username,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return await _tx_to_dict(db, row)


@router.put("/api/non-trade-transactions/{tx_id}")
async def update_non_trade_transaction(
    tx_id: int,
    payload: NonTradeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """编辑收支流水（本人或老板）。"""
    _check_perm(current_user)
    row = (await db.execute(select(NonTradeTransaction).where(NonTradeTransaction.id == tx_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="收支记录不存在")
    if current_user.role != "boss" and row.created_by != current_user.username:
        raise HTTPException(status_code=403, detail="只能编辑自己录入的数据")
    code = (await db.execute(select(AccountingCode).where(AccountingCode.id == payload.code_id))).scalar_one_or_none()
    if not code:
        raise HTTPException(status_code=400, detail="账务代码不存在")
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="金额必须大于0")
    if payload.trans_type not in ("income", "expense"):
        raise HTTPException(status_code=400, detail="trans_type 只能是 income 或 expense")
    shop_id = (payload.shop_id or "").strip()
    if shop_id:
        shop = (await db.execute(select(Shop).where(Shop.shop_id == shop_id))).scalar_one_or_none()
        if not shop:
            raise HTTPException(status_code=400, detail="关联的网店不存在")
        if current_user.role != "boss" and shop.creator != current_user.username:
            raise HTTPException(status_code=403, detail="只能关联自己创建的网店")

    row.code_id = payload.code_id
    row.shop_id = shop_id or None
    row.trans_type = payload.trans_type
    row.amount = round(payload.amount, 2)
    row.remark = (payload.remark or "").strip()
    row.update_by = current_user.username
    await db.commit()
    return await _tx_to_dict(db, row)


@router.delete("/api/non-trade-transactions/{tx_id}")
async def delete_non_trade_transaction(
    tx_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """删除收支流水（本人或老板）。"""
    _check_perm(current_user)
    row = (await db.execute(select(NonTradeTransaction).where(NonTradeTransaction.id == tx_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="收支记录不存在")
    if current_user.role != "boss" and row.created_by != current_user.username:
        raise HTTPException(status_code=403, detail="只能删除自己录入的数据")
    await db.delete(row)
    await db.commit()
    return {"message": "删除成功"}


# ==================== 非交易收支统计（老板端） ====================
@router.get("/api/non-trade-transactions/summary")
async def non_trade_summary(
    start_date: str = Query(None, description="起始日期 YYYY-MM-DD（按录入时间）"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD（按录入时间）"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """统计报表：汇总 + 按账务代码维度 + 按人员维度。仅老板端。"""
    _check_boss(current_user)
    query = select(NonTradeTransaction)
    if start_date:
        try:
            query = query.where(NonTradeTransaction.create_time >= datetime.strptime(start_date, "%Y-%m-%d"))
        except ValueError:
            raise HTTPException(status_code=400, detail="start_date 格式应为 YYYY-MM-DD")
    if end_date:
        try:
            query = query.where(NonTradeTransaction.create_time < datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1))
        except ValueError:
            raise HTTPException(status_code=400, detail="end_date 格式应为 YYYY-MM-DD")

    rows = (await db.execute(query)).scalars().all()
    codes = await _code_map(db)
    user_map = {}
    for u in (await db.execute(select(User))).scalars().all():
        user_map[u.username] = u.real_name or u.username

    income_total = sum(r.amount for r in rows if r.trans_type == "income")
    expense_total = sum(r.amount for r in rows if r.trans_type == "expense")

    # 按账务代码维度
    by_code_map = {}
    for r in rows:
        c = codes.get(r.code_id)
        key = c.id if c else r.code_id
        if key not in by_code_map:
            by_code_map[key] = {
                "code_id": r.code_id,
                "code": c.code if c else "",
                "name": c.name if c else "（已删除的账务代码）",
                "code_type": c.code_type if c else "",
                "income_total": 0.0,
                "expense_total": 0.0,
                "count": 0,
            }
        item = by_code_map[key]
        if r.trans_type == "income":
            item["income_total"] += r.amount
        else:
            item["expense_total"] += r.amount
        item["count"] += 1
    by_code = [dict(v) | {"income_total": round(v["income_total"], 2), "expense_total": round(v["expense_total"], 2)} for v in by_code_map.values()]
    by_code.sort(key=lambda x: -(x["income_total"] + x["expense_total"]))

    # 按人员维度
    by_user_map = {}
    for r in rows:
        key = r.created_by or "未知"
        if key not in by_user_map:
            by_user_map[key] = {
                "username": key,
                "real_name": user_map.get(key, key),
                "income_total": 0.0,
                "expense_total": 0.0,
                "count": 0,
            }
        item = by_user_map[key]
        if r.trans_type == "income":
            item["income_total"] += r.amount
        else:
            item["expense_total"] += r.amount
        item["count"] += 1
    by_user = [dict(v) | {"income_total": round(v["income_total"], 2), "expense_total": round(v["expense_total"], 2)} for v in by_user_map.values()]
    by_user.sort(key=lambda x: -(x["income_total"] + x["expense_total"]))

    return {
        "summary": {
            "income_total": round(income_total, 2),
            "expense_total": round(expense_total, 2),
            "net": round(income_total - expense_total, 2),
            "count": len(rows),
        },
        "by_code": by_code,
        "by_user": by_user,
    }
