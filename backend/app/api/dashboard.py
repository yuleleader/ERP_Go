# -*- coding: utf-8 -*-
"""
智慧大屏专用API模块
独立注册路由，确保路由正确加载
"""
import asyncio
import time
from datetime import datetime, timedelta
from ..models.models import beijing_now
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, Float, desc, asc, text, update
from ..core.database import get_db
from ..core.security import get_current_active_user
from ..models.models import Order, User, Shop

router = APIRouter(prefix="/api/dashboard", tags=["智慧大屏"])

# ==================== 测试接口 ====================
@router.get("/test")
async def test_dashboard_api():
    """测试接口 - 用于验证智慧大屏API是否正确加载"""
    return {"status": "success", "message": "Dashboard API is working", "timestamp": beijing_now().isoformat()}

# ==================== 订单总览 ====================
@router.get("/overview")
async def get_dashboard_overview(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取智慧大屏订单总览数据
    - 仅boss角色可访问
    """
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="权限不足，仅老板端可访问")
    
    # 最近24个月起始时间
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)
    
    # 获取总订单数（最近24个月）
    total_query = select(func.count(Order.id)).filter(Order.created_at >= start_date)
    total_result = await db.execute(total_query)
    total_orders = total_result.scalar() or 0
    
    # 获取销售总金额（最近24个月）
    total_sales_query = select(func.sum(func.cast(Order.sales_amount, Float))).filter(Order.created_at >= start_date)
    total_sales_result = await db.execute(total_sales_query)
    total_sales = total_sales_result.scalar() or 0
    
    # 获取已发货订单数
    shipped_query = select(func.count(Order.id)).filter(
        Order.shipping_status == "shipped",
        Order.created_at >= start_date
    )
    shipped_result = await db.execute(shipped_query)
    shipped_orders = shipped_result.scalar() or 0
    
    # 获取待发货订单数
    pending_query = select(func.count(Order.id)).filter(
        Order.shipping_status == "pending",
        Order.created_at >= start_date
    )
    pending_result = await db.execute(pending_query)
    pending_orders = pending_result.scalar() or 0
    
    # 获取生产中订单数
    producing_query = select(func.count(Order.id)).filter(
        Order.produce_status == "producing",
        Order.created_at >= start_date
    )
    producing_result = await db.execute(producing_query)
    producing_orders = producing_result.scalar() or 0
    
    # 获取虚拟发货订单数
    virtual_query = select(func.count(Order.id)).filter(
        Order.shipping_status.in_(["virtual", "virtual_shipped"]),
        Order.created_at >= start_date
    )
    virtual_result = await db.execute(virtual_query)
    virtual_orders = virtual_result.scalar() or 0
    
    # 计算发货率
    shipped_percentage = round((shipped_orders / total_orders) * 100, 1) if total_orders > 0 else 0
    
    # 判断待发货预警（待发货超过100单触发预警）
    pending_warning = pending_orders > 100
    
    return {
        "total_orders": total_orders,
        "total_sales": round(total_sales, 2),
        "shipped_orders": shipped_orders,
        "pending_orders": pending_orders,
        "producing_orders": producing_orders,
        "virtual_orders": virtual_orders,
        "shipped_percentage": shipped_percentage,
        "pending_warning": pending_warning,
        "update_time": beijing_now().isoformat()
    }

# ==================== 销售排行榜 ====================
@router.get("/sales-ranking")
async def get_dashboard_sales_ranking(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取智慧大屏销售排行榜数据
    - 按销售额排名
    - 仅boss角色可访问
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

# ==================== 财务汇总 ====================
@router.get("/finance-summary")
async def get_dashboard_finance_summary(
    period: str = Query("month", enum=["week", "month", "quarter", "year"]),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取智慧大屏财务汇总数据
    - 仅boss角色可访问
    """
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="权限不足，仅老板端可访问")
    
    end_date = datetime.now()
    if period == "week":
        start_date = end_date - timedelta(weeks=1)
    elif period == "month":
        start_date = end_date - timedelta(days=30)
    elif period == "quarter":
        start_date = end_date - timedelta(days=90)
    else:
        start_date = end_date - timedelta(days=365)
    
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
    
    # 真实月度营收趋势：取最近 12 个自然月，按订单创建时间(北京时间)聚合真实销售额
    trend_data = []
    try:
        trend_start = end_date - timedelta(days=365)
        trend_query = select(
            func.strftime('%Y-%m', Order.created_at).label("ym"),
            func.sum(func.cast(Order.sales_amount, Float)).label("revenue")
        ).filter(
            Order.created_at >= trend_start,
            Order.created_at <= end_date
        ).group_by("ym")
        trend_rows = (await db.execute(trend_query)).all()
        revenue_by_month = {r.ym: (r.revenue or 0) for r in trend_rows}
        # 组装最近 12 个自然月（含当月），未产生订单的月份营收为 0
        first_of_this_month = end_date.replace(day=1)
        for i in range(11, -1, -1):
            year = first_of_this_month.year
            month = first_of_this_month.month - i
            while month <= 0:
                year -= 1
                month += 12
            key = f"{year:04d}-{month:02d}"
            trend_data.append({
                "period": f"{month}月",
                "revenue": round(revenue_by_month.get(key, 0.0), 2)
            })
    except Exception:
        # 聚合失败时返回空趋势，避免整个接口报错（保留 total 数据）
        trend_data = []

    return {
        "total_revenue": round(total_revenue, 2),
        "order_count": order_count,
        "avg_order_value": avg_order_value,
        "period": period,
        "trend_data": trend_data,
        "update_time": beijing_now().isoformat()
    }

