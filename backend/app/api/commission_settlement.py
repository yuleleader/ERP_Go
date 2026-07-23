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


@router.get("/unpaid")
async def get_unpaid_commission(
    month: str = Query(..., description="查询月份，格式 YYYY-MM"),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user)
):
    try:
        year, month_num = map(int, month.split("-"))
        start_datetime = datetime(year, month_num, 1)
        if month_num == 12:
            end_datetime = datetime(year + 1, 1, 1)
        else:
            end_datetime = datetime(year, month_num + 1, 1)

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
            Order.commission_paid == False,
            User.role == "sales"
        ).group_by(User.username, User.real_name)

        result = await db.execute(query)
        rows = result.all()

        summary = {
            "month": month,
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
    except ValueError:
        raise HTTPException(status_code=400, detail="月份格式错误，请使用 YYYY-MM 格式")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unpaid/orders")
async def get_unpaid_orders(
    month: str = Query(..., description="查询月份，格式 YYYY-MM"),
    username: str = Query(None, description="销售用户名，不传则查询所有销售"),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user)
):
    try:
        year, month_num = map(int, month.split("-"))
        start_datetime = datetime(year, month_num, 1)
        if month_num == 12:
            end_datetime = datetime(year + 1, 1, 1)
        else:
            end_datetime = datetime(year, month_num + 1, 1)

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
    except ValueError:
        raise HTTPException(status_code=400, detail="月份格式错误，请使用 YYYY-MM 格式")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pay")
async def pay_commission(
    month: str = Query(..., description="发放月份，格式 YYYY-MM"),
    username: str = Query(None, description="销售用户名，不传则发放所有销售"),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user)
):
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="只有老板端可以发放提成")

    try:
        year, month_num = map(int, month.split("-"))
        start_datetime = datetime(year, month_num, 1)
        if month_num == 12:
            end_datetime = datetime(year + 1, 1, 1)
        else:
            end_datetime = datetime(year, month_num + 1, 1)

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
            raise HTTPException(status_code=400, detail=f"{month}月份没有未发放的提成")

        total_amount = 0
        total_count = 0

        for order in orders:
            order.commission_paid = True
            total_amount += order.commission_amount or 0
            total_count += 1

        await db.commit()

        return {
            "code": 200,
            "message": "success",
            "data": {
                "month": month,
                "username": username,
                "paid_count": total_count,
                "paid_amount": round(total_amount, 2)
            }
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="月份格式错误，请使用 YYYY-MM 格式")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
