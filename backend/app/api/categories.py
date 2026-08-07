# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from ..core.database import get_db
from ..core.security import get_current_active_user, ensure_data_permission
from ..models.models import Category, Product, OperationLog
from ..schemas.schemas import CategoryCreate, CategoryUpdate, CategoryResponse

router = APIRouter(prefix="/api/categories", tags=["类别管理"])

CODE_WIDTH = 3  # 每一级编码占三位，如一级 002、二级 002001


async def _next_root_code(db: AsyncSession) -> str:
    """生成下一个一级类别编码（三位补零）"""
    result = await db.execute(select(Category.category_code).where(Category.level == 1))
    codes = [str(c) for c in result.scalars().all() if c]
    max_seq = 0
    for code in codes:
        try:
            max_seq = max(max_seq, int(code[:CODE_WIDTH]))
        except ValueError:
            continue
    return str(max_seq + 1).zfill(CODE_WIDTH)


async def _next_child_code(db: AsyncSession, parent: Category) -> str:
    """生成下一个二级类别编码：父编码 + 三位序号，如 002001"""
    result = await db.execute(select(Category.category_code).where(Category.parent_id == parent.id))
    codes = [str(c) for c in result.scalars().all() if c]
    max_seq = 0
    for code in codes:
        try:
            max_seq = max(max_seq, int(code[CODE_WIDTH:]))
        except ValueError:
            continue
    return f"{parent.category_code}{str(max_seq + 1).zfill(CODE_WIDTH)}"


def _to_tree(rows: List[Category]) -> List[CategoryResponse]:
    """把平铺列表组装成两级树"""
    nodes = {}
    for row in rows:
        item = CategoryResponse.model_validate(row)
        item.children = []
        nodes[row.id] = item

    tree: List[CategoryResponse] = []
    for row in rows:
        item = nodes[row.id]
        parent = nodes.get(row.parent_id) if row.parent_id else None
        if parent:
            parent.children.append(item)
        else:
            tree.append(item)

    tree.sort(key=lambda x: x.category_code)
    for item in tree:
        item.children.sort(key=lambda x: x.category_code)
    return tree


@router.get("/", response_model=List[CategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """返回两级类别树"""
    result = await db.execute(select(Category).order_by(Category.category_code))
    return _to_tree(list(result.scalars().all()))


@router.post("/", response_model=CategoryResponse)
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    ensure_data_permission(current_user, 'category', 'add')

    parent = None
    if data.parent_id:
        result = await db.execute(select(Category).where(Category.id == data.parent_id))
        parent = result.scalar_one_or_none()
        if not parent:
            raise HTTPException(status_code=404, detail="上级类别不存在")
        if parent.level >= 2:
            raise HTTPException(status_code=400, detail="仅支持两级类别，二级类别下不能再建子类别")

    if parent:
        code = await _next_child_code(db, parent)
        level = 2
    else:
        code = await _next_root_code(db)
        level = 1

    cat = Category(
        category_code=code,
        category_name=data.category_name,
        parent_id=parent.id if parent else None,
        level=level,
        created_by=current_user.username
    )
    db.add(cat)
    db.add(OperationLog(
        username=current_user.username,
        operation_type="创建类别",
        operation_content=f"创建{'二级' if level == 2 else '一级'}类别 {code} {data.category_name}"
    ))
    await db.commit()
    await db.refresh(cat)
    return cat


@router.put("/{cat_id}", response_model=CategoryResponse)
async def update_category(
    cat_id: int,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    ensure_data_permission(current_user, 'category', 'edit')

    result = await db.execute(select(Category).where(Category.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="类别不存在")

    if data.category_name is not None:
        cat.category_name = data.category_name

    await db.commit()
    await db.refresh(cat)
    return cat


@router.delete("/{cat_id}", status_code=200)
async def delete_category(
    cat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    ensure_data_permission(current_user, 'category', 'delete')

    result = await db.execute(select(Category).where(Category.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="类别不存在")

    child_result = await db.execute(select(Category.id).where(Category.parent_id == cat_id))
    if child_result.scalars().first():
        raise HTTPException(status_code=400, detail="该类别下存在子类别，请先删除子类别")

    # 检查是否有商品引用该类别，防止产生孤儿数据
    product_ref = await db.execute(select(Product.id).where(Product.category_id == cat_id).limit(1))
    if product_ref.scalars().first():
        raise HTTPException(status_code=400, detail="该类别下存在关联商品，无法删除。请先移除或转移商品")

    db.add(OperationLog(
        username=current_user.username,
        operation_type="删除类别",
        operation_content=f"删除类别 {cat.category_code} {cat.category_name}"
    ))
    await db.delete(cat)
    await db.commit()
    return {"message": "类别删除成功"}