# ==================== 销售业绩详情 ====================
@router.get("/sales-performance")
async def get_dashboard_sales_performance(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取智慧大屏销售业绩详情数据
    - 仅boss角色可访问
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
            "rank": "senior" if (row.commission_rate or 0) >= 0.05 else "middle" if (row.commission_rate or 0) >= 0.03 else "junior"
        })
    
    return {
        "data": performance_data,
        "update_time": beijing_now().isoformat()
    }

# ==================== 商品排行榜 ====================
@router.get("/product-ranking")
async def get_dashboard_product_ranking(
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取智慧大屏商品热销排行榜数据
    - 仅boss角色可访问
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
            # 真实可算指标：客单价（该商品总销售额 ÷ 订单数），替代原伪随机利润率
            "avg_order_value": round((row.total_revenue or 0) / row.sales_count, 2) if row.sales_count else 0
        })
    
    return {
        "data": product_ranking,
        "update_time": beijing_now().isoformat()
    }


# ==================== 月度销售趋势 ====================
@router.get("/monthly-sales")
async def get_dashboard_monthly_sales(
    months: int = Query(24, ge=3, le=60),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取智慧大屏月度销售趋势
    - 按月汇总销售额
    - 仅boss角色可访问
    """
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="权限不足，仅老板端可访问")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30 * months)
    
    # 构造最近N个月的月份列表
    result = []
    for i in range(months - 1, -1, -1):
        month_date = end_date - timedelta(days=30 * i)
        year = month_date.year
        month = month_date.month
        result.append({
            "year": year,
            "month": month,
            "period": f"{year}-{month:02d}",
            "label": f"{month}月",
            "sales": 0
        })
    
    # 从数据库按月聚合销售额
    query = select(
        func.strftime("%Y-%m", Order.created_at).label("period"),
        func.sum(func.cast(Order.sales_amount, Float)).label("total_sales")
    ).filter(
        Order.created_at >= start_date
    ).group_by(
        func.strftime("%Y-%m", Order.created_at)
    ).order_by(
        func.strftime("%Y-%m", Order.created_at)
    )
    
    db_result = await db.execute(query)
    sales_map = {row.period: row.total_sales or 0 for row in db_result.all()}
    
    # 回填数据
    for item in result:
        item["sales"] = round(sales_map.get(item["period"], 0), 2)
    
    return {
        "data": result,
        "update_time": beijing_now().isoformat()
    }


# ==================== 网店销售排行 ====================
@router.get("/shop-ranking")
async def get_dashboard_shop_ranking(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取智慧大屏网店销售排行
    - 按网店销售额排名
    - 仅boss角色可访问
    """
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="权限不足，仅老板端可访问")
    
    # 子查询：按 shop_id 聚合销售额和订单数
    shop_sales_subquery = select(
        Order.shop_id.label("shop_id"),
        func.count(Order.id).label("order_count"),
        func.sum(func.cast(Order.sales_amount, Float)).label("total_sales")
    ).filter(
        Order.shop_id.isnot(None),
        Order.shop_id != ""
    ).group_by(
        Order.shop_id
    ).subquery()
    
    query = select(
        Shop.shop_id,
        Shop.shop_name,
        Shop.shop_account,
        User.real_name,
        shop_sales_subquery.c.order_count,
        shop_sales_subquery.c.total_sales
    ).select_from(Shop).join(
        shop_sales_subquery, Shop.shop_id == shop_sales_subquery.c.shop_id, isouter=True
    ).join(
        User, User.username == Shop.creator, isouter=True
    ).order_by(
        desc(shop_sales_subquery.c.total_sales)
    ).limit(limit)
    
    result = await db.execute(query)
    rows = result.all()
    
    shop_ranking = []
    for index, row in enumerate(rows):
        shop_ranking.append({
            "rank": index + 1,
            "real_name": row.real_name or "—",
            "shop_id": row.shop_id or "未知",
            "shop_name": row.shop_name or "未知网店",
            "shop_account": row.shop_account or "—",
            "order_count": row.order_count or 0,
            "total_sales": round(row.total_sales or 0, 2)
        })
    
    return {
        "data": shop_ranking,
        "update_time": beijing_now().isoformat()
    }


