# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from ..core.database import get_db
from ..core.security import get_current_active_user, ensure_data_permission
from ..core.crypto import encrypt_value, decrypt_value
from ..models.models import Shop, Order, OperationLog, User, Platform, OrderImport, beijing_now
from ..schemas.schemas import ShopCreate, ShopUpdate, ShopResponse
from .order_imports import compute_import_errors
import json
import secrets

router = APIRouter(prefix="/api/shops", tags=["网店管理"])

# 需要加密存储的密钥类字段
_SECRET_FIELDS = ("api_app_secret", "api_access_token", "api_refresh_token", "webhook_verify_key")
# 平台切换为"手工录入"时需清空的全部 API 配置字段（保留 platform_id / 基础字段）
_API_CONFIG_FIELDS = (
    "api_app_key", "api_app_secret", "api_access_token", "api_refresh_token",
    "api_token_expire", "api_auth_scope", "api_self_qps", "sync_auto_enable",
    "sync_order_interval", "sync_time_window", "last_sync_success_time",
    "api_retry_count", "api_retry_base_ms", "webhook_callback", "webhook_verify_key",
    "api_ext_json",
)


def _encrypt_or_clear(value):
    """None / 空串 -> None（清空）；否则加密后存储。"""
    if value is None or value == "":
        return None
    return encrypt_value(value)


def _shop_response(shop, platform, creator_real_name, order_count, current_user) -> ShopResponse:
    """构造网店响应；密钥类字段仅 boss 解密返回明文，其余角色整套 API 面板字段置空。"""
    is_boss = current_user.role == "boss"
    base = {
        "id": shop.id,
        "shop_id": shop.shop_id,
        "shop_name": shop.shop_name,
        "shop_account": shop.shop_account,
        "status": shop.status,
        "platform_id": shop.platform_id,
        "platform_code": platform.platform_code if platform else None,
        "platform_name": platform.platform_name if platform else None,
        "creator": creator_real_name,
        "create_time": shop.create_time,
        "update_time": shop.update_time,
        "order_count": order_count,
    }
    if is_boss:
        base.update({
            "api_app_key": shop.api_app_key,
            "api_app_secret": decrypt_value(shop.api_app_secret),
            "api_access_token": decrypt_value(shop.api_access_token),
            "api_refresh_token": decrypt_value(shop.api_refresh_token),
            "api_token_expire": shop.api_token_expire,
            "api_auth_scope": shop.api_auth_scope,
            "api_self_qps": shop.api_self_qps,
            "sync_auto_enable": shop.sync_auto_enable,
            "sync_order_interval": shop.sync_order_interval,
            "sync_time_window": shop.sync_time_window,
            "last_sync_success_time": shop.last_sync_success_time,
            "api_retry_count": shop.api_retry_count,
            "api_retry_base_ms": shop.api_retry_base_ms,
            "webhook_callback": shop.webhook_callback,
            "webhook_verify_key": decrypt_value(shop.webhook_verify_key),
            "api_ext_json": shop.api_ext_json,
        })
    else:
        # 销售等角色：整套 API 面板字段置空（前端隐藏整组）
        base.update({k: None for k in (
            "api_app_key", "api_app_secret", "api_access_token", "api_refresh_token",
            "api_token_expire", "api_auth_scope", "api_self_qps", "sync_auto_enable",
            "sync_order_interval", "sync_time_window", "last_sync_success_time",
            "api_retry_count", "api_retry_base_ms", "webhook_callback", "webhook_verify_key",
            "api_ext_json",
        )})
    return ShopResponse(**base)


