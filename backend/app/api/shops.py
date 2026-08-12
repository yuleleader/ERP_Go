# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from ..core.database import get_db
from ..core.security import get_current_active_user, ensure_data_permission
from ..models.models import Shop, Order, OperationLog, User
from ..schemas.schemas import ShopCreate, ShopUpdate, ShopResponse

router = APIRouter(prefix="/api/shops", tags=["网店管理"])

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

    shop_responses = []
    for shop in shops:
        order_count_result = await db.execute(
            select(func.count(Order.id)).where(Order.shop_id == shop.shop_id)
        )
        order_count = order_count_result.scalar() or 0

        # 查询创建者的真实姓名
        creator_result = await db.execute(
            select(User.real_name).where(User.username == shop.creator)
        )
        creator_real_name = creator_result.scalar() or shop.creator

        shop_dict = {
            "id": shop.id,
            "shop_id": shop.shop_id,
            "shop_name": shop.shop_name,
            "shop_account": shop.shop_account,
            "status": shop.status,
            "creator": creator_real_name,
            "create_time": shop.create_time,
            "update_time": shop.update_time,
            "order_count": order_count
        }
        shop_responses.append(ShopResponse(**shop_dict))

    return shop_responses

@router.get("/{shop_id}", response_model=ShopResponse)
async def get_shop(
    shop_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    result = await db.execute(select(Shop).where(Shop.shop_id == shop_id))
    shop = result.scalar_one_or_none()
    if not shop:
        raise HTTPException(status_code=404, detail="网店不存在")

    if current_user.role != "boss" and shop.creator != current_user.username:
        raise HTTPException(status_code=403, detail="您没有权限查看此网店")

    order_count_result = await db.execute(
        select(func.count(Order.id)).where(Order.shop_id == shop.shop_id)
    )
    order_count = order_count_result.scalar() or 0

    # 查询创建者的真实姓名
    creator_result = await db.execute(
        select(User.real_name).where(User.username == shop.creator)
    )
    creator_real_name = creator_result.scalar() or shop.creator

    shop_dict = {
        "id": shop.id,
        "shop_id": shop.shop_id,
        "shop_name": shop.shop_name,
        "shop_account": shop.shop_account,
        "status": shop.status,
        "creator": creator_real_name,
        "create_time": shop.create_time,
        "update_time": shop.update_time,
        "order_count": order_count
    }
    return ShopResponse(**shop_dict)

@router.post("/", response_model=ShopResponse)
async def create_shop(
    shop_data: ShopCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    if current_user.role not in ["boss", "sales"]:
        raise HTTPException(status_code=403, detail="您没有权限创建网店")
    ensure_data_permission(current_user, '/shops', 'add')

    # 唯一性校验：同邮箱可在不同平台（网店名不同）重复注册；仅"名称+账号"都相同才拦截
    result = await db.execute(
        select(Shop).where(
            Shop.shop_name == shop_data.shop_name,
            Shop.shop_account == shop_data.shop_account
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="相同网店（名称+账号）已存在，请修改")

    # 生成shop_id：店铺名称 + 网店账号
    shop_id = shop_data.shop_name + shop_data.shop_account

    new_shop = Shop(
        shop_id=shop_id,
        shop_name=shop_data.shop_name,
        shop_account=shop_data.shop_account,
        status=shop_data.status,
        creator=current_user.username
    )
    db.add(new_shop)
    await db.commit()
    await db.refresh(new_shop)

    log = OperationLog(
        username=current_user.username,
        operation_type="创建网店",
        operation_content=f"创建网店 {new_shop.shop_name}"
    )
    db.add(log)
    await db.commit()

    # 查询创建者的真实姓名
    creator_result = await db.execute(
        select(User.real_name).where(User.username == current_user.username)
    )
    creator_real_name = creator_result.scalar() or current_user.username

    return ShopResponse(
        id=new_shop.id,
        shop_id=new_shop.shop_id,
        shop_name=new_shop.shop_name,
        shop_account=new_shop.shop_account,
        status=new_shop.status,
        creator=creator_real_name,
        create_time=new_shop.create_time,
        update_time=new_shop.update_time,
        order_count=0
    )

@router.put("/{shop_id}", response_model=ShopResponse)
async def update_shop(
    shop_id: str,
    shop_data: ShopUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    ensure_data_permission(current_user, '/shops', 'edit')
    result = await db.execute(select(Shop).where(Shop.shop_id == shop_id))
    shop = result.scalar_one_or_none()
    if not shop:
        raise HTTPException(status_code=404, detail="网店不存在")

    if current_user.role != "boss" and shop.creator != current_user.username:
        raise HTTPException(status_code=403, detail="您没有权限修改此网店")

    if shop_data.shop_name is not None or shop_data.shop_account is not None:
        # 组合唯一：以"修改后的名称 + 修改后的账号"判断，排除自身
        new_name = shop_data.shop_name if shop_data.shop_name is not None else shop.shop_name
        new_account = shop_data.shop_account if shop_data.shop_account is not None else shop.shop_account
        existing = await db.execute(
            select(Shop).where(
                Shop.shop_name == new_name,
                Shop.shop_account == new_account,
                Shop.shop_id != shop_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="相同网店（名称+账号）已存在")

    update_data = shop_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == 'shop_id':
            continue  # 不允许修改 shop_id，防止订单关联断裂
        setattr(shop, field, value)

    await db.commit()
    await db.refresh(shop)

    order_count_result = await db.execute(
        select(func.count(Order.id)).where(Order.shop_id == shop.shop_id)
    )
    order_count = order_count_result.scalar() or 0

    log = OperationLog(
        username=current_user.username,
        operation_type="更新网店",
        operation_content=f"更新网店 {shop.shop_name}"
    )
    db.add(log)
    await db.commit()

    # 查询创建者的真实姓名
    creator_result = await db.execute(
        select(User.real_name).where(User.username == shop.creator)
    )
    creator_real_name = creator_result.scalar() or shop.creator

    return ShopResponse(
        id=shop.id,
        shop_id=shop.shop_id,
        shop_name=shop.shop_name,
        shop_account=shop.shop_account,
        status=shop.status,
        creator=creator_real_name,
        create_time=shop.create_time,
        update_time=shop.update_time,
        order_count=order_count
    )

@router.delete("/{shop_id}", status_code=200)
async def delete_shop(
    shop_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    ensure_data_permission(current_user, '/shops', 'delete')
    result = await db.execute(select(Shop).where(Shop.shop_id == shop_id))
    shop = result.scalar_one_or_none()
    if not shop:
        raise HTTPException(status_code=404, detail="网店不存在")

    if current_user.role != "boss" and shop.creator != current_user.username:
        raise HTTPException(status_code=403, detail="您没有权限删除此网店")

    order_count_result = await db.execute(
        select(func.count(Order.id)).where(Order.shop_id == shop_id)
    )
    order_count = order_count_result.scalar() or 0
    if order_count > 0:
        raise HTTPException(status_code=400, detail="该网店已关联订单，无法删除")

    await db.delete(shop)
    await db.commit()

    log = OperationLog(
        username=current_user.username,
        operation_type="删除网店",
        operation_content=f"删除网店 {shop.shop_name}"
    )
    db.add(log)
    await db.commit()

    return {"message": "网店删除成功"}
