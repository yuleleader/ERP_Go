# -*- coding: utf-8 -*-
"""预警中心：自动提醒销售员超期未生产 / 超期未发货订单。

口径与订单列表「超期订单」筛选完全一致：
- 超期 = 下单时间早于「超期订单天数」(system_settings.overdue_order_days，默认 7 天) 且未发货完成
  （shipping_status 不在 shipped/refunded 中，即 pending/virtual 均视为未发货完成）
- 超期未生产 = 超期 且 produce_status != produced
- 超期未发货 = 超期（未发货完成的订单天然满足）

可见范围：销售端只看自己创建的订单预警；老板端按销售员分组查看全部。
"""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.security import get_current_active_user
from ..models.models import Order, Shop, User, beijing_now
from ..api.settings import read_setting
from ..api.orders import effective_order_days

router = APIRouter(prefix="/api/warnings", tags=["预警中心"])


@router.get("/overdue")
async def get_overdue_warnings(
    days: int = Query(None, ge=0, description="超期天数（默认取系统参数 overdue_order_days）"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """超期预警：按销售员分组返回超期未生产/未发货订单明细。"""
    if current_user.role not in ("boss", "sales"):
        raise HTTPException(status_code=403, detail="仅老板端/销售端可查看预警中心")

    if days is None:
        days_str = await read_setting(db, "overdue_order_days", "7")
        try:
            days = int(float(days_str))
        except (TypeError, ValueError):
            days = 7
    if days < 0:
        days = 0

    threshold = beijing_now() - timedelta(days=days)

    query = select(Order).where(
        Order.created_at < threshold,
        Order.shipping_status.notin_(["shipped", "refunded"]),
    )
    if current_user.role != "boss":
        query = query.where(Order.created_by == current_user.username)

    orders = (await db.execute(query.order_by(Order.created_at.asc()))).scalars().all()

    # 店铺名映射
    shop_ids = {o.shop_id for o in orders if o.shop_id}
    shop_map = {}
    if shop_ids:
        for s in (await db.execute(select(Shop).where(Shop.shop_id.in_(shop_ids)))).scalars().all():
            shop_map[s.shop_id] = s.shop_name
    # 销售员真名映射
    user_map = {}
    for u in (await db.execute(select(User))).scalars().all():
        user_map[u.username] = u.real_name or u.username

    # 按创建人分组
    group_map = {}
    for o in orders:
        username = o.created_by or "未知"
        if username not in group_map:
            group_map[username] = {"unproduced": [], "unsent": []}
        item = {
            "order_id": o.order_id,
            "platform_order_no": o.platform_order_no or "",
            "product_name": o.product_name or "",
            "sales_amount": o.sales_amount or "",
            "shop_name": shop_map.get(o.shop_id) or o.shop_id or "",
            "shipping_status": o.shipping_status or "",
            "shipping_status_text": {"pending": "待发货", "virtual": "虚拟发货"}.get(o.shipping_status, o.shipping_status or ""),
            "produce_status": o.produce_status or "unproduce",
            "produce_status_text": {"unproduce": "未生产", "producing": "生产中", "produced": "生产完成"}.get(o.produce_status, o.produce_status or ""),
            "created_at": o.created_at.strftime("%Y-%m-%d %H:%M:%S") if o.created_at else None,
            "order_days": effective_order_days(o),
            "created_by": username,
            "created_by_name": user_map.get(username, username),
        }
        group_map[username]["unsent"].append(item)
        if o.produce_status != "produced":
            group_map[username]["unproduced"].append(item)

    groups = [
        {
            "username": u,
            "sales_person": user_map.get(u, u),
            "unproduced_count": len(v["unproduced"]),
            "unsent_count": len(v["unsent"]),
            "unproduced": v["unproduced"],
            "unsent": v["unsent"],
        }
        for u, v in sorted(group_map.items(), key=lambda kv: kv[0])
    ]
    total_unproduced = sum(len(v["unproduced"]) for v in group_map.values())
    total_unsent = sum(len(v["unsent"]) for v in group_map.values())

    return {
        "overdue_days": days,
        "total_unproduced": total_unproduced,
        "total_unsent": total_unsent,
        "sales_count": len(groups),
        "groups": groups,
    }
