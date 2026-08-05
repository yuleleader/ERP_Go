import asyncio
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, cast, Float
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_db
from ..core.security import get_current_active_user
from ..models.models import Order, User
from ..schemas.schemas import UserResponse


def _safe_float(value):
    """将 VARCHAR 数值字段安全转为 float，非法或空返回 0.0。"""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


router = APIRouter(prefix="/api/commission-settlement", tags=["commission-settlement"])

# 提成发放串行锁：防止并发发放重复计入
_pay_lock = asyncio.Lock()


def _parse_date_range(start_date: str, end_date: str):
    """解析结算日期区间（YYYY-MM-DD，结束日含当天）。返回 (开始datetime, 结束datetime+1天)。"""
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD 格式")
    if end_dt < start_dt:
        raise HTTPException(status_code=400, detail="结束日期不能早于开始日期")
    return start_dt, end_dt + timedelta(days=1)


@router.get("/unpaid")
async def get_unpaid_commission(
    start_date: str = Query(..., description="结算开始日期，格式 YYYY-MM-DD"),
    end_date: str = Query(..., description="结算结束日期，格式 YYYY-MM-DD（含当天）"),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user)
):
    if current_user.role not in ("boss", "sales"):
        raise HTTPException(status_code=403, detail="权限不足，仅老板端和销售端可访问")

    try:
        start_datetime, end_datetime = _parse_date_range(start_date, end_date)

        # 按销售汇总区间内【已发货】订单，同时统计 总额/已结算/未结算
        query = select(
            User.username,
            User.real_name,
            func.sum(func.cast(Order.commission_amount, Float)).label("total_commission"),
            func.count(Order.id).label("order_count"),
            func.sum(func.cast(Order.sales_amount, Float)).label("total_sales"),
            func.sum(func.cast(Order.commission_amount, Float)).filter(Order.commission_paid.is_(True)).label("paid_commission"),
            func.count(Order.id).filter(Order.commission_paid.is_(True)).label("paid_order_count"),
        ).join(Order, User.username == Order.created_by).filter(
            Order.shipping_time >= start_datetime,
            Order.shipping_time < end_datetime,
            Order.shipping_status == "shipped",
            User.role == "sales"
        )
        if current_user.role == "sales":
            query = query.filter(Order.created_by == current_user.username)
        query = query.group_by(User.username, User.real_name)

        result = await db.execute(query)
        rows = result.all()

        users = []
        unpaid_total = 0.0
        paid_total = 0.0
        unpaid_orders = 0
        for row in rows:
            total = float(row.total_commission or 0)
            paid = float(row.paid_commission or 0)
            unpaid = round(total - paid, 2)
            unpaid_total += unpaid
            paid_total += paid
            unpaid_orders += (row.order_count or 0) - (row.paid_order_count or 0)
            users.append({
                "username": row.username,
                "real_name": row.real_name,
                "total_commission": round(total, 2),   # 区间内应得提成总额
                "paid_commission": round(paid, 2),     # 已结算金额
                "unpaid_commission": unpaid,           # 未结算金额（可发放）
                "order_count": row.order_count or 0,
                "paid_order_count": row.paid_order_count or 0,
                "unpaid_order_count": (row.order_count or 0) - (row.paid_order_count or 0),
                "total_sales": round(float(row.total_sales or 0), 2)
            })

        summary = {
            "start_date": start_date,
            "end_date": end_date,
            "total_amount": round(unpaid_total, 2),                       # 未结算总额（用于发放）
            "paid_amount": round(paid_total, 2),                          # 已结算总额
            "total_all_amount": round(unpaid_total + paid_total, 2),      # 区间应发提成总额（已发+未发）
            "total_orders": unpaid_orders,                                # 未结算订单数
            "total_order_count": sum(u["order_count"] for u in users),    # 区间全部已发货订单数
            "total_sales": round(sum(u["total_sales"] for u in users), 2),
            "users": users
        }

        return {"code": 200, "message": "success", "data": summary}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unpaid/orders")
async def get_unpaid_orders(
    start_date: str = Query(..., description="结算开始日期，格式 YYYY-MM-DD"),
    end_date: str = Query(..., description="结算结束日期，格式 YYYY-MM-DD（含当天）"),
    username: str = Query(None, description="销售用户名，不传则查询所有销售"),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user)
):
    if current_user.role not in ("boss", "sales"):
        raise HTTPException(status_code=403, detail="权限不足，仅老板端和销售端可访问")

    try:
        start_datetime, end_datetime = _parse_date_range(start_date, end_date)

        query = select(Order).filter(
            Order.shipping_time >= start_datetime,
            Order.shipping_time < end_datetime,
            Order.shipping_status == "shipped"
        )
        if current_user.role == "sales":
            query = query.filter(Order.created_by == current_user.username)
        elif username:
            query = query.filter(Order.created_by == username)
        query = query.order_by(Order.shipping_time.desc())

        result = await db.execute(query)
        orders = result.scalars().all()

        order_list = []
        for order in orders:
            order_list.append({
                "id": order.id,
                "shop_id": order.shop_id,                                  # 平台（网店ID）
                "platform_order_no": order.platform_order_no,
                "product_name": order.product_name,
                "sales_amount": round(_safe_float(order.sales_amount), 2),
                "commission_amount": round(_safe_float(order.commission_amount), 2),
                "created_by": order.created_by,
                "shipping_time": order.shipping_time.isoformat() if order.shipping_time else None,
                "commission_paid": bool(order.commission_paid)             # 发放状态
            })

        return {"code": 200, "message": "success", "data": order_list}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pay")
async def pay_commission(
    start_date: str = Query(..., description="结算开始日期，格式 YYYY-MM-DD"),
    end_date: str = Query(..., description="结算结束日期，格式 YYYY-MM-DD（含当天）"),
    username: str = Query(None, description="销售用户名，不传则发放所有销售"),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user)
):
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="只有老板端可以发放提成")

    # 并发保护：同一进程内串行发放，避免两次并发请求读到同一批未发订单、重复计入提成
    async with _pay_lock:
        try:
            start_datetime, end_datetime = _parse_date_range(start_date, end_date)

            query = select(Order).filter(
                Order.shipping_time >= start_datetime,
                Order.shipping_time < end_datetime,
                Order.shipping_status == "shipped",
                Order.commission_paid == False
            )
            if username:
                query = query.filter(Order.created_by == username)

            result = await db.execute(query)
            orders = result.scalars().all()

            if not orders:
                raise HTTPException(status_code=400, detail=f"{start_date} 至 {end_date} 期间没有未发放的提成")

            total_amount = 0.0
            total_count = 0
            for order in orders:
                order.commission_paid = True
                total_amount += _safe_float(order.commission_amount)
                total_count += 1

            await db.commit()

            return {
                "code": 200,
                "message": "success",
                "data": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "username": username,
                    "paid_count": total_count,
                    "paid_amount": round(total_amount, 2)
                }
            }
        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