# ==================== 超期订单 ====================
@router.get("/overdue-orders")
async def get_dashboard_overdue_orders(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取智慧大屏超期订单
    - 统计未发货和虚拟发货订单，从下单时间到当前的时间差
    - 仅boss角色可访问
    """
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="权限不足，仅老板端可访问")
    
    now = datetime.now()
    
    query = select(
        Order.order_id,
        Order.platform_order_no,
        Order.created_at,
        Order.shipping_status,
        Order.shop_id,
        Order.product_name,
        Order.sales_amount
    ).filter(
        Order.shipping_status.in_(["pending", "virtual", "virtual_shipped"])
    ).order_by(
        # 下单越早 = 超期越久，升序取最超期的前 N 条
        asc(Order.created_at)
    ).limit(limit)
    
    result = await db.execute(query)
    rows = result.all()
    
    overdue_orders = []
    for row in rows:
        created_at = row.created_at
        if created_at and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=now.tzinfo)
        else:
            created_at = created_at or now
        
        diff = now - created_at
        overdue_days = diff.days
        overdue_hours = diff.seconds // 3600
        
        # 友好显示（下单时长精确到天）
        overdue_text = f"{overdue_days}天"
        
        overdue_orders.append({
            "order_id": row.order_id,
            "platform_order_no": row.platform_order_no,
            "created_at": created_at.strftime("%Y-%m-%d %H:%M") if created_at else "-",
            "shipping_status": row.shipping_status,
            "shipping_status_text": "待发货" if row.shipping_status == "pending" else "虚拟发货",
            "shop_id": row.shop_id,
            "product_name": row.product_name or "-",
            "sales_amount": row.sales_amount or 0,
            "overdue_days": overdue_days,
            "overdue_hours": overdue_hours,
            "overdue_text": overdue_text
        })
    
    # 按超期时长从大到小排序（下单越早越靠前）
    overdue_orders.sort(key=lambda x: x["overdue_days"], reverse=True)

    return {
        "data": overdue_orders,
        "update_time": beijing_now().isoformat()
    }

# ==================== 国家分布（离线识别收货地址所属国家） ====================
import re

# 离线双语国家词典：en=英文标准名，cn=中文显示名，aliases=所有可匹配文本（中/英/别名），
# coord=[经度, 纬度] 为国家质心，用于地图打点。台湾/香港/澳门按一个中国原则归入中国。
COUNTRY_DICT = [
    {"en": "China", "cn": "中国", "aliases": ["中国", "中國", "中国大陆", "中华人民共和国", "内地", "中国台湾", "台湾", "台湾省", "中国香港", "香港", "中国澳门", "澳门", "China", "CN", "P.R.China", "PRC", "중국", "Chine", "Китай", "الصين"], "coord": [104.1954, 35.8617]},
    {"en": "United States", "cn": "美国", "aliases": ["美国", "美國", "United States", "USA", "U.S.A.", "US", "U.S.", "America", "United States of America", "アメリカ", "미국", "États-Unis", "Vereinigte Staaten", "Estados Unidos", "США", "Соединённые Штаты", "الولايات المتحدة", "أمريكا"], "coord": [-98.5833, 39.8333]},
    {"en": "United Kingdom", "cn": "英国", "aliases": ["英国", "英國", "United Kingdom", "UK", "U.K.", "Britain", "England", "Great Britain", "イギリス", "영국", "Royaume-Uni", "Vereinigtes Königreich", "Reino Unido", "Великобритания", "المملكة المتحدة", "بريطانيا"], "coord": [-1.5, 52.5]},
    {"en": "Germany", "cn": "德国", "aliases": ["德国", "德國", "Germany", "DE", "Deutschland", "ドイツ", "독일", "Allemagne", "Alemania", "Германия", "ألمانيا"], "coord": [10.4515, 51.1657]},
    {"en": "France", "cn": "法国", "aliases": ["法国", "法國", "France", "FR", "フランス", "프랑스", "Frankreich", "Francia", "Франция", "فرنسا"], "coord": [2.2137, 46.2276]},
    {"en": "Japan", "cn": "日本", "aliases": ["日本", "日本国", "Japan", "JP", "Nippon", "ニッポン", "일본", "Japon", "Japan", "Япония", "اليابان"], "coord": [138.2529, 36.2048]},
    {"en": "South Korea", "cn": "韩国", "aliases": ["韩国", "韓國", "South Korea", "Korea", "Republic of Korea", "KR", "한국", "대한민국", "Corée du Sud", "Südkorea", "Corea del Sur", "Южная Корея", "كوريا الجنوبية"], "coord": [127.7669, 35.9078]},
    {"en": "Australia", "cn": "澳大利亚", "aliases": ["澳大利亚", "澳洲", "Australia", "AU", "オーストラリア", "호주", "Australie", "Australien", "Australia", "Австралия", "أستراليا"], "coord": [133.7751, -25.2744]},
    {"en": "Canada", "cn": "加拿大", "aliases": ["加拿大", "加拿大國", "Canada", "CA", "カナダ", "캐나다", "Kanada", "Canadá", "Канада", "كندا"], "coord": [-106.3468, 56.1304]},
    {"en": "Italy", "cn": "意大利", "aliases": ["意大利", "義大利", "Italy", "IT", "イタリア", "이탈리아", "Italie", "Italien", "Italia", "Италия", "إيطاليا"], "coord": [12.5674, 41.8719]},
    {"en": "Spain", "cn": "西班牙", "aliases": ["西班牙", "西班牙國", "Spain", "ES", "España", "スペイン", "스페인", "Espagne", "Spanien", "España", "Испания", "إسبانيا"], "coord": [-3.7492, 40.4637]},
    {"en": "Netherlands", "cn": "荷兰", "aliases": ["荷兰", "荷蘭", "Netherlands", "Holland", "NL", "The Netherlands", "オランダ", "네덜란드", "Pays-Bas", "Niederlande", "Países Bajos", "Нидерланды", "هولندا"], "coord": [5.2913, 52.1326]},
    {"en": "Russia", "cn": "俄罗斯", "aliases": ["俄罗斯", "俄羅斯", "Russia", "RU", "Russian Federation", "ロシア", "러시아", "Russie", "Russland", "Rusia", "Россия", "روسيا"], "coord": [105.3188, 61.5240]},
    {"en": "Brazil", "cn": "巴西", "aliases": ["巴西", "巴西聯邦共和國", "Brazil", "BR", "Brasil", "ブラジル", "브라질", "Brésil", "Brasilien", "Brasil", "Бразилия", "البرازيل"], "coord": [-51.9253, -14.2350]},
    {"en": "Mexico", "cn": "墨西哥", "aliases": ["墨西哥", "墨西哥合眾國", "Mexico", "MX", "México", "メキシコ", "멕시코", "Mexique", "Mexiko", "México", "Мексика", "المكسيك"], "coord": [-102.5528, 23.6345]},
    {"en": "India", "cn": "印度", "aliases": ["印度", "印度共和國", "India", "IN", "Bharat", "インド", "인도", "Inde", "Indien", "India", "Индия", "الهند"], "coord": [78.9629, 20.5937]},
    {"en": "Thailand", "cn": "泰国", "aliases": ["泰国", "泰國", "Thailand", "TH", "タイ", "태국", "Thaïlande", "Thailand", "Tailandia", "Таиланд", "تايلاند"], "coord": [100.9925, 15.8700]},
    {"en": "Singapore", "cn": "新加坡", "aliases": ["新加坡", "Singapore", "SG", "シンガポール", "싱가포르", "Singapour", "Singapur", "Singapur", "Сингапур", "سنغافورة"], "coord": [103.8198, 1.3521]},
    {"en": "Malaysia", "cn": "马来西亚", "aliases": ["马来西亚", "馬來西亞", "Malaysia", "MY", "マレーシア", "말레이시아", "Malaisie", "Malaysia", "Malasia", "Малайзия", "ماليزيا"], "coord": [101.9758, 4.2105]},
    {"en": "Vietnam", "cn": "越南", "aliases": ["越南", "越南社會主義共和國", "Vietnam", "VN", "ベトナム", "베트남", "Viêt Nam", "Vietnam", "Vietnam", "Вьетнам", "فيتنام"], "coord": [108.2772, 14.0583]},
    {"en": "Indonesia", "cn": "印度尼西亚", "aliases": ["印度尼西亚", "印尼", "Indonesia", "ID", "インドネシア", "인도네시아", "Indonésie", "Indonesien", "Indonesia", "Индонезия", "إندونيسيا"], "coord": [113.9213, -0.7893]},
    {"en": "Philippines", "cn": "菲律宾", "aliases": ["菲律宾", "菲律賓", "Philippines", "PH", "フィリピン", "필리핀", "Philippines", "Philippinen", "Filipinas", "Филиппины", "الفلبين"], "coord": [121.7740, 12.8797]},
    {"en": "United Arab Emirates", "cn": "阿联酋", "aliases": ["阿联酋", "阿拉伯联合酋长国", "迪拜", "United Arab Emirates", "UAE", "Dubai", "الإمارات العربية المتحدة", "إمارات", "ОАЭ", "Объединённые Арабские Эмираты", "아랍에미리트"], "coord": [53.8478, 23.4241]},
    {"en": "Saudi Arabia", "cn": "沙特阿拉伯", "aliases": ["沙特阿拉伯", "沙特", "Saudi Arabia", "Saudi", "SA", "السعودية", "サウジアラビア", "사우디아라비아", "Arabie saoudite", "Saudi-Arabien", "Arabia Saudita", "Саудовская Аравия"], "coord": [45.0792, 23.8859]},
    {"en": "Turkey", "cn": "土耳其", "aliases": ["土耳其", "土耳其共和國", "Turkey", "TR", "Türkiye", "トルコ", "터키", "Turquie", "Türkei", "Turquía", "Турция", "تركيا"], "coord": [35.2433, 38.9637]},
    {"en": "Poland", "cn": "波兰", "aliases": ["波兰", "波蘭", "Poland", "PL", "ポーランド", "폴란드", "Pologne", "Polen", "Polonia", "Польша", "بولندا"], "coord": [19.1451, 51.9194]},
    {"en": "Sweden", "cn": "瑞典", "aliases": ["瑞典", "瑞典國", "Sweden", "SE", "スウェーデン", "스웨덴", "Suède", "Schweden", "Suecia", "Швеция", "السويد"], "coord": [18.6435, 60.1282]},
    {"en": "Norway", "cn": "挪威", "aliases": ["挪威", "挪威王國", "Norway", "NO", "ノルウェー", "노르웨이", "Norvège", "Norwegen", "Noruega", "Норвегия", "النرويج"], "coord": [8.4689, 60.4720]},
    {"en": "Switzerland", "cn": "瑞士", "aliases": ["瑞士", "瑞士聯邦", "Switzerland", "CH", "スイス", "스위스", "Suisse", "Schweiz", "Suiza", "Швейцария", "سويسرا"], "coord": [8.5417, 46.8182]},
    {"en": "Belgium", "cn": "比利时", "aliases": ["比利时", "比利時", "Belgium", "BE", "ベルギー", "벨기에", "Belgique", "Belgien", "Bélgica", "Бельгия", "بلجيكا"], "coord": [4.4699, 50.5039]},
    {"en": "Austria", "cn": "奥地利", "aliases": ["奥地利", "奧地利", "Austria", "AT", "オーストリア", "오스트리아", "Autriche", "Österreich", "Austria", "Австрия", "النمسا"], "coord": [14.5501, 47.5162]},
    {"en": "Portugal", "cn": "葡萄牙", "aliases": ["葡萄牙", "葡萄牙共和國", "Portugal", "PT", "ポルトガル", "포르투갈", "Portugal", "Portugal", "Portugal", "Португалия", "البرتغال"], "coord": [-8.2245, 39.3999]},
    {"en": "Greece", "cn": "希腊", "aliases": ["希腊", "希臘", "Greece", "GR", "ギリシャ", "그리스", "Grèce", "Griechenland", "Grecia", "Греция", "اليونان"], "coord": [21.8243, 39.0742]},
    {"en": "Ireland", "cn": "爱尔兰", "aliases": ["爱尔兰", "愛爾蘭", "Ireland", "IE", "アイルランド", "아일랜드", "Irlande", "Irland", "Irlanda", "Ирландия", "أيرلندا"], "coord": [-8.2439, 53.4129]},
    {"en": "Denmark", "cn": "丹麦", "aliases": ["丹麦", "丹麥", "Denmark", "DK", "デンマーク", "덴마크", "Danemark", "Dänemark", "Dinamarca", "Дания", "الدنمارك"], "coord": [9.5018, 56.2639]},
    {"en": "Finland", "cn": "芬兰", "aliases": ["芬兰", "芬蘭", "Finland", "FI", "フィンランド", "핀란드", "Finlande", "Finnland", "Finlandia", "Финляндия", "فنلندا"], "coord": [25.7482, 61.9241]},
    {"en": "Czech Republic", "cn": "捷克", "aliases": ["捷克", "捷克共和國", "Czech Republic", "Czechia", "CZ", "チェコ", "체코", "Tchéquie", "Tschechien", "República Checa", "Чехия", "التشيك"], "coord": [15.4730, 49.8175]},
    {"en": "Hungary", "cn": "匈牙利", "aliases": ["匈牙利", "匈牙利共和國", "Hungary", "HU", "ハンガリー", "헝가리", "Hongrie", "Ungarn", "Hungría", "Венгрия", "المجر"], "coord": [47.1625, 48.9821]},
    {"en": "Romania", "cn": "罗马尼亚", "aliases": ["罗马尼亚", "羅馬尼亞", "Romania", "RO", "ルーマニア", "루마니아", "Roumanie", "Rumänien", "Rumanía", "Румыния", "رومانيا"], "coord": [24.9668, 45.9432]},
    {"en": "Ukraine", "cn": "乌克兰", "aliases": ["乌克兰", "烏克蘭", "Ukraine", "UA", "ウクライナ", "우크라이나", "Ukraine", "Ukraine", "Ucrania", "Украина", "أوكرانيا"], "coord": [31.1656, 48.3794]},
    {"en": "South Africa", "cn": "南非", "aliases": ["南非", "南非共和國", "South Africa", "ZA", "南アフリカ", "남아프리카공화국", "Afrique du Sud", "Südafrika", "Sudáfrica", "Южная Африка", "جنوب أفريقيا"], "coord": [22.9375, -30.5595]},
    {"en": "Egypt", "cn": "埃及", "aliases": ["埃及", "埃及阿拉伯共和國", "Egypt", "EG", "مصر", "エジプト", "이집트", "Égypte", "Ägypten", "Egipto", "Египет", "مصر"], "coord": [30.8025, 26.8206]},
    {"en": "Nigeria", "cn": "尼日利亚", "aliases": ["尼日利亚", "尼日利亞", "Nigeria", "NG", "ナイジェリア", "나이지리아", "Nigéria", "Nigeria", "Nigeria", "Нигерия", "نيجيريا"], "coord": [8.6753, 9.0820]},
    {"en": "Chile", "cn": "智利", "aliases": ["智利", "智利共和國", "Chile", "CL", "チリ", "칠레", "Chili", "Chile", "Chile", "Чили", "تشيلي"], "coord": [-71.5430, -35.6751]},
    {"en": "Argentina", "cn": "阿根廷", "aliases": ["阿根廷", "阿根廷共和國", "Argentina", "AR", "アルゼンチン", "아르헨티나", "Argentine", "Argentinien", "Argentina", "Аргентина", "الأرجنتين"], "coord": [-63.6167, -38.4161]},
    {"en": "Colombia", "cn": "哥伦比亚", "aliases": ["哥伦比亚", "哥倫比亞", "Colombia", "CO", "コロンビア", "콜롬비아", "Colombie", "Kolumbien", "Colombia", "Колумбия", "كولومبيا"], "coord": [-74.2973, 4.5709]},
    {"en": "New Zealand", "cn": "新西兰", "aliases": ["新西兰", "紐西蘭", "New Zealand", "NZ", "ニュージーランド", "뉴질랜드", "Nouvelle-Zélande", "Neuseeland", "Nueva Zelanda", "Новая Зеландия", "نيوزيلندا"], "coord": [174.8860, -40.9006]},
    {"en": "Israel", "cn": "以色列", "aliases": ["以色列", "以色列國", "Israel", "IL", "イスラエル", "이스라엘", "Israël", "Israel", "Israel", "Израиль", "إسرائيل"], "coord": [34.8516, 31.0461]},
    {"en": "Lebanon", "cn": "黎巴嫩", "aliases": ["黎巴嫩", "黎巴嫩共和国", "Lebanon", "Lebanese Republic", "لبنان", "لبنان الجمهورية", "レバノン", "레바논", "Liban", "Libanon", "Líbano", "Ливан"], "coord": [35.8623, 33.8547]},
    {"en": "Jordan", "cn": "约旦", "aliases": ["约旦", "约旦哈希姆王国", "Jordan", "Hashemite Kingdom of Jordan", "الأردن", "الاردن", "ヨルダン", "요르단", "Jordanie", "Jordanien", "Jordania", "Иордания"], "coord": [36.2384, 30.5852]},
    {"en": "Syria", "cn": "叙利亚", "aliases": ["叙利亚", "敘利亞", "叙利亚阿拉伯共和国", "Syria", "Syrian Arab Republic", "سوريا", "シリア", "시리아", "Syrie", "Syrien", "Siria", "Сирия"], "coord": [38.9968, 34.8021]},
    {"en": "Iraq", "cn": "伊拉克", "aliases": ["伊拉克", "伊拉克共和国", "Iraq", "Republic of Iraq", "العراق", "イラク", "이라크", "Irak", "Irak", "Irak", "Ирак"], "coord": [43.6793, 33.2232]},
    {"en": "Kuwait", "cn": "科威特", "aliases": ["科威特", "科威特国", "Kuwait", "State of Kuwait", "الكويت", "クウェート", "쿠웨이트", "Koweït", "Kuwait", "Kuwait", "Кувейт"], "coord": [47.4818, 29.3117]},
    {"en": "Qatar", "cn": "卡塔尔", "aliases": ["卡塔尔", "卡達爾", "Qatar", "State of Qatar", "قطر", "カタール", "카타르", "Qatar", "Katar", "Catar", "Катар"], "coord": [51.1839, 25.3548]},
    {"en": "Bahrain", "cn": "巴林", "aliases": ["巴林", "巴林王国", "Bahrain", "Kingdom of Bahrain", "البحرين", "バーレーン", "바레인", "Bahreïn", "Bahrain", "Baréin", "Бахрейн"], "coord": [50.5577, 26.0667]},
    {"en": "Oman", "cn": "阿曼", "aliases": ["阿曼", "阿曼苏丹国", "Oman", "Sultanate of Oman", "عُمان", "オマーン", "오만", "Oman", "Oman", "Omán", "Оман"], "coord": [56.0968, 21.4735]},
    {"en": "Yemen", "cn": "也门", "aliases": ["也门", "葉門", "也门共和国", "Yemen", "Republic of Yemen", "اليمن", "イエメン", "예멘", "Yémen", "Jemen", "Yemen", "Йемен"], "coord": [47.8495, 15.5527]},
    {"en": "Palestine", "cn": "巴勒斯坦", "aliases": ["巴勒斯坦", "巴勒斯坦国", "Palestine", "State of Palestine", "فلسطين", "パレスチナ", "팔레스타인", "Palestine", "Palästina", "Palestina", "Палестина"], "coord": [35.2332, 31.9522]},
    {"en": "Cyprus", "cn": "塞浦路斯", "aliases": ["塞浦路斯", "塞普勒斯", "Cyprus", "Republic of Cyprus", "قبرص", "キプロス", "키프로스", "Chypre", "Zypern", "Chipre", "Кипр"], "coord": [33.4299, 35.1264]},
    {"en": "Iran", "cn": "伊朗", "aliases": ["伊朗", "伊朗伊斯兰共和国", "Iran", "Islamic Republic of Iran", "ايران", "إيران", "イラン", "이란", "Iran", "Iran", "Irán", "Иран"], "coord": [53.6880, 32.4279]},
]


# 剔除「纯两位拉丁字母」的别名（多为两位ISO国家代码）。这些短码一旦遇到翻译成英文的
# 地址/搜索摘要，极易与英文常见词或美国州缩写碰撞造成误判（IN→in、IT→it、AT→at、
# NO→no、BE→be、US→us、MY→my、CA→California、CO→Colorado 等）。
# 注意：仅剔除拉丁短码，保留中文两位国名（美国/日本/英国…）与三位及以上代码（USA/UAE/PRC）。
# 另剔除易与洲/地区名碰撞的别名（America→South America、England→New England）。
_DANGEROUS_ALIASES = {"America", "England"}
for _entry in COUNTRY_DICT:
    _entry["aliases"] = [
        a for a in _entry["aliases"]
        if not (a.strip().isascii() and a.strip().isalpha() and len(a.strip()) <= 2)
        and a not in _DANGEROUS_ALIASES
    ]


def _is_ascii(token):
    return bool(re.match(r'^[A-Za-z0-9\s\.]+$', token))


def _build_country_matcher():
    """构建国家识别正则与 token->国家 映射（最长匹配优先）"""
    tokens = []
    token_to_entry = {}
    for entry in COUNTRY_DICT:
        for alias in entry["aliases"]:
            tokens.append(alias)
            key = alias.lower() if _is_ascii(alias) else alias
            token_to_entry[key] = entry
    # 按 token 长度降序，保证更长的国家名优先匹配
    tokens.sort(key=len, reverse=True)
    patterns = []
    for token in tokens:
        esc = re.escape(token)
        if _is_ascii(token):
            patterns.append(r'\b' + esc + r'\b')
        else:
            patterns.append(esc)
    regex = re.compile('|'.join(patterns), re.IGNORECASE)
    return regex, token_to_entry


_COUNTRY_REGEX, _TOKEN_TO_ENTRY = _build_country_matcher()

# cn(中文名) -> 国家条目，供聚合时反查坐标/英文名
_CN_TO_ENTRY = {entry["cn"]: entry for entry in COUNTRY_DICT}


def detect_country(address):
    """从收货地址文本中离线识别所属国家，返回国家条目或 None（识别不到直接丢弃）"""
    if not address:
        return None
    m = _COUNTRY_REGEX.search(address)
    if not m:
        return None
    matched = m.group(0)
    key = matched.lower() if _is_ascii(matched) else matched
    return _TOKEN_TO_ENTRY.get(key)


def resolve_country(address):
    """从收货地址文本中离线识别所属国家：仅本地多语言词典匹配，不发起任何网络请求，
    客户地址不会外发到任何第三方服务。返回国家条目(dict)；识别不到返回 None。"""
    if not address:
        return None
    return detect_country(address)


# ── 国家分布计算的保护层 ──
# 结果缓存：大屏每 3 分钟刷新一次，缓存 TTL 略小于刷新间隔，避免每次刷新重复计算
_country_cache = {"data": None, "update_time": None, "ts": 0.0}
_COUNTRY_CACHE_TTL = 150  # 秒
# 同一时刻只允许一个计算过程（防止多用户/多标签并发）
_country_compute_lock = asyncio.Lock()


async def _resolve_one(address):
    """单笔地址离线识别：本地词典匹配，不联网、不阻塞事件循环。返回国家条目或 None。"""
    try:
        return resolve_country(address)
    except Exception:
        return None  # 任何异常 -> 视为识别不到


@router.get("/country-distribution")
async def get_country_distribution(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user)
):
    """
    按收货地址识别国家，聚合每个国家的订单分布。
    识别链路（对操作员透明、无感知）：离线多语言词典 -> 联网翻译 -> 联网搜索。
    结果持久化到 Order.detected_country：NULL=未计算, ""=识别不到(丢弃), 其他=国家中文名。
    - 仅boss角色可访问
    """
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="权限不足，仅老板端可访问")

    # 命中近期缓存则直接返回，避免重复触发联网识别（大屏频繁刷新/多标签并发）
    if _country_cache["data"] is not None and (time.time() - _country_cache["ts"]) < _COUNTRY_CACHE_TTL:
        return {
            "data": _country_cache["data"],
            "update_time": _country_cache["update_time"],
            "cached": True,
        }

    # 同一时刻只允许一个计算过程，其余请求复用同一份结果（防线程风暴）
    async with _country_compute_lock:
        # 等待锁期间可能已被其他协程算好，二次检查
        if _country_cache["data"] is not None and (time.time() - _country_cache["ts"]) < _COUNTRY_CACHE_TTL:
            return {
                "data": _country_cache["data"],
                "update_time": _country_cache["update_time"],
                "cached": True,
            }

        result = await db.execute(
            select(
                Order.id,
                Order.receiver_address,
                Order.sales_amount,
                Order.shipping_status,
                Order.detected_country,
            )
        )
        rows = result.all()

        agg = {}
        dirty = []  # 本次新计算且需写回的值：(order_id, detected_country)
        for order_id, address, amount, shipping_status, detected in rows:
            resolved_now = False
            if detected is None:
                # 首次计算：本地离线词典识别（不发起任何网络请求）
                res = await _resolve_one(address)
                detected = res["cn"] if res else ""
                resolved_now = True
            if not detected:
                continue  # 识别不到国家 -> 丢弃（"" 与 None 均跳过）
            if resolved_now:
                dirty.append((order_id, detected))

            key = detected
            if key not in agg:
                entry0 = _CN_TO_ENTRY.get(key)
                agg[key] = {
                    "country_cn": key,
                    "country_en": entry0["en"] if entry0 else key,
                    "coord": entry0["coord"] if entry0 else [0, 0],
                    "total_amount": 0.0,
                    "total_count": 0,
                    "shipped_count": 0,
                }
            item = agg[key]
            item["total_count"] += 1
            try:
                item["total_amount"] += float(amount or 0)
            except (ValueError, TypeError):
                pass
            if shipping_status == "shipped":
                item["shipped_count"] += 1

        # 将本次新识别结果写回数据库，避免每次刷新重复联网
        if dirty:
            for order_id, val in dirty:
                await db.execute(
                    update(Order).where(Order.id == order_id).values(detected_country=val)
                )
            await db.commit()

        data = []
        for item in agg.values():
            item["unshipped_count"] = item["total_count"] - item["shipped_count"]
            item["total_amount"] = round(item["total_amount"], 2)
            data.append(item)

        # 按订单金额降序
        data.sort(key=lambda x: x["total_amount"], reverse=True)

        update_time = beijing_now().isoformat()
        _country_cache["data"] = data
        _country_cache["update_time"] = update_time
        _country_cache["ts"] = time.time()

        return {
            "data": data,
            "update_time": update_time,
            "cached": False,
        }