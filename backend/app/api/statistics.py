# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from ..models.models import beijing_now
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, Float, desc
from ..core.database import get_db
from ..core.security import get_current_active_user
from ..models.models import Order, User, Product, Category, Brand, Shop
from ..api.settings import read_setting

router = APIRouter(prefix="/api/statistics", tags=["数据统计"])

# ==================== 测试接口 ====================
@router.get("/test")
async def test_statistics_api():
    """测试接口 - 用于验证statistics模块是否正确加载"""
    return {"status": "success", "message": "Statistics API is working", "timestamp": beijing_now().isoformat()}

# ==================== 智慧大屏专用接口 ====================

@router.get("/dashboard/overview")
async def get_dashboard_overview(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取智慧大屏订单总览数据
    - 总订单数
    - 已发货订单数
    - 待发货订单数
    - 虚拟发货订单数
    - 发货率
    - 待发货预警状态
    """
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="权限不足，仅老板端可访问")
    
    # 获取总订单数
    total_query = select(func.count(Order.id))
    total_result = await db.execute(total_query)
    total_orders = total_result.scalar() or 0
    
    # 获取已发货订单数
    shipped_query = select(func.count(Order.id)).filter(Order.shipping_status == "shipped")
    shipped_result = await db.execute(shipped_query)
    shipped_orders = shipped_result.scalar() or 0
    
    # 获取待发货订单数
    pending_query = select(func.count(Order.id)).filter(Order.shipping_status == "pending")
    pending_result = await db.execute(pending_query)
    pending_orders = pending_result.scalar() or 0
    
    # 获取虚拟发货订单数
    virtual_query = select(func.count(Order.id)).filter(Order.shipping_status.in_(["virtual", "virtual_shipped"]))
    virtual_result = await db.execute(virtual_query)
    virtual_orders = virtual_result.scalar() or 0

    # 已退货/退款订单数
    refunded_query = select(func.count(Order.id)).filter(Order.shipping_status == "refunded")
    refunded_result = await db.execute(refunded_query)
    refunded_orders = refunded_result.scalar() or 0

    # 退货金额（已退货订单的销售金额合计）
    refunded_amount_query = select(func.sum(func.cast(Order.sales_amount, Float))).filter(Order.shipping_status == "refunded")
    refunded_amount_result = await db.execute(refunded_amount_query)
    refunded_amount = round(refunded_amount_result.scalar() or 0, 2)

    # 计算发货率
    shipped_percentage = round((shipped_orders / total_orders) * 100, 1) if total_orders > 0 else 0
    
    # 判断待发货预警（待发货超过100单触发预警）
    pending_warning = pending_orders > 100
    
    return {
        "total_orders": total_orders,
        "shipped_orders": shipped_orders,
        "pending_orders": pending_orders,
        "virtual_orders": virtual_orders,
        "refunded_orders": refunded_orders,
        "refunded_amount": refunded_amount,
        "shipped_percentage": shipped_percentage,
        "pending_warning": pending_warning,
        "update_time": beijing_now().isoformat()
    }

@router.get("/dashboard/sales-ranking")
async def get_dashboard_sales_ranking(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取智慧大屏销售排行榜数据
    - 按销售额排名
    - 返回销售用户的销售金额、订单数等信息
    """
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="权限不足，仅老板端可访问")
    
    query = select(
        User.id.label("user_id"),
        User.username,
        User.real_name,
        func.sum(func.cast(Order.sales_amount, Float)).label("total_sales"),
        func.count(Order.id).label("order_count"),
        func.sum(func.cast(Order.commission_amount, Float)).label("total_commission")
    ).join(
        Order, User.username == Order.created_by
    ).filter(
        User.role == "sales",
        User.is_active == True
    ).group_by(
        User.id, User.username, User.real_name
    ).order_by(
        desc(func.sum(func.cast(Order.sales_amount, Float)))
    ).limit(limit)
    
    result = await db.execute(query)
    rows = result.all()
    
    # 计算总销售额用于百分比计算
    total_sales = sum(row.total_sales or 0 for row in rows)
    
    sales_ranking = []
    for row in rows:
        sales_ranking.append({
            "user_id": row.user_id,
            "username": row.username,
            "real_name": row.real_name,
            "total_sales": round(row.total_sales or 0, 2),
            "order_count": row.order_count or 0,
            "total_commission": round(row.total_commission or 0, 2),
            "percentage": round((row.total_sales or 0) / total_sales * 100, 1) if total_sales > 0 else 0
        })
    
    return {
        "data": sales_ranking,
        "total_sales": round(total_sales, 2),
        "update_time": beijing_now().isoformat()
    }

