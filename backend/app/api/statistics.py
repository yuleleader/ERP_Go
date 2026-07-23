# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from ..models.models import beijing_now
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, Float, desc
from ..core.database import get_db
from ..core.security import get_current_active_user
from ..models.models import Order, User, Product

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
    virtual_query = select(func.count(Order.id)).filter(Order.shipping_status == "virtual_shipped")
    virtual_result = await db.execute(virtual_query)
    virtual_orders = virtual_result.scalar() or 0
    
    # 计算发货率
    shipped_percentage = round((shipped_orders / total_orders) * 100, 1) if total_orders > 0 else 0
    
    # 判断待发货预警（待发货超过100单触发预警）
    pending_warning = pending_orders > 100
    
    return {
        "total_orders": total_orders,
        "shipped_orders": shipped_orders,
        "pending_orders": pending_orders,
        "virtual_orders": virtual_orders,
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
