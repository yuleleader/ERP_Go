# -*- coding: utf-8 -*-
"""
商品管理API模块
提供商品的增删改查功能，支持分页、搜索、筛选
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional, List
from ..core.database import get_db
from ..core.security import get_current_active_user
from ..models.models import Product, User, OperationLog
from ..schemas.schemas import ProductCreate, ProductUpdate, ProductResponse
from ..api.product_images import delete_product_images

router = APIRouter(prefix="/api/products", tags=["商品管理"])


async def generate_product_code(db: AsyncSession) -> str:
    """
    生成商品唯一标识码
    采用顺序编号格式：PLU-000001
    每次新增自动+1
    """
    result = await db.execute(
        select(func.max(Product.id))
    )
    max_id = result.scalar() or 0
    new_id = max_id + 1
    return f"PLU-{new_id:06d}"


@router.post("/", response_model=ProductResponse)
async def create_product(
    product_data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    创建商品
    权限要求：boss（仅老板端可新建商品）
    """
    # 权限检查：只有老板端可以创建商品
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="您没有权限创建商品")

    # 创建商品记录：先插入占位编码，flush 拿到自增 id 后回填唯一编码
    # （编码=PLU-{id:06d}，与 id 绑定，从根上避免 max(id)+1 在并发下的重复问题）
    new_product = Product(
        product_code="",
        product_name=product_data.product_name,
        product_remark=product_data.product_remark,
        status="active",
        category_id=product_data.category_id,
        brand_id=product_data.brand_id,
        cost_price=product_data.cost_price,
        retail_price=product_data.retail_price,
        min_price=product_data.min_price,
        remark1=product_data.remark1,
        remark2=product_data.remark2,
        remark3=product_data.remark3,
        created_by=current_user.username
    )
    db.add(new_product)
    await db.flush()
    new_product.product_code = f"PLU-{new_product.id:06d}"
    await db.commit()
    await db.refresh(new_product)

    # 记录操作日志
    log = OperationLog(
        username=current_user.username,
        operation_type="创建商品",
        operation_content=f"创建商品 {new_product.product_code} - {product_data.product_name}"
    )
    db.add(log)
    await db.commit()

    return ProductResponse(
        id=new_product.id,
        product_code=new_product.product_code,
        product_name=new_product.product_name,
        product_remark=new_product.product_remark,
        status=new_product.status,
        category_id=new_product.category_id,
        brand_id=new_product.brand_id,
        cost_price=new_product.cost_price,
        retail_price=new_product.retail_price,
        min_price=new_product.min_price,
        remark1=new_product.remark1,
        remark2=new_product.remark2,
        remark3=new_product.remark3,
        created_by=new_product.created_by,
        created_at=new_product.created_at,
        updated_at=new_product.updated_at
    )


