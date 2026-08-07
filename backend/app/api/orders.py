# -*- coding: utf-8 -*-
import hashlib
import os
import uuid
import qrcode
from io import BytesIO
from datetime import datetime, timedelta
from ..models.models import beijing_now
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, String
from typing import List, Optional
from ..core.database import get_db
from ..core.security import get_current_active_user, verify_password
from ..core.config import TEMP_DIR, OFFICIAL_DIR
from ..api.images import sanitize_path_component
from ..models.models import Order, Shop, User, Product, Image as ImageModel, OperationLog
from ..schemas.schemas import OrderCreate, OrderUpdate, OrderResponse
from ..utils.order_id_generator import order_id_generator
from ..services.notification_service import NotificationService
from ..api.settings import read_setting

router = APIRouter(prefix="/api/orders", tags=["订单管理"])

# 定义删除订单的请求体模型
class DeleteOrderRequest(BaseModel):
    password: str

def calculate_order_days(order_date: datetime) -> int:
    """
    计算订单滞留天数（自然日计算）
    计算规则：当前自然日 - 订单下单自然日
    返回纯整数天数，无小数
    """
    if not order_date:
        return 0
    # 获取当前时间的自然日（归零时分秒）
    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day)
    # 获取订单时间的自然日（归零时分秒）
    order_date_start = datetime(order_date.year, order_date.month, order_date.day)
    # 计算天数差
    days_diff = (today_start - order_date_start).days
    return max(0, days_diff)

# 已发货 / 已退款后，下单时长冻结不再变化
_FROZEN_DAYS_STATUSES = ("shipped", "refunded")

def effective_order_days(order) -> int:
    """
    下单时长（滞留天数）展示值：
    - 未发货（pending/virtual/virtual_shipped 等）：实时计算，随日期推移自动增长；
    - 已发货 / 已退款：返回冻结值（数据库保存的数值），不再随时间变化。
    """
    if getattr(order, "shipping_status", None) in _FROZEN_DAYS_STATUSES:
        return order.order_days if order.order_days is not None else 0
    created = getattr(order, "created_at", None)
    if created is None:
        return order.order_days or 0
    if isinstance(created, str):
        try:
            created = datetime.fromisoformat(str(created).replace("Z", "+00:00").split("+")[0])
        except ValueError:
            return order.order_days or 0
    return calculate_order_days(created)

async def generate_order_id(username: str, shop_account: str, platform_order_no: str) -> str:
    date_str = beijing_now().strftime("%Y%m%d")
    random_num = order_id_generator.get_random_number()
    # 按照要求生成订单ID：登录账号 + 年月日 + 网店ID（shop_account） + 平台订单号 + 6位随机数字
    order_id = f"{username}{date_str}{shop_account}{platform_order_no}{random_num}"
    return order_id