@router.get("/dashboard/product-ranking")
async def get_dashboard_product_ranking(
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取智慧大屏商品热销排行榜数据
    - 按销售额排名
    - 返回商品名称、销量、销售额、利润率等信息
    """
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="权限不足，仅老板端可访问")
    
    query = select(
        Order.product_name,
        func.count(Order.id).label("sales_count"),
        func.sum(func.cast(Order.sales_amount, Float)).label("total_revenue")
    ).filter(
        Order.product_name.isnot(None),
        Order.product_name != ""
    ).group_by(
        Order.product_name
    ).order_by(
        desc(func.sum(func.cast(Order.sales_amount, Float)))
    ).limit(limit)
    
    result = await db.execute(query)
    rows = result.all()
    
    product_ranking = []
    for row in rows:
        product_ranking.append({
            "product_name": row.product_name,
            "sales_count": row.sales_count or 0,
            "total_revenue": round(row.total_revenue or 0, 2),
            "profit_rate": round(20 + (row.sales_count or 0) % 15, 1)  # 模拟利润率
        })
    
    return {
        "data": product_ranking,
        "update_time": beijing_now().isoformat()
    }

@router.get("/dashboard/finance-summary")
async def get_dashboard_finance_summary(
    period: str = Query("month", enum=["week", "month", "quarter", "year"]),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取智慧大屏财务汇总数据
    - 总销售额
    - 总订单数
    - 平均客单价
    - 趋势数据
    """
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="权限不足，仅老板端可访问")
    
    # 根据周期设置时间范围
    end_date = datetime.now()
    if period == "week":
        start_date = end_date - timedelta(weeks=1)
    elif period == "month":
        start_date = end_date - timedelta(days=30)
    elif period == "quarter":
        start_date = end_date - timedelta(days=90)
    else:  # year
        start_date = end_date - timedelta(days=365)
    
    # 获取总销售额和订单数
    query = select(
        func.sum(func.cast(Order.sales_amount, Float)).label("total_revenue"),
        func.count(Order.id).label("order_count")
    ).filter(
        Order.created_at >= start_date,
        Order.created_at <= end_date
    )
    
    result = await db.execute(query)
    row = result.first()
    
    total_revenue = row.total_revenue or 0
    order_count = row.order_count or 0
    avg_order_value = round(total_revenue / order_count, 2) if order_count > 0 else 0
    
    # 生成趋势数据（最近12个周期）
    trend_data = []
    if period == "month":
        months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
        current_month = end_date.month - 1
        for i in range(12):
            month_index = (current_month - 11 + i) % 12
            trend_data.append({
                "period": months[month_index],
                "revenue": round(800000 + (current_month - month_index) * 50000 + (i % 3) * 30000, 2)
            })
    else:
        for i in range(12):
            trend_data.append({
                "period": f"周期{i+1}",
                "revenue": round(800000 + i * 50000 + (i % 3) * 30000, 2)
            })
    
    return {
        "total_revenue": round(total_revenue, 2),
        "order_count": order_count,
        "avg_order_value": avg_order_value,
        "period": period,
        "trend_data": trend_data,
        "update_time": beijing_now().isoformat()
    }

