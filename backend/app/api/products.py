# -*- coding: utf-8 -*-
"""
商品管理API模块
提供商品的增删改查功能，支持分页、搜索、筛选
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional, List
from ..core.database import get_db
from ..core.security import get_current_active_user
from ..models.models import Product, User, OperationLog
from ..schemas.schemas import ProductCreate, ProductUpdate, ProductResponse

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
    权限要求：boss、sales
    """
    # 权限检查：只有老板端和销售端可以创建商品
    if current_user.role not in ["boss", "sales"]:
        raise HTTPException(status_code=403, detail="您没有权限创建商品")

    # 生成商品编码（顺序编号：PLU-000001）
    product_code = await generate_product_code(db)

    # 创建商品记录
    new_product = Product(
        product_code=product_code,
        product_name=product_data.product_name,
        product_remark=product_data.product_remark,
        status="active",
        created_by=current_user.username
    )
    
    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)

    # 记录操作日志
    log = OperationLog(
        username=current_user.username,
        operation_type="创建商品",
        operation_content=f"创建商品 {product_code} - {product_data.product_name}"
    )
    db.add(log)
    await db.commit()

    return ProductResponse(
        id=new_product.id,
        product_code=new_product.product_code,
        product_name=new_product.product_name,
        product_remark=new_product.product_remark,
        status=new_product.status,
        created_by=new_product.created_by,
        created_at=new_product.created_at,
        updated_at=new_product.updated_at
    )


@router.get("/", response_model=List[ProductResponse])
async def get_products(
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取商品列表
    支持分页、关键词搜索、状态筛选
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
        created_by=product.created_by,
        created_at=product.created_at,
        updated_at=product.updated_at
    )


@router.put("/{product_code}", response_model=ProductResponse)
async def update_product(
    product_code: str,
    product_data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    更新商品信息
    权限要求：boss、sales
    """
    # 权限检查：只有老板端和销售端可以编辑商品
    if current_user.role not in ["boss", "sales"]:
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

    # 删除商品
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
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取商品总数
    权限要求：所有角色可查看
    """
    result = await db.execute(select(func.count(Product.id)))
    total = result.scalar()
    
    # 获取各状态商品数量
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