def generate_qr_code(content: str) -> bytes:
    """生成二维码并返回字节数据"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(content)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer.getvalue()

@router.get("/generate-preview")
async def generate_order_preview(
    shop_id: str,
    platform_order_no: str = "",
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    if current_user.role not in ["boss", "sales"]:
        raise HTTPException(status_code=403, detail="您没有权限创建订单")

    # 验证shop_id是否存在
    result = await db.execute(select(Shop).where(Shop.shop_id == shop_id))
    shop = result.scalar_one_or_none()
    if not shop:
        raise HTTPException(status_code=404, detail="网店不存在")

    order_id = await generate_order_id(current_user.username, shop.shop_account, platform_order_no)
    qr_code = generate_qr_code(order_id)

    return StreamingResponse(
        BytesIO(qr_code),
        media_type="image/png",
        headers={"Content-Disposition": f"inline; filename=qr_{order_id}.png"}
    )


async def calc_order_gross_profit(product_name, sales_amount, db: AsyncSession):
    """计算订单毛利 = 销售金额 - 商品成本价（products 表按商品名匹配，取第一条）。
    商品未匹配或未填成本价按 0；销售金额为空/非数字按 0。返回 float 或 None。
    """
    try:
        sales = float(sales_amount or 0)
    except (TypeError, ValueError):
        return None
    try:
        pr = await db.execute(
            select(Product).where(Product.product_name == (product_name or "")).limit(1)
        )
        prod = pr.scalar_one_or_none()
        cost = float(prod.cost_price) if prod and prod.cost_price is not None else 0.0
    except Exception:
        cost = 0.0
    return round(sales - cost, 2)

@router.post("/", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    try:
        if current_user.role not in ["boss", "sales"]:
            raise HTTPException(status_code=403, detail="您没有权限创建订单")

        result = await db.execute(select(Shop).where(Shop.shop_id == order_data.shop_id))
        shop = result.scalar_one_or_none()
        if not shop:
            raise HTTPException(status_code=400, detail="网店不存在")

        if shop.status == "closed":
            raise HTTPException(status_code=400, detail="该网店已关店，无法创建订单")

        result = await db.execute(
            select(Order).where(Order.platform_order_no == order_data.platform_order_no)
        )
        existing_order = result.scalar_one_or_none()
        if existing_order:
            raise HTTPException(status_code=400, detail="该平台订单号已存在")

        order_id = await generate_order_id(current_user.username, shop.shop_account, order_data.platform_order_no)

        commission_amount = None
        if order_data.sales_amount and current_user.commission_rate:
            try:
                sales = float(order_data.sales_amount)
                rate = current_user.commission_rate
                commission_amount = str(round(sales * rate / 100, 2))
            except ValueError:
                pass

        # 设置创建时间：如果用户选择了则使用用户选择的，否则使用当前时间
        created_at_value = order_data.created_at
        if not created_at_value:
            created_at_value = beijing_now()
        elif isinstance(created_at_value, str):
            # 如果是字符串，转换为 datetime 对象
            from datetime import datetime as dt
            created_at_value = dt.fromisoformat(created_at_value.split('T')[0])
        
        # 计算订单滞留天数（自然日计算）
        order_days_value = calculate_order_days(created_at_value)

        # 计算毛利 = 销售金额 - 商品成本价（products 按商品名匹配，未匹配/未填成本按 0）
        gross_profit_value = await calc_order_gross_profit(
            order_data.product_name, order_data.sales_amount, db
        )

        new_order = Order(
            order_id=order_id,
            shop_id=order_data.shop_id,
            product_name=order_data.product_name,
            platform_order_no=order_data.platform_order_no,
            sales_amount=order_data.sales_amount,
            freight=order_data.freight,
            shipping_status=order_data.shipping_status,
            receiver_address=order_data.receiver_address,
            remark=order_data.remark,
            commission_rate=current_user.commission_rate,
            commission_amount=commission_amount,
            created_by=current_user.username,
            created_at=created_at_value,
            order_days=order_days_value,
            gross_profit=gross_profit_value
        )
        db.add(new_order)
        await db.commit()
        await db.refresh(new_order)

        # 发送新订单通知给工厂端
        creator_name = current_user.real_name or current_user.username
        await NotificationService.send_order_created_notification(db, new_order, creator_name)

        log = OperationLog(
            username=current_user.username,
            operation_type="创建订单",
            operation_content=f"创建订单 {order_id}"
        )
        db.add(log)
        await db.commit()

        order_dict = {
            "id": new_order.id,
            "order_id": new_order.order_id,
            "shop_id": new_order.shop_id,
            "product_name": new_order.product_name,
            "platform_order_no": new_order.platform_order_no,
            "sales_amount": new_order.sales_amount,
            "shipping_status": new_order.shipping_status,
            "logistics_company": new_order.logistics_company,
            "logistics_no": new_order.logistics_no,
            "logistics_no_2": new_order.logistics_no_2,
            "freight": new_order.freight,
            "shipping_operator": new_order.shipping_operator,
            "shipping_time": new_order.shipping_time,
            "receiver_address": new_order.receiver_address,
            "remark": new_order.remark,
            "commission_rate": new_order.commission_rate,
            "commission_amount": new_order.commission_amount,
            "created_by": str(new_order.created_by) if new_order.created_by else None,
            "creator_real_name": current_user.real_name or current_user.username,
            "created_at": new_order.created_at,
            "order_days": effective_order_days(new_order)
        }
        
        try:
            response = OrderResponse(**order_dict)
            return response
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"OrderResponse creation failed: {e}, order_dict keys: {list(order_dict.keys())}")
            raise
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"create_order failed: {e}", exc_info=True)
        raise

@router.get("/")
async def get_orders(
    shipping_status: Optional[str] = None,
    produce_status: Optional[str] = None,
    shop_id: Optional[str] = None,
    keyword: Optional[str] = None,
    created_by: Optional[str] = None,
    overdue: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    query = select(Order)
    count_query = select(func.count(Order.id))

    if current_user.role == "sales":
        query = query.where(
            cast(Order.created_by, String) == str(current_user.username)
        )
        count_query = count_query.where(
            cast(Order.created_by, String) == str(current_user.username)
        )

    # 超期订单筛选：下单时间早于「超期订单天数」阈值且尚未发货完成
    if overdue:
        days_str = await read_setting(db, "overdue_order_days", "7")
        try:
            overdue_days = int(float(days_str))
        except (TypeError, ValueError):
            overdue_days = 7
        if overdue_days < 0:
            overdue_days = 0
        threshold = beijing_now() - timedelta(days=overdue_days)
        overdue_filter = (Order.created_at < threshold) & (
            Order.shipping_status.notin_(["shipped", "refunded"])
        )
        query = query.where(overdue_filter)
        count_query = count_query.where(overdue_filter)

    if shipping_status:
        query = query.where(Order.shipping_status == shipping_status)
        count_query = count_query.where(Order.shipping_status == shipping_status)
    if produce_status:
        query = query.where(Order.produce_status == produce_status)
        count_query = count_query.where(Order.produce_status == produce_status)
    if shop_id:
        query = query.where(Order.shop_id == shop_id)
        count_query = count_query.where(Order.shop_id == shop_id)
    if keyword:
        like_conditions = (
            (Order.order_id.like(f"%{keyword}%")) |
            (Order.product_name.like(f"%{keyword}%")) |
            (Order.platform_order_no.like(f"%{keyword}%")) |
            (cast(Order.sales_amount, String).like(f"%{keyword}%"))
        )
        query = query.where(like_conditions)
        count_query = count_query.where(like_conditions)

    # 创建人筛选：仅老板端可按 created_by 过滤；销售端已在上方强制只看自己
    if created_by and current_user.role == "boss":
        query = query.where(cast(Order.created_by, String) == str(created_by))
        count_query = count_query.where(cast(Order.created_by, String) == str(created_by))

    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # 下单时长实时化后无法用存库值排序：按下单时间升序（下单越早=滞留越久，排越前），
    # 与"超期订单"实时计算口径一致；同日订单按存库时长降序保持稳定
    query = query.order_by(Order.created_at.asc(), Order.order_days.desc().nullslast()).offset(skip).limit(limit)
    result = await db.execute(query)
    orders = result.scalars().all()

    order_responses = []
    for order in orders:
        order_dict = {
            "id": order.id,
            "order_id": order.order_id,
            "shop_id": order.shop_id,
            "product_name": order.product_name,
            "platform_order_no": order.platform_order_no,
            "sales_amount": order.sales_amount,
            "shipping_status": order.shipping_status,
            "logistics_company": order.logistics_company,
            "logistics_no": order.logistics_no,
            "logistics_no_2": order.logistics_no_2,
            "freight": order.freight,
            "shipping_operator": order.shipping_operator,
            "shipping_time": order.shipping_time,
            "receiver_address": order.receiver_address,
            "remark": order.remark,
            "commission_rate": order.commission_rate,
            "commission_amount": order.commission_amount,
            "created_by": str(order.created_by) if order.created_by else None,
            "created_at": order.created_at,
            "order_days": effective_order_days(order),
            "produce_status": order.produce_status,
            "produce_status_update_at": order.produce_status_update_at,
            "produce_status_update_user": order.produce_status_update_user,
            "last_print_at": order.last_print_at,
        }

        if order.created_by:
            creator_result = await db.execute(
                select(User.real_name).where(User.username == order.created_by)
            )
            order_dict["creator_real_name"] = creator_result.scalar() or str(order.created_by)
        else:
            order_dict["creator_real_name"] = None

        # 金额/提成/创建人属财务敏感字段：仅老板端与销售端可见，工厂端/发货端置空
        if current_user.role not in ("boss", "sales"):
            order_dict["sales_amount"] = None
            order_dict["commission_amount"] = None
            order_dict["commission_rate"] = None
            order_dict["creator_real_name"] = None

        order_responses.append(order_dict)

    return {"data": order_responses, "total": total}

async def _serialize_order(order, db: AsyncSession, current_user):
    """将 Order 模型序列化为 OrderResponse（含创建人姓名与财务字段权限控制）。"""
    order_dict = {
        "id": order.id,
        "order_id": order.order_id,
        "shop_id": order.shop_id,
        "product_name": order.product_name,
        "platform_order_no": order.platform_order_no,
        "sales_amount": order.sales_amount,
        "shipping_status": order.shipping_status,
        "logistics_company": order.logistics_company,
        "logistics_no": order.logistics_no,
        "logistics_no_2": order.logistics_no_2,
        "freight": order.freight,
        "shipping_operator": order.shipping_operator,
        "shipping_time": order.shipping_time,
        "receiver_address": order.receiver_address,
        "remark": order.remark,
        "commission_rate": order.commission_rate,
        "commission_amount": order.commission_amount,
        "created_by": str(order.created_by) if order.created_by else None,
        "created_at": order.created_at,
        "order_days": effective_order_days(order),
        "produce_status": order.produce_status,
        "produce_status_update_at": order.produce_status_update_at,
        "produce_status_update_user": order.produce_status_update_user,
        "last_print_at": order.last_print_at,
    }

    if order.created_by:
        creator_result = await db.execute(
            select(User.real_name).where(User.username == str(order.created_by))
        )
        order_dict["creator_real_name"] = creator_result.scalar() or str(order.created_by)
    else:
        order_dict["creator_real_name"] = None

    # 金额/提成/创建人属财务敏感字段：仅老板端与销售端可见，工厂端/发货端置空
    if current_user.role not in ("boss", "sales"):
        order_dict["sales_amount"] = None
        order_dict["commission_amount"] = None
        order_dict["commission_rate"] = None
        order_dict["creator_real_name"] = None

    return OrderResponse(**order_dict)


@router.get("/by-platform/{platform_order_no}", response_model=OrderResponse)
async def get_order_by_platform_order_no(
    platform_order_no: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """按平台订单号（platform_order_no，唯一）精确查询订单。
    供手机端手动输入平台订单号查单使用。
    """
    result = await db.execute(select(Order).where(Order.platform_order_no == platform_order_no))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    if current_user.role == "sales" and str(order.created_by) != str(current_user.username):
        raise HTTPException(status_code=403, detail="您没有权限查看此订单")

    return await _serialize_order(order, db, current_user)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    result = await db.execute(select(Order).where(Order.order_id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    if current_user.role == "sales" and str(order.created_by) != str(current_user.username):
        raise HTTPException(status_code=403, detail="您没有权限查看此订单")

    return await _serialize_order(order, db, current_user)

PRODUCE_STATUS_MAP = {
    "unproduce": "未生产",
    "producing": "生产中",
    "produced": "生产完成"
}

async def update_produce_status(
    db: AsyncSession,
    order: Order,
    new_status: str,
    operator: str,
    change_type: str = "manual",
    old_status: str = None
):
    if old_status is None:
        old_status = order.produce_status
    
    if old_status == new_status:
        return
    
    order.produce_status = new_status
    order.produce_status_update_at = beijing_now()
    order.produce_status_update_user = operator
    
    old_display = PRODUCE_STATUS_MAP.get(old_status, old_status)
    new_display = PRODUCE_STATUS_MAP.get(new_status, new_status)
    
    if change_type == "manual":
        content = f"用户{operator}手动调整订单生产状态：{old_display} → {new_display}"
    elif change_type == "factory_image":
        content = f"系统自动更新：工厂上传生产图片，订单生产状态由{old_display}变更为生产中"
    elif change_type == "shipping":
        content = f"系统自动锁定：订单完成发货，生产状态强制更新为生产完成，生产流程结束"
    else:
        content = f"订单生产状态由{old_display}变更为{new_display}"
    
    log = OperationLog(
        username=operator,
        operation_type="update_produce_status",
        operation_content=content
    )
    db.add(log)
    
    await NotificationService.send_produce_status_notification(
        db=db,
        order=order,
        new_status=new_status,
        operator=operator,
        change_type=change_type,
        old_status=old_status
    )

@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: str,
    order_data: OrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    result = await db.execute(select(Order).where(Order.order_id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    if current_user.role == "sales" and str(order.created_by) != str(current_user.username):
        raise HTTPException(status_code=403, detail="您没有权限修改此订单")
    update_data = order_data.model_dump(exclude_unset=True)
    changes = []
    
    if "created_at" in update_data and isinstance(update_data["created_at"], str):
        from datetime import datetime as dt
        update_data["created_at"] = dt.fromisoformat(update_data["created_at"].split('T')[0])
        print(f"[DEBUG] converted created_at to datetime: {update_data['created_at']}")

    if current_user.role == "shipping":
        allowed_fields = {"shipping_status", "logistics_company", "logistics_no", "logistics_no_2", "freight", "remark"}
        forbidden_fields = set(update_data.keys()) - allowed_fields
        if forbidden_fields:
            raise HTTPException(
                status_code=403,
                detail=f"发货端仅允许编辑发货状态、物流公司、物流单号、运费、备注，禁止修改: {', '.join(forbidden_fields)}"
            )

    if current_user.role == "factory":
        allowed_fields = {"produce_status", "remark"}
        forbidden_fields = set(update_data.keys()) - allowed_fields
        if forbidden_fields:
            raise HTTPException(
                status_code=403,
                detail=f"工厂端仅允许修改生产状态、备注，禁止修改: {', '.join(forbidden_fields)}"
            )

    old_shipping_status = order.shipping_status
    
    if "produce_status" in update_data:
        new_produce_status = update_data["produce_status"]
        
        if order.shipping_status in ["shipped", "virtual"]:
            if new_produce_status in ["unproduce", "producing"]:
                raise HTTPException(
                    status_code=400,
                    detail="订单已完成发货，生产流程已结束，生产状态锁定为【生产完成】，无法修改"
                )
        
        if new_produce_status not in ["unproduce", "producing", "produced"]:
            raise HTTPException(status_code=400, detail="生产状态值无效")
        
        old_produce_status = order.produce_status
        await update_produce_status(
            db=db,
            order=order,
            new_status=new_produce_status,
            operator=current_user.username,
            change_type="manual",
            old_status=old_produce_status
        )
        update_data.pop("produce_status")

    if "shipping_status" in update_data:
        new_status = update_data["shipping_status"]
        if order.shipping_status == "shipped" and new_status not in ("shipped", "refunded"):
            raise HTTPException(
                status_code=403,
                detail="已发货的订单仅允许改为【已退货/退款】，不允许改为其他状态"
            )
        if order.shipping_status == "virtual" and new_status not in ("virtual", "shipped", "refunded"):
            raise HTTPException(
                status_code=403,
                detail="已虚拟发货的订单仅允许改为【已发货】或【已退货/退款】"
            )
        if new_status == "shipped" and order.shipping_status != "shipped":
            if "shipping_time" not in update_data or not update_data["shipping_time"]:
                update_data["shipping_time"] = beijing_now()
            update_data["shipping_operator"] = current_user.username
            changes.append(f"发货时间: 记录为 {update_data['shipping_time']}")
            changes.append(f"发货操作员: {current_user.username}")
            
            if order.produce_status != "produced":
                await update_produce_status(
                    db=db,
                    order=order,
                    new_status="produced",
                    operator="system-auto",
                    change_type="shipping"
                )

    if "shipping_time" in update_data and update_data["shipping_time"]:
        if isinstance(update_data["shipping_time"], str):
            try:
                update_data["shipping_time"] = datetime.fromisoformat(update_data["shipping_time"])
            except ValueError:
                pass

    if "sales_amount" in update_data and update_data["sales_amount"] != order.sales_amount:
        if order.commission_rate:
            try:
                new_sales = float(update_data["sales_amount"])
                new_commission = round(new_sales * order.commission_rate / 100, 2)
                update_data["commission_amount"] = str(new_commission)
                changes.append(f"销售金额: {order.sales_amount} -> {update_data['sales_amount']}")
            except ValueError:
                pass
    
    old_receiver_address = order.receiver_address
    for field, value in update_data.items():
        old_value = getattr(order, field)
        if old_value != value and field not in ["shipping_time", "shipping_operator"]:
            changes.append(f"{field}: {old_value} -> {value}")
        setattr(order, field, value)
    
    if "created_at" in update_data:
        if isinstance(order.created_at, str):
            from datetime import datetime as dt
            order.created_at = dt.fromisoformat(order.created_at.split('T')[0])
        order.order_days = calculate_order_days(order.created_at)
        changes.append(f"滞留时长: 更新为 {order.order_days} 天")

    # 状态变为已发货/已退款：冻结下单时长（此后读取时不再随时间变化）
    if "shipping_status" in update_data:
        new_status = update_data["shipping_status"]
        if new_status in _FROZEN_DAYS_STATUSES and old_shipping_status not in _FROZEN_DAYS_STATUSES:
            order.order_days = calculate_order_days(order.created_at)
            changes.append(f"下单时长: 冻结为 {order.order_days} 天")
    
    # 收货地址发生变更 → 重置国家识别结果，智慧大屏下次刷新会按新地址重新识别
    if "receiver_address" in update_data and update_data["receiver_address"] != old_receiver_address:
        order.detected_country = None
        changes.append("收货地址已变更，国家识别已重置（智慧大屏将重新识别）")

    # 商品名或销售金额变化 → 重算毛利（内部统计字段，不在订单界面展示）
    if "product_name" in update_data or "sales_amount" in update_data:
        order.gross_profit = await calc_order_gross_profit(
            order.product_name, order.sales_amount, db
        )

    await db.commit()
    await db.refresh(order)

    if "shipping_status" in update_data and old_shipping_status != "shipped" and update_data["shipping_status"] == "shipped":
        try:
            await NotificationService.send_order_shipped_notification(
                db=db,
                order_id=order_id,
                logistics_company=update_data.get("logistics_company") or order.logistics_company,
                logistics_no=update_data.get("logistics_no") or order.logistics_no,
                logistics_no_2=update_data.get("logistics_no_2") or order.logistics_no_2
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"发送站内信失败，但不影响订单更新: {e}")

    if changes:
        log = OperationLog(
            username=current_user.username,
            operation_type="更新订单",
            operation_content=f"更新订单 {order_id}，变更: {', '.join(changes)}"
        )
        db.add(log)
        await db.commit()

    order_dict = {
        "id": order.id,
        "order_id": order.order_id,
        "shop_id": order.shop_id,
        "product_name": order.product_name,
        "platform_order_no": order.platform_order_no,
        "sales_amount": order.sales_amount,
        "shipping_status": order.shipping_status,
        "logistics_company": order.logistics_company,
        "logistics_no": order.logistics_no,
        "logistics_no_2": order.logistics_no_2,
        "freight": order.freight,
        "shipping_operator": order.shipping_operator,
        "shipping_time": order.shipping_time,
        "receiver_address": order.receiver_address,
        "remark": order.remark,
        "commission_rate": order.commission_rate,
        "commission_amount": order.commission_amount,
        "created_by": str(order.created_by) if order.created_by else None,
        "created_at": order.created_at,
        "order_days": effective_order_days(order),
        "produce_status": order.produce_status,
        "produce_status_update_at": order.produce_status_update_at,
        "produce_status_update_user": order.produce_status_update_user,
        "last_print_at": order.last_print_at,
    }

    if order.created_by:
        creator_result = await db.execute(
            select(User.real_name).where(User.username == str(order.created_by))
        )
        order_dict["creator_real_name"] = creator_result.scalar() or str(order.created_by)
    else:
        order_dict["creator_real_name"] = None

    return OrderResponse(**order_dict)


@router.post("/{order_id}/mark-printed", response_model=OrderResponse)
async def mark_order_printed(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """点击"打印"按钮时调用，将订单的 last_print_at 设为当前时间（beijing）。
    无论是否真的打出纸张，只要点了打印按钮即视为"打印过"并记录。
    """
    result = await db.execute(select(Order).where(Order.order_id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    order.last_print_at = beijing_now()
    await db.commit()
    await db.refresh(order)

    # 操作日志
    db.add(OperationLog(
        username=current_user.username,
        operation_type="订单打印",
        operation_content=f"标记订单 {order.order_id} 已打印"
    ))
    await db.commit()

    # 构造响应（复用 update_order 的字段补全逻辑，保持与列表/详情一致）
    order_dict = {c.key: getattr(order, c.key) for c in order.__table__.columns}
    if "creator_real_name" not in order_dict or order_dict.get("creator_real_name") is None:
        order_dict["creator_real_name"] = None
    return OrderResponse(**order_dict)


@router.delete("/{order_id}", status_code=200)
async def delete_order(
    order_id: str,
    delete_request: DeleteOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    # 验证密码
    if not verify_password(delete_request.password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="密码错误")

    result = await db.execute(select(Order).where(Order.order_id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 检查权限：仅允许订单创建人删除订单，其他用户（包括管理员）均不允许删除他人订单
    if str(order.created_by) != str(current_user.username):
        # 记录未授权的删除尝试
        log = OperationLog(
            username=current_user.username,
            operation_type="删除订单",
            operation_content=f"尝试删除订单 {order_id} 失败：无权限，操作用户={current_user.real_name or current_user.username}"
        )
        db.add(log)
        await db.commit()
        
        raise HTTPException(status_code=403, detail="您没有权限删除此订单，只有订单创建人可以删除")

    # 删除关联的图片记录和物理文件
    from app.models.models import Image
    from app.core.config import OFFICIAL_DIR
    from pathlib import Path
    import shutil
    import os

    # 查询该订单关联的所有图片
    img_result = await db.execute(select(Image).where(Image.order_id == order_id))
    images = img_result.scalars().all()

    for img in images:
        # 删除物理文件
        if img.image_url:
            file_path = Path(str(OFFICIAL_DIR.parent) + img.image_url.replace("/data/images", ""))
            if file_path.exists() and file_path.is_file():
                try:
                    os.remove(file_path)
                except Exception as e:
                    pass
        
        # 删除数据库记录
        await db.delete(img)
    
    await db.commit()

    # 删除订单对应的文件夹（先做路径净化与边界校验，防路径穿越）
    safe_order_id = sanitize_path_component(order_id)
    order_folder = (OFFICIAL_DIR / safe_order_id).resolve()
    try:
        order_folder.relative_to(OFFICIAL_DIR.resolve())
    except ValueError:
        order_folder = OFFICIAL_DIR  # 非法路径：不删除任何目录
    if order_folder.exists() and order_folder.is_dir():
        try:
            shutil.rmtree(order_folder)
        except Exception as e:
            pass

    # 删除订单
    await db.delete(order)
    await db.commit()

    # 记录成功的删除操作
    log = OperationLog(
        username=current_user.username,
        operation_type="删除订单",
        operation_content=f"成功删除订单 {order_id}（含{len(images)}张图片），操作用户={current_user.real_name or current_user.username}"
    )
    db.add(log)
    await db.commit()

    return {"message": "订单删除成功"}