@router.get("/", response_model=List[ProductResponse])
async def get_products(
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    category_id: Optional[int] = None,
    brand_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取商品列表
    支持分页、关键词搜索、状态筛选、按类别/品牌筛选
    权限要求：所有角色可查看
    """
    query = select(Product)

    # 关键词搜索：商品编码、商品名称
    if keyword:
        query = query.where(
            or_(
                Product.product_code.like(f"%{keyword}%"),
                Product.product_name.like(f"%{keyword}%")
            )
        )

    # 状态筛选
    if status:
        query = query.where(Product.status == status)

    # 按类别筛选
    if category_id is not None:
        query = query.where(Product.category_id == category_id)

    # 按品牌筛选
    if brand_id is not None:
        query = query.where(Product.brand_id == brand_id)

    # 排序：按创建时间倒序
    query = query.order_by(Product.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    products = result.scalars().all()

    return [ProductResponse(
        id=p.id,
        product_code=p.product_code,
        product_name=p.product_name,
        product_remark=p.product_remark,
        status=p.status,
        category_id=p.category_id,
        brand_id=p.brand_id,
        cost_price=p.cost_price if _can_see_price(current_user, "cost_price") else None,
        retail_price=p.retail_price if _can_see_price(current_user, "retail_price") else None,
        min_price=p.min_price if _can_see_price(current_user, "min_price") else None,
        remark1=p.remark1,
        remark2=p.remark2,
        remark3=p.remark3,
        created_by=p.created_by,
        created_at=p.created_at,
        updated_at=p.updated_at
    ) for p in products]


@router.get("/{product_code}", response_model=ProductResponse)
async def get_product(
    product_code: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取商品详情
    权限要求：所有角色可查看
    """
    result = await db.execute(
        select(Product).where(Product.product_code == product_code)
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    return ProductResponse(
        id=product.id,
        product_code=product.product_code,
        product_name=product.product_name,
        product_remark=product.product_remark,
        status=product.status,
        category_id=product.category_id,
        brand_id=product.brand_id,
        cost_price=product.cost_price if _can_see_price(current_user, "cost_price") else None,
        retail_price=product.retail_price if _can_see_price(current_user, "retail_price") else None,
        min_price=product.min_price if _can_see_price(current_user, "min_price") else None,
        remark1=product.remark1,
        remark2=product.remark2,
        remark3=product.remark3,
        created_by=product.created_by,
        created_at=product.created_at,
        updated_at=product.updated_at
    )


def _can_see_price(user, key: str) -> bool:
    """按用户价格权限判断是否可见某价格字段（boss 恒可见；空权限=全掩码）。"""
    if getattr(user, "role", None) == "boss":
        return True
    perms = [x for x in (getattr(user, "price_permissions", "") or "").split(",") if x]
    return key in perms


@router.put("/{product_code}", response_model=ProductResponse)
async def update_product(
    product_code: str,
    product_data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    更新商品信息
    权限要求：boss（仅老板端可编辑商品）
    """
    # 权限检查：只有老板端可以编辑商品
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="您没有权限编辑商品")

    result = await db.execute(
        select(Product).where(Product.product_code == product_code)
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 更新字段
    update_data = product_data.model_dump(exclude_unset=True)
    changes = []
    
    for field, value in update_data.items():
        old_value = getattr(product, field)
        if old_value != value:
            changes.append(f"{field}: {old_value} -> {value}")
            setattr(product, field, value)

    await db.commit()
    await db.refresh(product)

    # 记录操作日志
    if changes:
        log = OperationLog(
            username=current_user.username,
            operation_type="更新商品",
            operation_content=f"更新商品 {product_code}，变更: {', '.join(changes)}"
        )
        db.add(log)
        await db.commit()

    return ProductResponse(
        id=product.id,
        product_code=product.product_code,
        product_name=product.product_name,
        product_remark=product.product_remark,
        status=product.status,
        category_id=product.category_id,
        brand_id=product.brand_id,
        cost_price=product.cost_price,
        retail_price=product.retail_price,
        min_price=product.min_price,
        remark1=product.remark1,
        remark2=product.remark2,
        remark3=product.remark3,
        created_by=product.created_by,
        created_at=product.created_at,
        updated_at=product.updated_at
    )


@router.delete("/{product_code}")
async def delete_product(
    product_code: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    删除商品
    权限要求：仅boss
    删除限制：已被订单引用的商品不允许删除
    """
    # 权限检查：只有老板端可以删除商品
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="您没有权限删除商品")

    result = await db.execute(
        select(Product).where(Product.product_code == product_code)
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 检查商品是否被订单引用（通过商品名称和编码双重匹配）
    from sqlalchemy import or_
    from ..models.models import Order
    order_result = await db.execute(
        select(Order).where(
            or_(
                Order.product_name == product.product_name,
                Order.product_name == product.product_code
            )
        ).limit(1)
    )
    referenced_order = order_result.scalar_one_or_none()
    
    if referenced_order:
        raise HTTPException(
            status_code=400, 
            detail=f"该商品已被订单引用（订单号：{referenced_order.order_id}），不允许删除"
        )

    # 删除商品（联动清理该商品的图片：数据库记录 + 磁盘文件 + 空文件夹）
    await delete_product_images(db, product.product_code)
    await db.delete(product)
    await db.commit()

    # 记录操作日志
    log = OperationLog(
        username=current_user.username,
        operation_type="删除商品",
        operation_content=f"删除商品 {product_code} - {product.product_name}"
    )
    db.add(log)
    await db.commit()

    return {"message": "商品删除成功"}


@router.post("/batch-delete")
async def batch_delete_products(
    product_codes: List[str],
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    批量删除商品
    权限要求：仅boss
    删除限制：已被订单引用的商品不允许删除
    """
    # 权限检查：只有老板端可以批量删除商品
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="您没有权限批量删除商品")

    if not product_codes:
        raise HTTPException(status_code=400, detail="请选择要删除的商品")

    deleted_count = 0
    failed_products = []
    
    for code in product_codes:
        result = await db.execute(
            select(Product).where(Product.product_code == code)
        )
        product = result.scalar_one_or_none()
        
        if product:
            # 检查商品是否被订单引用
            from ..models.models import Order
            order_result = await db.execute(
                select(Order).where(Order.product_name == product.product_name).limit(1)
            )
            referenced_order = order_result.scalar_one_or_none()
            
            if referenced_order:
                failed_products.append({
                    "product_code": code,
                    "product_name": product.product_name,
                    "reason": f"已被订单 {referenced_order.order_id} 引用"
                })
            else:
                # 联动清理该商品的图片（数据库记录 + 磁盘文件 + 空文件夹）
                await delete_product_images(db, code)
                await db.delete(product)
                deleted_count += 1

    await db.commit()

    # 记录操作日志
    log = OperationLog(
        username=current_user.username,
        operation_type="批量删除商品",
        operation_content=f"批量删除 {deleted_count} 个商品，失败 {len(failed_products)} 个"
    )
    db.add(log)
    await db.commit()

    # 构建返回消息
    message = f"成功删除 {deleted_count} 个商品"
    if failed_products:
        failed_names = [f"{p['product_name']}({p['reason']})" for p in failed_products]
        message += f"，以下商品无法删除：{', '.join(failed_names)}"

    return {
        "message": message,
        "deleted_count": deleted_count,
        "failed_count": len(failed_products),
        "failed_products": failed_products
    }


@router.get("/count/total")
async def get_product_count(
    keyword: str = Query(None, description="关键词（编码/名称模糊）"),
    status: str = Query(None, description="状态筛选"),
    category_id: int = Query(None, description="类别筛选"),
    brand_id: int = Query(None, description="品牌筛选"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取商品总数（支持与列表一致的筛选条件，用于分页）
    权限要求：所有角色可查看
    """
    count_query = select(func.count(Product.id))
    if keyword:
        count_query = count_query.where(
            or_(
                Product.product_code.like(f"%{keyword}%"),
                Product.product_name.like(f"%{keyword}%")
            )
        )
    if status:
        count_query = count_query.where(Product.status == status)
    if category_id is not None:
        count_query = count_query.where(Product.category_id == category_id)
    if brand_id is not None:
        count_query = count_query.where(Product.brand_id == brand_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 获取各状态商品数量（全量口径，用于统计卡片）
    active_result = await db.execute(
        select(func.count(Product.id)).where(Product.status == "active")
    )
    active_count = active_result.scalar()
    
    inactive_result = await db.execute(
        select(func.count(Product.id)).where(Product.status == "inactive")
    )
    inactive_count = inactive_result.scalar()

    return {
        "total": total,
        "active": active_count,
        "inactive": inactive_count
    }