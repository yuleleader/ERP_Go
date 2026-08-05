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

        query = select(
            User.username,
            User.real_name,
            func.sum(func.cast(Order.commission_amount, Float)).label("total_commission"),
            func.count(Order.id).label("order_count"),
            func.sum(func.cast(Order.sales_amount, Float)).label("total_sales")
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

        summary = {
            "start_date": start_date,
            "end_date": end_date,
            "total_amount": sum(row.total_commission or 0 for row in rows),
            "total_orders": sum(row.order_count or 0 for row in rows),
            "total_sales": sum(row.total_sales or 0 for row in rows),
            "users": [
                {
                    "username": row.username,
                    "real_name": row.real_name,
                    "total_commission": round(row.total_commission or 0, 2),
                    "order_count": row.order_count or 0,
                    "total_sales": round(row.total_sales or 0, 2)
                }
                for row in rows
            ]
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

        result = await db.execute(query)
        orders = result.scalars().all()

        order_list = []
        for order in orders:
            order_list.append({
                "id": order.id,
                "platform_order_no": order.platform_order_no,
                "product_name": order.product_name,
            "sales_amount": round(_safe_float(order.sales_amount), 2),
            "commission_amount": round(_safe_float(order.commission_amount), 2),
                "created_by": order.created_by,
                "shipping_time": order.shipping_time.isoformat() if order.shipping_time else None
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