@router.get("/", response_model=List[ShopResponse])
async def get_shops(
    shop_name: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    query = select(Shop)
    if current_user.role != "boss":
        query = query.where(Shop.creator == current_user.username)
    if shop_name:
        query = query.where(Shop.shop_name.like(f"%{shop_name}%"))
    if status:
        query = query.where(Shop.status == status)

    query = query.order_by(Shop.create_time.desc())
    result = await db.execute(query)
    shops = result.scalars().all()

    platforms = {p.id: p for p in (await db.execute(select(Platform))).scalars().all()}

    shop_responses = []
    for shop in shops:
        order_count = (await db.execute(
            select(func.count(Order.id)).where(Order.shop_id == shop.shop_id)
        )).scalar() or 0
        creator_real_name = (await db.execute(
            select(User.real_name).where(User.username == shop.creator)
        )).scalar() or shop.creator
        shop_responses.append(_shop_response(shop, platforms.get(shop.platform_id), creator_real_name, order_count, current_user))
    return shop_responses


@router.get("/{shop_id}", response_model=ShopResponse)
async def get_shop(
    shop_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    shop = (await db.execute(select(Shop).where(Shop.shop_id == shop_id))).scalar_one_or_none()
    if not shop:
        raise HTTPException(status_code=404, detail="网店不存在")
    if current_user.role != "boss" and shop.creator != current_user.username:
        raise HTTPException(status_code=403, detail="您没有权限查看此网店")

    order_count = (await db.execute(
        select(func.count(Order.id)).where(Order.shop_id == shop.shop_id)
    )).scalar() or 0
    creator_real_name = (await db.execute(
        select(User.real_name).where(User.username == shop.creator)
    )).scalar() or shop.creator
    platform = (await db.execute(select(Platform).where(Platform.id == shop.platform_id))).scalar_one_or_none() if shop.platform_id else None
    return _shop_response(shop, platform, creator_real_name, order_count, current_user)


async def _validate_platform(db, platform_id):
    """校验 platform_id：None 合法（手工录入）；非 None 必须存在且启用。"""
    if platform_id is None:
        return None
    p = (await db.execute(select(Platform).where(Platform.id == platform_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=400, detail="关联的平台不存在")
    if p.status != 1:
        raise HTTPException(status_code=400, detail="关联的平台已禁用，请先到平台管理启用")
    return p


@router.post("/", response_model=ShopResponse)
async def create_shop(
    shop_data: ShopCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    if current_user.role not in ["boss", "sales"]:
        raise HTTPException(status_code=403, detail="您没有权限创建网店")
    ensure_data_permission(current_user, '/shops', 'add')

    result = await db.execute(select(Shop).where(
        Shop.shop_name == shop_data.shop_name,
        Shop.shop_account == shop_data.shop_account
    ))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="相同网店（名称+账号）已存在，请修改")

    platform = await _validate_platform(db, shop_data.platform_id)

    shop_id = shop_data.shop_name + shop_data.shop_account
    new_shop = Shop(
        shop_id=shop_id,
        shop_name=shop_data.shop_name,
        shop_account=shop_data.shop_account,
        status=shop_data.status,
        platform_id=shop_data.platform_id,
        creator=current_user.username,
        api_app_key=shop_data.api_app_key,
        api_app_secret=_encrypt_or_clear(shop_data.api_app_secret),
        api_access_token=_encrypt_or_clear(shop_data.api_access_token),
        api_refresh_token=_encrypt_or_clear(shop_data.api_refresh_token),
        api_self_qps=shop_data.api_self_qps,
        sync_auto_enable=shop_data.sync_auto_enable,
        sync_order_interval=shop_data.sync_order_interval,
        sync_time_window=shop_data.sync_time_window,
        api_retry_count=shop_data.api_retry_count,
        api_retry_base_ms=shop_data.api_retry_base_ms,
        webhook_callback=shop_data.webhook_callback,
        webhook_verify_key=_encrypt_or_clear(shop_data.webhook_verify_key),
        api_ext_json=shop_data.api_ext_json,
    )
    db.add(new_shop)
    await db.commit()
    await db.refresh(new_shop)

    db.add(OperationLog(
        username=current_user.username,
        operation_type="创建网店",
        operation_content=f"创建网店 {new_shop.shop_name}" + (f"（平台：{platform.platform_name}）" if platform else "（手工录入）")
    ))
    await db.commit()

    creator_real_name = (await db.execute(
        select(User.real_name).where(User.username == current_user.username)
    )).scalar() or current_user.username
    return _shop_response(new_shop, platform, creator_real_name, 0, current_user)


@router.put("/{shop_id}", response_model=ShopResponse)
async def update_shop(
    shop_id: str,
    shop_data: ShopUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    ensure_data_permission(current_user, '/shops', 'edit')
    shop = (await db.execute(select(Shop).where(Shop.shop_id == shop_id))).scalar_one_or_none()
    if not shop:
        raise HTTPException(status_code=404, detail="网店不存在")
    if current_user.role != "boss" and shop.creator != current_user.username:
        raise HTTPException(status_code=403, detail="您没有权限修改此网店")

    if shop_data.shop_name is not None or shop_data.shop_account is not None:
        new_name = shop_data.shop_name if shop_data.shop_name is not None else shop.shop_name
        new_account = shop_data.shop_account if shop_data.shop_account is not None else shop.shop_account
        existing = await db.execute(select(Shop).where(
            Shop.shop_name == new_name,
            Shop.shop_account == new_account,
            Shop.shop_id != shop_id
        ))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="相同网店（名称+账号）已存在")

    update_data = shop_data.model_dump(exclude_unset=True)

    # 平台校验 + 切换为手工模式时清空整套 API 配置
    if "platform_id" in update_data:
        pid = update_data["platform_id"]
        await _validate_platform(db, pid)
        if pid is None:
            for f in _API_CONFIG_FIELDS:
                setattr(shop, f, None)

    for field, value in update_data.items():
        if field == "shop_id":
            continue  # 不允许修改 shop_id，防止订单关联断裂
        if field in _SECRET_FIELDS:
            setattr(shop, field, _encrypt_or_clear(value))
        else:
            setattr(shop, field, value)

    await db.commit()
    await db.refresh(shop)

    order_count = (await db.execute(
        select(func.count(Order.id)).where(Order.shop_id == shop.shop_id)
    )).scalar() or 0
    db.add(OperationLog(
        username=current_user.username,
        operation_type="更新网店",
        operation_content=f"更新网店 {shop.shop_name}"
    ))
    await db.commit()

    creator_real_name = (await db.execute(
        select(User.real_name).where(User.username == shop.creator)
    )).scalar() or shop.creator
    platform = (await db.execute(select(Platform).where(Platform.id == shop.platform_id))).scalar_one_or_none() if shop.platform_id else None
    return _shop_response(shop, platform, creator_real_name, order_count, current_user)


@router.delete("/{shop_id}", status_code=200)
async def delete_shop(
    shop_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    ensure_data_permission(current_user, '/shops', 'delete')
    shop = (await db.execute(select(Shop).where(Shop.shop_id == shop_id))).scalar_one_or_none()
    if not shop:
        raise HTTPException(status_code=404, detail="网店不存在")
    if current_user.role != "boss" and shop.creator != current_user.username:
        raise HTTPException(status_code=403, detail="您没有权限删除此网店")

    order_count = (await db.execute(
        select(func.count(Order.id)).where(Order.shop_id == shop_id)
    )).scalar() or 0
    if order_count > 0:
        raise HTTPException(status_code=400, detail="该网店已关联订单，无法删除")

    await db.delete(shop)
    await db.commit()
    db.add(OperationLog(
        username=current_user.username,
        operation_type="删除网店",
        operation_content=f"删除网店 {shop.shop_name}"
    ))
    await db.commit()
    return {"message": "网店删除成功"}


async def _save_fetched_to_imports(db: AsyncSession, shop: Shop, orders: list, current_user) -> int:
    """把平台拉回的订单写入 order_imports 临时表（同批 batch_no），逐行计算异常。
    返回写入条数。落点与 Excel 导入完全一致：仅暂存，等待人工审核合并，
    不直接进正式 orders 表，避免平台脏数据污染正式订单。"""
    batch_no = f"SYNC{beijing_now().strftime('%Y%m%d%H%M%S')}{secrets.token_hex(3).upper()}"
    created_rows = []
    for o in orders:
        row = OrderImport(
            batch_no=batch_no,
            platform_order_no=str(o.get("platform_order_no") or "").strip(),
            shop_name=shop.shop_name,
            shop_account=shop.shop_account,
            shop_id=shop.shop_id,
            product_name=str(o.get("product_name") or ""),
            sales_amount=str(o.get("sales_amount") or ""),
            freight=str(o.get("freight") or ""),
            shipping_status=str(o.get("shipping_status") or "pending"),
            produce_status=str(o.get("produce_status") or "unproduce"),
            logistics_company=str(o.get("logistics_company") or ""),
            logistics_no=str(o.get("logistics_no") or ""),
            receiver_address=str(o.get("receiver_address") or ""),
            remark=str(o.get("remark") or ""),
            refund_note=str(o.get("refund_note") or ""),
            order_time=str(o.get("order_time") or ""),
            shipping_time=str(o.get("shipping_time") or ""),
            imported_by=current_user.username,
        )
        db.add(row)
        created_rows.append(row)
    await db.commit()
    for row in created_rows:
        errors = await compute_import_errors(db, row)
        row.errors = json.dumps(errors, ensure_ascii=False)
    await db.commit()
    # 操作日志
    db.add(OperationLog(
        username=current_user.username,
        operation_type="平台订单同步",
        operation_content=f"同步写入数据导入临时表 {len(created_rows)} 行（批次 {batch_no}）",
    ))
    await db.commit()
    return len(created_rows)


# ==================== 手动同步订单 ====================

async def _fetch_platform_orders(shop, platform, secrets, config):
    """占位：真实实现需按 platform.platform_code 调用对应开放平台接口，
    以 shop.last_sync_success_time 为增量起点拉取订单，并用 orders.platform_order_no 去重
    （存在则更新、不存在则新增）。当前仅搭建框架，返回空列表。
    返回结构：{"orders": [...], "note": "..."}。
    每条 order 字段映射 OrderImport：platform_order_no / sales_amount / freight /
    shipping_status / produce_status / order_time / shipping_time / product_name / remark 等。"""
    return {"orders": [], "note": "平台拉单逻辑待按各平台开放 API 接入"}


@router.post("/{shop_id}/sync", summary="手动同步订单（立即同步，不受自动同步开关影响）")
async def sync_shop_orders(
    shop_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="仅老板可手动同步订单")
    shop = (await db.execute(select(Shop).where(Shop.shop_id == shop_id))).scalar_one_or_none()
    if not shop:
        raise HTTPException(status_code=404, detail="网店不存在")
    if shop.platform_id is None:
        raise HTTPException(status_code=400, detail="手工录入网店不支持订单同步")

    platform = (await db.execute(select(Platform).where(Platform.id == shop.platform_id))).scalar_one_or_none()
    if not platform:
        raise HTTPException(status_code=400, detail="关联平台不存在")

    # 合并平台公共配置 + 店铺私有密钥（内存使用，不复制进 shops 表）
    secrets = {f: decrypt_value(getattr(shop, f)) for f in _SECRET_FIELDS}
    config = {
        "platform_code": platform.platform_code,
        "api_gateway": platform.api_gateway,
        "api_version": platform.api_version,
        "api_global_max_qps": platform.api_global_max_qps,
        "top_sign_type": platform.top_sign_type,
        "top_default_fields": platform.top_default_fields,
        "rest_auth_header": platform.rest_auth_header,
        "rest_token_prefix": platform.rest_token_prefix,
        "webhook_encrypt_type": platform.webhook_encrypt_type,
    }
    try:
        result = await _fetch_platform_orders(shop, platform, secrets, config)
        # 拉到的平台订单先写入"数据导入"临时表（同批 batch_no），等待人工审核合并，
        # 不直接进正式 orders 表。
        fetched_orders = (result or {}).get("orders") or []
        imported_count = 0
        if fetched_orders:
            imported_count = await _save_fetched_to_imports(db, shop, fetched_orders, current_user)
        # 同步成功：更新增量起点（失败分支不更新，见 except）
        shop.last_sync_success_time = beijing_now()
        await db.commit()
        if imported_count > 0:
            return {"message": f"共导入 {imported_count} 条订单，请到数据导入中审核导入", "detail": result}
        # 占位实现尚未真正拉单；如实反馈，避免让用户误以为已同步真实订单
        note = (result or {}).get("note")
        return {"message": note or "本次未拉取到新订单", "detail": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败：{e}")