@router.get("/dashboard/sales-performance")
async def get_dashboard_sales_performance(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取智慧大屏销售业绩详情数据
    - 每个销售的订单完成情况
    - 销售金额统计
    """
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="权限不足，仅老板端可访问")
    
    query = select(
        User.id.label("user_id"),
        User.username,
        User.real_name,
        User.commission_rate,
        func.count(Order.id).label("total_orders"),
        func.sum(func.cast(Order.sales_amount, Float)).label("total_sales"),
        func.sum(func.cast(Order.commission_amount, Float)).label("total_commission"),
        func.count(Order.id).filter(Order.shipping_status == "shipped").label("shipped_orders"),
        func.count(Order.id).filter(Order.shipping_status == "pending").label("pending_orders")
    ).join(
        Order, User.username == Order.created_by, isouter=True
    ).filter(
        User.role == "sales",
        User.is_active == True
    ).group_by(
        User.id, User.username, User.real_name, User.commission_rate
    ).order_by(
        desc(func.sum(func.cast(Order.sales_amount, Float)))
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    performance_data = []
    for row in rows:
        total_orders = row.total_orders or 0
        shipped_orders = row.shipped_orders or 0
        shipped_percentage = round((shipped_orders / total_orders) * 100, 1) if total_orders > 0 else 0
        
        performance_data.append({
            "user_id": row.user_id,
            "username": row.username,
            "real_name": row.real_name,
            "commission_rate": row.commission_rate or 0,
            "total_orders": total_orders,
            "shipped_orders": shipped_orders,
            "pending_orders": row.pending_orders or 0,
            "shipped_percentage": shipped_percentage,
            "total_sales": round(row.total_sales or 0, 2),
            "total_commission": round(row.total_commission or 0, 2),
            "rank": "senior" if (row.commission_rate or 0) >= 5 else "middle" if (row.commission_rate or 0) >= 3 else "junior"
        })
    
    return {
        "data": performance_data,
        "update_time": beijing_now().isoformat()
    }

@router.get("/sales/total")
async def get_total_sales(
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取销售总金额统计
    
    参数:
    - start_date: 开始日期 (YYYY-MM-DD)，不传则查询最近365天
    - end_date: 结束日期 (YYYY-MM-DD)，不传则查询最近365天
    
    返回:
    - total_amount: 总金额
    - order_count: 订单数
    """
    if not end_date:
        end_date = beijing_now().strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
    end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    
    query = select(
        func.sum(func.cast(Order.sales_amount, Float)).label("total_amount"),
        func.count(Order.id).label("order_count")
    ).filter(
        Order.created_at >= start_datetime,
        Order.created_at < end_datetime
    )
    
    if current_user.role == "sales":
        query = query.filter(Order.created_by == current_user.username)
    
    result = await db.execute(query)
    row = result.first()
    
    return {
        "total_amount": round(row.total_amount or 0, 2),
        "order_count": row.order_count or 0,
        "start_date": start_date,
        "end_date": end_date
    }

@router.get("/commission/theoretical")
async def get_theoretical_commission(
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取理论应得提成（按销售时间统计）
    """
    if not end_date:
        end_date = beijing_now().strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
    end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    
    query = select(
        func.sum(func.cast(Order.commission_amount, Float)).label("total_commission"),
        func.count(Order.id).label("order_count")
    ).filter(
        Order.created_at >= start_datetime,
        Order.created_at < end_datetime
    )
    
    if current_user.role == "sales":
        query = query.filter(Order.created_by == current_user.username)
    
    result = await db.execute(query)
    row = result.first()
    
    return {
        "total_commission": round(row.total_commission or 0, 2),
        "order_count": row.order_count or 0,
        "start_date": start_date,
        "end_date": end_date
    }

@router.get("/commission/actual")
async def get_actual_commission(
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取实际应得提成（按发货时间统计）
    """
    if not end_date:
        end_date = beijing_now().strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
    end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    
    query = select(
        func.sum(func.cast(Order.commission_amount, Float)).label("total_commission"),
        func.count(Order.id).label("order_count")
    ).filter(
        Order.shipping_time >= start_datetime,
        Order.shipping_time < end_datetime,
        Order.shipping_status == "shipped"
    )
    
    if current_user.role == "sales":
        query = query.filter(Order.created_by == current_user.username)
    
    result = await db.execute(query)
    row = result.first()
    
    return {
        "total_commission": round(row.total_commission or 0, 2),
        "order_count": row.order_count or 0,
        "start_date": start_date,
        "end_date": end_date
    }

@router.get("/commission/by-user")
async def get_commission_by_user(
    start_date: str = Query(None),
    end_date: str = Query(None),
    user_id: int = Query(None, description="筛选指定用户ID"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取每个销售端用户的实际提成统计（按发货时间统计）- 仅老板端可用
    支持按用户ID筛选
    """
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="权限不足，仅老板端可访问")
    
    if not end_date:
        end_date = beijing_now().strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
    end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    
    query = select(
        User.id.label("user_id"),
        User.username,
        User.real_name,
        User.commission_rate,
        func.sum(func.cast(Order.commission_amount, Float)).label("total_commission"),
        func.count(Order.id).label("order_count"),
        func.sum(func.cast(Order.sales_amount, Float)).label("total_sales")
    ).join(
        Order, User.username == Order.created_by
    ).filter(
        Order.shipping_time >= start_datetime,
        Order.shipping_time < end_datetime,
        Order.shipping_status == "shipped",
        User.role == "sales",
        User.is_active == True
    )
    
    if user_id:
        query = query.filter(User.id == user_id)
    
    query = query.group_by(
        User.id, User.username, User.real_name, User.commission_rate
    ).order_by(
        func.sum(func.cast(Order.commission_amount, Float)).desc()
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    user_commissions = []
    for row in rows:
        user_commissions.append({
            "user_id": row.user_id,
            "username": row.username,
            "real_name": row.real_name,
            "commission_rate": row.commission_rate or 0,
            "total_commission": round(row.total_commission or 0, 2),
            "order_count": row.order_count or 0,
            "total_sales": round(row.total_sales or 0, 2)
        })
    
    total_commission = sum(item["total_commission"] for item in user_commissions)
    total_orders = sum(item["order_count"] for item in user_commissions)
    total_sales = sum(item["total_sales"] for item in user_commissions)
    
    return {
        "data": user_commissions,
        "summary": {
            "total_commission": round(total_commission, 2),
            "total_orders": total_orders,
            "total_sales": round(total_sales, 2)
        },
        "start_date": start_date,
        "end_date": end_date
    }

@router.get("/avg-shipping-time")
async def get_avg_shipping_time(
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取平均发货时长统计（从订单创建到发货的平均时间）
    """
    if not end_date:
        end_date = beijing_now().strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
    end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    
    query = select(
        func.avg(func.julianday(Order.shipping_time) - func.julianday(Order.created_at)).label("avg_days")
    ).filter(
        Order.shipping_time >= start_datetime,
        Order.shipping_time < end_datetime,
        Order.shipping_status == "shipped"
    )
    
    if current_user.role == "sales":
        query = query.filter(Order.created_by == current_user.username)
    
    result = await db.execute(query)
    avg_days = result.scalar() or 0
    
    avg_hours = avg_days * 24
    
    return {
        "avg_days": round(avg_days, 2),
        "avg_hours": round(avg_hours, 1),
        "start_date": start_date,
        "end_date": end_date
    }

# ==================== 工厂端工作台统计 ====================

@router.get("/factory-dashboard")
async def get_factory_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    工厂端工作台统计卡片数据
    - 全部订单数 / 待发货 / 已发货
    - 未生产 / 生产中 / 生产完成
    - 工厂端和老板端可访问
    """
    if current_user.role not in ("factory", "boss"):
        raise HTTPException(status_code=403, detail="权限不足")

    # 全部订单数
    total_result = await db.execute(select(func.count(Order.id)))
    total_orders = total_result.scalar() or 0

    # 待发货（shipping_status = pending）
    pending_result = await db.execute(
        select(func.count(Order.id)).filter(Order.shipping_status == "pending")
    )
    pending_orders = pending_result.scalar() or 0

    # 已发货（shipping_status = shipped）
    shipped_result = await db.execute(
        select(func.count(Order.id)).filter(Order.shipping_status == "shipped")
    )
    shipped_orders = shipped_result.scalar() or 0

    # 虚拟发货（shipping_status = virtual）
    virtual_result = await db.execute(
        select(func.count(Order.id)).filter(Order.shipping_status == "virtual")
    )
    virtual_orders = virtual_result.scalar() or 0

    # 已退货/退款（shipping_status = refunded）
    refunded_result = await db.execute(
        select(func.count(Order.id)).filter(Order.shipping_status == "refunded")
    )
    refunded_orders = refunded_result.scalar() or 0

    # 未生产（produce_status = unproduce）
    unproduce_result = await db.execute(
        select(func.count(Order.id)).filter(Order.produce_status == "unproduce")
    )
    unproduce_orders = unproduce_result.scalar() or 0

    # 生产中（produce_status = producing）
    producing_result = await db.execute(
        select(func.count(Order.id)).filter(Order.produce_status == "producing")
    )
    producing_orders = producing_result.scalar() or 0

    # 生产完成（produce_status = produced）
    produced_result = await db.execute(
        select(func.count(Order.id)).filter(Order.produce_status == "produced")
    )
    produced_orders = produced_result.scalar() or 0

    return {
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "shipped_orders": shipped_orders,
        "virtual_orders": virtual_orders,
        "refunded_orders": refunded_orders,
        "unproduce_orders": unproduce_orders,
        "producing_orders": producing_orders,
        "produced_orders": produced_orders,
        "update_time": beijing_now().isoformat()
    }


@router.get("/shipping-dashboard")
async def get_shipping_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    发货端工作台统计卡片数据
    - 全部订单数 / 待发货 / 已发货
    - 发货端可访问（老板端可查看）
    """
    if current_user.role not in ("shipping", "boss"):
        raise HTTPException(status_code=403, detail="权限不足")

    # 全部订单数
    total_result = await db.execute(select(func.count(Order.id)))
    total_orders = total_result.scalar() or 0

    # 待发货（shipping_status = pending）
    pending_result = await db.execute(
        select(func.count(Order.id)).filter(Order.shipping_status == "pending")
    )
    pending_orders = pending_result.scalar() or 0

    # 已发货（shipping_status = shipped）
    shipped_result = await db.execute(
        select(func.count(Order.id)).filter(Order.shipping_status == "shipped")
    )
    shipped_orders = shipped_result.scalar() or 0

    return {
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "shipped_orders": shipped_orders,
        "update_time": beijing_now().isoformat()
    }


@router.get("/process-flow")
async def get_process_flow_stats(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    老板端工作台三段式流程图统计（销售 -> 生产 -> 发货）
    全部按订单当前状态实时计数：
    - 销售：总订单数 / 未发货(pending) / 虚拟发货(virtual) / 已退货(refunded)
    - 生产：未生产(unproduce) / 生产中(producing) / 生产完成(produced)
    - 发货：未发货(pending) / 已发货(shipped)
    """
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="权限不足，仅老板端可访问")

    async def count(filter_expr):
        result = await db.execute(select(func.count(Order.id)).filter(filter_expr))
        return result.scalar() or 0

    # 销售段
    total_orders = await count(True)
    sales_pending = await count(Order.shipping_status == "pending")
    sales_virtual = await count(Order.shipping_status == "virtual")
    sales_refunded = await count(Order.shipping_status == "refunded")

    # 生产段
    produce_unproduce = await count(Order.produce_status == "unproduce")
    produce_producing = await count(Order.produce_status == "producing")
    produce_produced = await count(Order.produce_status == "produced")

    # 发货段
    shipping_pending = await count(Order.shipping_status == "pending")
    shipping_shipped = await count(Order.shipping_status == "shipped")

    return {
        "sales": {
            "total_orders": total_orders,
            "pending_orders": sales_pending,
            "virtual_orders": sales_virtual,
            "refunded_orders": sales_refunded
        },
        "produce": {
            "unproduce_orders": produce_unproduce,
            "producing_orders": produce_producing,
            "produced_orders": produce_produced
        },
        "shipping": {
            "pending_orders": shipping_pending,
            "shipped_orders": shipping_shipped
        },
        "update_time": beijing_now().isoformat()
    }


@router.get("/overview")
async def get_overview_statistics(
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取综合统计概览
    """
    if not end_date:
        end_date = beijing_now().strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
    end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    
    total_query = select(func.count(Order.id)).filter(
        Order.created_at >= start_datetime,
        Order.created_at < end_datetime
    )
    if current_user.role == "sales":
        total_query = total_query.filter(Order.created_by == current_user.username)
    
    shipped_query = select(func.count(Order.id)).filter(
        Order.shipping_status == "shipped",
        Order.created_at >= start_datetime,
        Order.created_at < end_datetime
    )
    if current_user.role == "sales":
        shipped_query = shipped_query.filter(Order.created_by == current_user.username)
    
    sales_query = select(func.sum(func.cast(Order.sales_amount, Float))).filter(
        Order.created_at >= start_datetime,
        Order.created_at < end_datetime
    )
    if current_user.role == "sales":
        sales_query = sales_query.filter(Order.created_by == current_user.username)
    
    pending_query = select(func.count(Order.id)).filter(
        Order.shipping_status == "pending",
        Order.created_at >= start_datetime,
        Order.created_at < end_datetime
    )
    if current_user.role == "sales":
        pending_query = pending_query.filter(Order.created_by == current_user.username)
    
    total_result = await db.execute(total_query)
    shipped_result = await db.execute(shipped_query)
    sales_result = await db.execute(sales_query)
    pending_result = await db.execute(pending_query)
    
    return {
        "total_orders": total_result.scalar() or 0,
        "shipped_orders": shipped_result.scalar() or 0,
        "pending_orders": pending_result.scalar() or 0,
        "total_sales": round(sales_result.scalar() or 0, 2),
        "start_date": start_date,
        "end_date": end_date
    }


@router.get("/overdue")
async def get_overdue_orders(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    超期订单统计（老板端工作台经营概览卡片）
    下单时间距当前超过「系统参数-超期订单天数」且尚未发货完成的订单视为超期。
    """
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="权限不足，仅老板端可访问")

    # 读取系统参数：超期订单天数（默认 7 天）
    days_str = await read_setting(db, "overdue_order_days", "7")
    try:
        overdue_days = int(float(days_str))
    except (TypeError, ValueError):
        overdue_days = 7
    if overdue_days < 0:
        overdue_days = 0

    threshold = beijing_now() - timedelta(days=overdue_days)

    # 超期判定：下单时间早于阈值，且尚未发货完成（shipping_status 不为 shipped/refunded）
    async def count(*filters):
        stmt = select(func.count(Order.id))
        for f in filters:
            stmt = stmt.filter(f)
        result = await db.execute(stmt)
        return result.scalar() or 0

    unfinished = (Order.shipping_status.notin_(["shipped", "refunded"]))
    total = await count(Order.created_at < threshold, unfinished)
    pending = await count(Order.created_at < threshold, unfinished, Order.shipping_status == "pending")
    producing = await count(
        Order.created_at < threshold,
        unfinished,
        Order.shipping_status.in_(["pending", "virtual"]),
        Order.produce_status.in_(["unproduce", "producing"])
    )

    return {
        "overdue_days": overdue_days,
        "total_overdue": total,
        "pending_overdue": pending,
        "producing_overdue": producing,
        "update_time": beijing_now().isoformat()
    }


# ==================== 销售统计（人员/类别/品牌/商品 汇总） ====================
@router.get("/sales-summary")
async def get_sales_summary(
    summary_type: str = Query("product", description="person/category/brand/product"),
    keyword: str = Query(None, description="名称模糊查询（人员/类别/品牌/商品）"),
    category_id: int = Query(None, description="按类别（二级）过滤"),
    brand_id: int = Query(None, description="按品牌过滤"),
    start_date: str = Query(None, description="起始日期 YYYY-MM-DD（按下单时间）"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD（按下单时间）"),
    limit: int = Query(1000, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """销售汇总报表数据源。
    维度：person=人员 / category=二级类别 / brand=品牌 / product=商品。
    指标：销售金额（sum(sales_amount)）、销售数量（订单数，系统无数量字段按 1 计）、
          毛利（销售金额 - 商品成本价；成本价取自 products 表按商品名匹配，无匹配或未填按 0）。
    说明：订单与商品按 product_name 文本匹配（订单无商品编码字段），商品重名时取其一成本。
    权限：仅老板端与工厂端可访问。
    """
    if current_user.role not in ("boss", "factory"):
        raise HTTPException(status_code=403, detail="权限不足，仅老板端/工厂端可访问")

    # ---- 1. 日期范围（下单时间）----
    start_dt = None
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="start_date 格式应为 YYYY-MM-DD")
    end_dt = None
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        except ValueError:
            raise HTTPException(status_code=400, detail="end_date 格式应为 YYYY-MM-DD")

    # ---- 2. 拉取订单明细（仅需要的字段；内网轻量数据量，内存聚合避免 join 膨胀）----
    order_query = select(
        Order.product_name,
        Order.sales_amount,
        Order.created_by,
        Order.created_at
    )
    if start_dt:
        order_query = order_query.where(Order.created_at >= start_dt)
    if end_dt:
        order_query = order_query.where(Order.created_at < end_dt)

    # 退款单不计入销售（shipping_status=refunded 属退货）
    order_query = order_query.where(Order.shipping_status != "refunded")

    rows = (await db.execute(order_query)).all()

    # ---- 3. 商品成本/类别/品牌映射（product_name -> 取第一条）----
    prod_result = await db.execute(select(Product))
    prod_map = {}
    for p in prod_result.scalars().all():
        if p.product_name not in prod_map:
            prod_map[p.product_name] = {
                "category_id": p.category_id,
                "brand_id": p.brand_id,
                "cost_price": p.cost_price if isinstance(p.cost_price, (int, float)) else 0.0
            }

    # 类别名映射
    cat_map = {}
    for c in (await db.execute(select(Category))).scalars().all():
        cat_map[c.id] = c.category_name

    # 品牌名映射
    brand_map = {}
    for b in (await db.execute(select(Brand))).scalars().all():
        brand_map[b.id] = b.brand_name

    # 人员名映射（真实姓名优先）
    user_map = {}
    for u in (await db.execute(select(User))).scalars().all():
        user_map[u.username] = u.real_name or u.username

    # ---- 4. 分组聚合 ----
    groups = {}
    for r in rows:
        product_name = r.product_name or ""
        pmeta = prod_map.get(product_name) or {"category_id": None, "brand_id": None, "cost_price": 0.0}
        cat_id = pmeta["category_id"]
        brd_id = pmeta["brand_id"]

        # 构造分组 key 与名称
        if summary_type == "person":
            key = str(r.created_by or "")
            name = user_map.get(key) or key or "未知"
        elif summary_type == "category":
            key = str(cat_id)
            name = cat_map.get(cat_id) if cat_id is not None else "未分类"
        elif summary_type == "brand":
            key = str(brd_id)
            name = brand_map.get(brd_id) if brd_id is not None else "未分类"
        else:  # product
            key = product_name
            name = product_name or "未填商品名"

        if not key:
            key = "unknown"

        # keyword 过滤（名称模糊）
        if keyword:
            kw = keyword.strip().lower()
            if kw and kw not in (name or "").lower():
                continue

        # category/brand 过滤
        if category_id is not None and cat_id != category_id:
            continue
        if brand_id is not None and brd_id != brand_id:
            continue

        try:
            amount = float(r.sales_amount or 0)
        except (TypeError, ValueError):
            amount = 0.0

        g = groups.get(key)
        if g is None:
            g = {"name": name, "sales_amount": 0.0, "sales_count": 0, "gross_profit": 0.0}
            groups[key] = g
        g["sales_amount"] += amount
        g["sales_count"] += 1
        g["gross_profit"] += amount - pmeta["cost_price"]

    # ---- 5. 排序（销售金额降序）并输出 ----
    items = sorted(groups.values(), key=lambda x: x["sales_amount"], reverse=True)[:limit]
    totals = {
        "sales_amount": round(sum(i["sales_amount"] for i in groups.values()), 2),
        "sales_count": sum(i["sales_count"] for i in groups.values()),
        "gross_profit": round(sum(i["gross_profit"] for i in groups.values()), 2)
    }
    for i in items:
        i["sales_amount"] = round(i["sales_amount"], 2)
        i["gross_profit"] = round(i["gross_profit"], 2)

    return {"type": summary_type, "items": items, "totals": totals}


# ==================== 毛利分析（按下单时间 / 按发货时间） ====================
@router.get("/gross-profit/list")
async def get_gross_profit_list(
    time_type: str = Query("order", description="order=按下单时间 / shipping=按发货时间"),
    start_date: str = Query(None, description="起始日期 YYYY-MM-DD"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD"),
    sales_person: str = Query(None, description="销售人员（真实姓名/用户名，模糊）"),
    brand: str = Query(None, description="品牌名称（模糊）"),
    category: str = Query(None, description="类别名称（模糊）"),
    platform_order_no: str = Query(None, description="平台订单号（模糊）"),
    product_name: str = Query(None, description="商品名称（模糊）"),
    limit: int = Query(5000, ge=1, le=20000),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """毛利分析明细：订单毛利 = 销售金额 - 商品成本价（orders.gross_profit）。
    支持按下单时间（created_at）或发货时间（shipping_time）过滤。
    筛选条件均支持模糊匹配（前端既可输入关键字，也可下拉选择后传入名称）。
    仅老板端/工厂端可访问（毛利含成本信息）。
    """
    if current_user.role not in ("boss", "factory"):
        raise HTTPException(status_code=403, detail="权限不足，仅老板端/工厂端可访问")

    start_dt = None
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="start_date 格式应为 YYYY-MM-DD")
    end_dt = None
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        except ValueError:
            raise HTTPException(status_code=400, detail="end_date 格式应为 YYYY-MM-DD")

    query = select(
        Order.order_id,
        Order.platform_order_no,
        Order.product_name,
        Order.gross_profit,
        Order.created_by,
        Order.created_at,
        Order.shipping_time
    )

    # 退款单不计入毛利（已退货无利润）
    query = query.where(Order.shipping_status != "refunded")

    if time_type == "shipping":
        # 按发货时间统计：仅统计已发货（有发货时间）的订单
        query = query.where(Order.shipping_time.isnot(None))
        if start_dt:
            query = query.where(Order.shipping_time >= start_dt)
        if end_dt:
            query = query.where(Order.shipping_time < end_dt)
    else:
        if start_dt:
            query = query.where(Order.created_at >= start_dt)
        if end_dt:
            query = query.where(Order.created_at < end_dt)

    if platform_order_no:
        query = query.where(Order.platform_order_no.like(f"%{platform_order_no.strip()}%"))
    if product_name:
        query = query.where(Order.product_name.like(f"%{product_name.strip()}%"))

    rows = (await db.execute(query.limit(limit))).all()

    # 名称映射：人员（真实姓名优先）、品牌、类别（订单商品名 → products → brand/category）
    user_map = {}
    for u in (await db.execute(select(User))).scalars().all():
        user_map[u.username] = u.real_name or u.username

    brand_map = {}
    for b in (await db.execute(select(Brand))).scalars().all():
        brand_map[b.id] = b.brand_name
    cat_map = {}
    for c in (await db.execute(select(Category))).scalars().all():
        cat_map[c.id] = c.category_name

    prod_map = {}
    for p in (await db.execute(select(Product))).scalars().all():
        if p.product_name not in prod_map:
            prod_map[p.product_name] = {
                "brand": brand_map.get(p.brand_id) if p.brand_id is not None else None,
                "category": cat_map.get(p.category_id) if p.category_id is not None else None
            }

    items = []
    for r in rows:
        pname = r.product_name or ""
        pmeta = prod_map.get(pname) or {}
        brand_name = pmeta.get("brand") or "未分类"
        cat_name = pmeta.get("category") or "未分类"
        person = user_map.get(r.created_by or "") or (r.created_by or "未知")

        # 品牌/类别/人员模糊过滤（前端下拉选择传回名称，同样按名称过滤）
        if brand and brand.strip().lower() not in (brand_name or "").lower():
            continue
        if category and category.strip().lower() not in (cat_name or "").lower():
            continue
        if sales_person and sales_person.strip().lower() not in (person or "").lower():
            continue

        items.append({
            "order_id": r.order_id,
            "platform_order_no": r.platform_order_no or "",
            "product_name": pname,
            "gross_profit": round(r.gross_profit or 0, 2) if r.gross_profit is not None else 0,
            "sales_person": person,
            "brand": brand_name,
            "category": cat_name,
            "order_time": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else None,
            "shipping_time": r.shipping_time.strftime("%Y-%m-%d %H:%M:%S") if r.shipping_time else None
        })

    total_profit = round(sum(i["gross_profit"] for i in items), 2)
    return {
        "time_type": time_type,
        "items": items,
        "total_gross_profit": total_profit,
        "total_count": len(items)
    }


@router.get("/gross-profit/options")
async def get_gross_profit_options(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """毛利分析下拉选项：销售人员（订单创建人）、品牌、类别（含二级）。"""
    if current_user.role not in ("boss", "factory"):
        raise HTTPException(status_code=403, detail="权限不足")

    # 销售人员：订单创建人去重 → 真实姓名
    order_creators = set()
    for r in (await db.execute(select(Order.created_by).where(Order.created_by.isnot(None)))).all():
        order_creators.add(r[0])
    user_map = {}
    for u in (await db.execute(select(User))).scalars().all():
        user_map[u.username] = u.real_name or u.username
    persons = []
    for c in sorted(order_creators):
        persons.append(user_map.get(c) or c)

    brands = [{"id": b.id, "name": b.brand_name} for b in (await db.execute(select(Brand))).scalars().all()]
    cats = [{"id": c.id, "name": c.category_name} for c in (await db.execute(select(Category))).scalars().all()]

    return {"sales_persons": persons, "brands": brands, "categories": cats}


# ==================== 运费统计 ====================
@router.get("/freight-list")
async def get_freight_list(
    start_date: str = Query(None, description="起始日期 YYYY-MM-DD（按下单时间）"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD（按下单时间）"),
    platform_order_no: str = Query(None, description="平台订单号（模糊）"),
    logistics_company: str = Query(None, description="快递公司（模糊）"),
    limit: int = Query(5000, ge=1, le=20000),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """运费统计明细：平台订单号 / 运单号1 / 运单号2 / 运费 / 快递公司。
    按下单时间（created_at）时间段筛选；支持平台订单号、快递公司模糊查询。
    退款单不计入。仅老板端/工厂端可访问。
    """
    if current_user.role not in ("boss", "factory"):
        raise HTTPException(status_code=403, detail="权限不足，仅老板端/工厂端可访问")

    start_dt = None
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="start_date 格式应为 YYYY-MM-DD")
    end_dt = None
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        except ValueError:
            raise HTTPException(status_code=400, detail="end_date 格式应为 YYYY-MM-DD")

    query = select(
        Order.order_id,
        Order.platform_order_no,
        Order.logistics_no,
        Order.logistics_no_2,
        Order.freight,
        Order.logistics_company,
        Order.created_at
    )
    if start_dt:
        query = query.where(Order.created_at >= start_dt)
    if end_dt:
        query = query.where(Order.created_at < end_dt)
    # 退款单不计入
    query = query.where(Order.shipping_status != "refunded")
    if platform_order_no:
        query = query.where(Order.platform_order_no.like(f"%{platform_order_no.strip()}%"))
    if logistics_company:
        query = query.where(Order.logistics_company.like(f"%{logistics_company.strip()}%"))

    rows = (await db.execute(query.limit(limit))).all()

    items = []
    total_freight = 0.0
    for r in rows:
        try:
            freight = float(r.freight or 0)
        except (TypeError, ValueError):
            freight = 0.0
        total_freight += freight
        items.append({
            "order_id": r.order_id,
            "platform_order_no": r.platform_order_no or "",
            "logistics_no": r.logistics_no or "",
            "logistics_no_2": r.logistics_no_2 or "",
            "freight": round(freight, 2),
            "logistics_company": r.logistics_company or "",
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else None
        })

    return {
        "items": items,
        "total_freight": round(total_freight, 2),
        "total_count": len(items)
    }


# ==================== 销售趋势（按下单时间按天汇总金额） ====================
@router.get("/sales-trend")
async def get_sales_trend(
    days: int = Query(30, ge=1, le=365, description="统计最近 N 天，默认 30"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """按天汇总销售金额（按下单时间 created_at），用于数据总览折线图。
    X 轴=日期，Y 轴=当日销售金额汇总。缺失日期补 0；退款单不计入。
    销售端仅统计本人创建的订单，其他角色统计全部订单。
    """
    start = beijing_now() - timedelta(days=days - 1)
    start = datetime(start.year, start.month, start.day)

    query = select(
        func.date(Order.created_at).label("d"),
        func.sum(func.cast(Order.sales_amount, Float)).label("amt")
    )
    query = query.where(Order.created_at >= start)
    query = query.where(Order.shipping_status != "refunded")
    if current_user.role == "sales":
        query = query.where(Order.created_by == current_user.username)
    query = query.group_by(func.date(Order.created_at))
    query = query.order_by(func.date(Order.created_at))

    rows = (await db.execute(query)).all()
    amount_map = {r[0]: round(float(r[1] or 0), 2) for r in rows}

    # 补齐缺失日期（含今天）
    result = []
    total = 0.0
    for i in range(days):
        day = start + timedelta(days=i)
        ds = day.strftime("%Y-%m-%d")
        amt = amount_map.get(ds, 0.0)
        total += amt
        result.append({"date": ds, "amount": amt})

    return {"items": result, "total_amount": round(total, 2), "days": days}


# ==================== 销售统计下拉选项（人员/类别/品牌/商品） ====================
@router.get("/sales-summary/options")
async def get_sales_summary_options(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """销售统计查询条件下拉数据：销售人员（订单创建人）、类别、品牌、商品名称。"""
    if current_user.role not in ("boss", "factory"):
        raise HTTPException(status_code=403, detail="权限不足，仅老板端/工厂端可访问")

    order_creators = set()
    for r in (await db.execute(select(Order.created_by).where(Order.created_by.isnot(None)))).all():
        order_creators.add(r[0])
    user_map = {}
    for u in (await db.execute(select(User))).scalars().all():
        user_map[u.username] = u.real_name or u.username
    persons = sorted({user_map.get(c) or c for c in order_creators})

    brands = [{"id": b.id, "name": b.brand_name} for b in (await db.execute(select(Brand))).scalars().all()]
    cats = [{"id": c.id, "name": c.category_name} for c in (await db.execute(select(Category))).scalars().all()]

    # 商品名称：已出现在订单中的商品（去重），优先按 orders 中出现过的
    product_names = set()
    for r in (await db.execute(select(Order.product_name).where(Order.product_name.isnot(None)))).all():
        if r[0]:
            product_names.add(r[0])

    return {
        "sales_persons": persons,
        "brands": brands,
        "categories": cats,
        "products": sorted(product_names)
    }


# ==================== 网店销售统计 ====================
@router.get("/shop-sales-summary")
async def get_shop_sales_summary(
    start_date: str = Query(None, description="起始日期 YYYY-MM-DD（按下单时间）"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD（按下单时间）"),
    shop_id: str = Query(None, description="网店ID（模糊）"),
    creator: str = Query(None, description="创建者（模糊）"),
    limit: int = Query(1000, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """网店销售统计：按网店（shop_id）分组汇总。
    列：网店ID / 创建者 / 销售金额 / 总订单数 / 退货金额 / 退订单数。
    口径：销售金额=非退款单 sales_amount 合计；总订单数=全部订单数（含退款单）；
    退货金额/退订单数=shipping_status=refunded 的订单。按下单时间过滤。
    权限：仅老板端/工厂端。
    """
    if current_user.role not in ("boss", "factory"):
        raise HTTPException(status_code=403, detail="权限不足，仅老板端/工厂端可访问")

    start_dt = None
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="start_date 格式应为 YYYY-MM-DD")
    end_dt = None
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        except ValueError:
            raise HTTPException(status_code=400, detail="end_date 格式应为 YYYY-MM-DD")

    query = select(Order.shop_id, Order.sales_amount, Order.shipping_status)
    if start_dt:
        query = query.where(Order.created_at >= start_dt)
    if end_dt:
        query = query.where(Order.created_at < end_dt)
    rows = (await db.execute(query)).all()

    # 网店创建者映射（用户名 → 真实姓名）
    shop_creator = {}
    for s in (await db.execute(select(Shop))).scalars().all():
        shop_creator[s.shop_id] = s.creator
    user_name_map = {}
    for u in (await db.execute(select(User))).scalars().all():
        user_name_map[u.username] = u.real_name or u.username

    def creator_display(username):
        if not username:
            return "未知"
        return user_name_map.get(username) or username

    groups = {}
    for r in rows:
        sid = r.shop_id or ""
        key = sid or "未知网店"
        try:
            amt = float(r.sales_amount or 0)
        except (TypeError, ValueError):
            amt = 0.0
        g = groups.get(key)
        if g is None:
            g = {"shop_id": sid, "creator": creator_display(shop_creator.get(sid)),
                 "sales_amount": 0.0, "total_orders": 0,
                 "refund_amount": 0.0, "refund_count": 0}
            groups[key] = g
        g["total_orders"] += 1
        if r.shipping_status == "refunded":
            g["refund_count"] += 1
            g["refund_amount"] += amt
        else:
            g["sales_amount"] += amt

    items = list(groups.values())
    # 筛选：网店ID / 创建者 模糊
    if shop_id and shop_id.strip():
        kw = shop_id.strip().lower()
        items = [i for i in items if kw in (i["shop_id"] or "").lower()]
    if creator and creator.strip():
        kw = creator.strip().lower()
        items = [i for i in items if kw in (i["creator"] or "").lower()]

    items.sort(key=lambda x: x["sales_amount"], reverse=True)
    items = items[:limit]
    for i in items:
        i["sales_amount"] = round(i["sales_amount"], 2)
        i["refund_amount"] = round(i["refund_amount"], 2)

    totals = {
        "sales_amount": round(sum(i["sales_amount"] for i in items), 2),
        "total_orders": sum(i["total_orders"] for i in items),
        "refund_amount": round(sum(i["refund_amount"] for i in items), 2),
        "refund_count": sum(i["refund_count"] for i in items)
    }
    return {"items": items, "totals": totals}


# ==================== 汇总报表 → 订单明细钻取 ====================
_ORDER_STATUS_TEXT = {
    "pending": "待发货",
    "shipped": "已发货",
    "virtual": "虚拟发货",
    "virtual_shipped": "已虚拟发货",
    "refunded": "已退货/退款"
}


@router.get("/summary-order-details")
async def get_summary_order_details(
    mode: str = Query(..., description="shop=网店销售统计钻取 / sales=销售统计钻取"),
    shop_id: str = Query(None, description="网店ID（mode=shop，精确匹配；空=未知网店）"),
    only_refunded: bool = Query(False, description="mode=shop：true=仅退款单 / false=全部订单"),
    summary_type: str = Query(None, description="mode=sales：person/category/brand/product"),
    name: str = Query(None, description="mode=sales：点击行的分组名称（含 未分类/未知/未填商品名 特殊值）"),
    start_date: str = Query(None, description="起始日期 YYYY-MM-DD（按下单时间）"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD（按下单时间）"),
    limit: int = Query(2000, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """汇总报表钻取明细：点击网店销售统计的总订单数/退订单数、销售统计的销售数量，
    返回对应分组下的订单明细（平台订单号/商品名称/订单状态/订单金额）。
    口径与汇总接口保持一致：sales 模式剔除退款单；shop 模式由 only_refunded 决定。
    权限：仅老板端/工厂端。
    """
    if current_user.role not in ("boss", "factory"):
        raise HTTPException(status_code=403, detail="权限不足，仅老板端/工厂端可访问")

    start_dt = None
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="start_date 格式应为 YYYY-MM-DD")
    end_dt = None
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        except ValueError:
            raise HTTPException(status_code=400, detail="end_date 格式应为 YYYY-MM-DD")

    query = select(
        Order.platform_order_no,
        Order.product_name,
        Order.sales_amount,
        Order.shipping_status,
        Order.shop_id,
        Order.created_by,
        Order.created_at
    )
    if start_dt:
        query = query.where(Order.created_at >= start_dt)
    if end_dt:
        query = query.where(Order.created_at < end_dt)

    if mode == "shop":
        # 网店销售统计钻取：按网店ID精确匹配（未知网店 = shop_id 为空）
        sid = (shop_id or "").strip()
        if sid:
            query = query.where(Order.shop_id == sid)
        else:
            query = query.where((Order.shop_id.is_(None)) | (Order.shop_id == ""))
        if only_refunded:
            query = query.where(Order.shipping_status == "refunded")
    elif mode == "sales":
        # 销售统计钻取：销售金额/销售数量口径均剔除退款单
        query = query.where(Order.shipping_status != "refunded")
        name_key = (name or "").strip()
        if summary_type == "person":
            # 人员：created_by(用户名) → 真实姓名/用户名
            user_rows = (await db.execute(
                select(User.username, User.real_name)
            )).all()
            if name_key in ("", "未知"):
                query = query.where((Order.created_by.is_(None)) | (Order.created_by == ""))
            else:
                usernames = [u.username for u in user_rows
                             if (u.real_name or u.username) == name_key or u.username == name_key]
                if not usernames:
                    return {"mode": mode, "items": [], "total": 0}
                query = query.where(Order.created_by.in_(usernames))
        elif summary_type in ("category", "brand"):
            # 类别/品牌：订单商品名 → 商品档案的 category_id/brand_id
            prod_rows = (await db.execute(
                select(Product.product_name, Product.category_id, Product.brand_id)
            )).all()
            if summary_type == "category":
                meta_list = [(c.id, c.category_name) for c in (await db.execute(select(Category))).scalars().all()]
                field = "category_id"
            else:
                meta_list = [(b.id, b.brand_name) for b in (await db.execute(select(Brand))).scalars().all()]
                field = "brand_id"
            id_name = {i: nm for i, nm in meta_list}
            # 收集匹配目标商品名
            match_names = set()
            for pr in prod_rows:
                meta = {"category_id": pr.category_id, "brand_id": pr.brand_id}
                cid = meta.get(field)
                if name_key == "未分类":
                    if cid is None:
                        match_names.add(pr.product_name)
                elif cid in id_name and id_name[cid] == name_key:
                    match_names.add(pr.product_name)
            if not match_names:
                return {"mode": mode, "items": [], "total": 0}
            query = query.where(Order.product_name.in_(match_names))
        else:  # product
            if name_key in ("", "未填商品名"):
                query = query.where((Order.product_name.is_(None)) | (Order.product_name == ""))
            else:
                query = query.where(Order.product_name == name_key)
    else:
        raise HTTPException(status_code=400, detail="mode 仅支持 shop / sales")

    query = query.order_by(Order.created_at.desc()).limit(limit)
    rows = (await db.execute(query)).all()

    items = []
    for r in rows:
        try:
            amt = round(float(r.sales_amount or 0), 2)
        except (TypeError, ValueError):
            amt = 0.0
        items.append({
            "platform_order_no": r.platform_order_no or "-",
            "product_name": r.product_name or "-",
            "shipping_status": r.shipping_status or "",
            "shipping_status_text": _ORDER_STATUS_TEXT.get(r.shipping_status, r.shipping_status or "-"),
            "sales_amount": amt
        })
    return {"mode": mode, "items": items, "total": len(items)}
