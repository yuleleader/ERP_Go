# -*- coding: utf-8 -*-
"""
商品图片 API
- 上传：POST /api/products/{product_code}/images   （multipart, 最多 5 张）
- 列表：GET  /api/products/{product_code}/images
- 删除：DELETE /api/products/images/{image_id}

文件保存路径：backend/data/images/product/{product_code}/{uuid}.{ext}
Web URL 路径：/data/images/product/{product_code}/{filename}（走 images.serve_router 鉴权）
"""
import os
import uuid
from pathlib import Path

from aiofiles import open as aio_open
from aiofiles.os import makedirs, remove as aio_remove
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.security import get_current_active_user
from ..models.models import Product, ProductImage, OperationLog

router = APIRouter(prefix="/api/products", tags=["商品图片"])

BASE_DIR = Path(__file__).parent.parent.parent
IMAGE_ROOT = BASE_DIR / "data" / "images"
PRODUCT_IMAGE_DIR = IMAGE_ROOT / "product"
WEB_PREFIX = "/data/images"

MAX_IMAGES_PER_PRODUCT = 5
ALLOWED_EXTS = {".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

PRODUCT_IMAGE_DIR.mkdir(parents=True, exist_ok=True)


def _sanitize_code(code: str) -> str:
    """防止路径遍历"""
    import re
    s = re.sub(r"[\.]{2,}|[/\\]", "_", code)
    return s.strip("._") or "unknown"


async def delete_product_images(db: AsyncSession, product_code: str) -> int:
    """删除某商品的全部图片：数据库记录 + 磁盘文件 + 空文件夹。

    供删除商品（products.py）时联动调用，返回删除的图片记录数。
    """
    safe_code = _sanitize_code(product_code)
    rows = (await db.execute(
        select(ProductImage).where(ProductImage.product_code == safe_code)
    )).scalars().all()

    dir_path = PRODUCT_IMAGE_DIR / safe_code
    for row in rows:
        try:
            url = row.image_url or ""
            rel = url[len(WEB_PREFIX):].lstrip("/") if url.startswith(WEB_PREFIX) else None
            if rel:
                file_path = (IMAGE_ROOT / rel).resolve()
                file_path.relative_to(IMAGE_ROOT.resolve())  # 防路径穿越
                if file_path.is_file():
                    await aio_remove(str(file_path))
        except Exception:
            pass  # 文件不存在/被占用不影响数据库清理
        await db.delete(row)

    # 尝试删除商品图片空文件夹（非空或失败则忽略）
    try:
        if dir_path.is_dir() and not any(dir_path.iterdir()):
            dir_path.rmdir()
    except Exception:
        pass

    return len(rows)


@router.post("/{product_code}/images")
async def upload_product_image(
    product_code: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """上传一张商品图片。校验：商品存在 / 扩展名 / 大小 / 总数 ≤ 5。"""
    if current_user.role not in ("boss", "sales"):
        raise HTTPException(status_code=403, detail="您没有权限上传商品图片")

    safe_code = _sanitize_code(product_code)

    # 商品存在性
    p_row = (await db.execute(
        select(Product).where(Product.product_code == safe_code)
    )).scalar_one_or_none()
    if not p_row:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 数量上限
    cnt = (await db.execute(
        select(func.count(ProductImage.id)).where(ProductImage.product_code == safe_code)
    )).scalar() or 0
    if cnt >= MAX_IMAGES_PER_PRODUCT:
        raise HTTPException(status_code=400, detail=f"每个商品最多上传 {MAX_IMAGES_PER_PRODUCT} 张图片")

    # 校验扩展名 + 大小
    ext = os.path.splitext(file.filename or "")[-1].lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail="仅支持 jpg、jpeg、png 格式")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="图片不能超过 5MB")

    # 落盘
    target_dir = PRODUCT_IMAGE_DIR / safe_code
    await makedirs(target_dir, exist_ok=True)
    file_name = f"{uuid.uuid4()}{ext}"
    save_path = target_dir / file_name
    async with aio_open(save_path, "wb") as f:
        await f.write(content)

    # 写库
    image = ProductImage(
        product_code=safe_code,
        image_url=f"{WEB_PREFIX}/product/{safe_code}/{file_name}",
        file_name=file_name,
        sort_order=cnt,
        uploaded_by=current_user.username,
    )
    db.add(image)
    await db.commit()
    await db.refresh(image)

    # 操作日志
    db.add(OperationLog(
        username=current_user.username,
        operation_type="上传商品图片",
        operation_content=f"上传商品图片 {safe_code} -> {file_name}",
    ))
    await db.commit()

    return {
        "id": image.id,
        "product_code": image.product_code,
        "image_url": image.image_url,
        "sort_order": image.sort_order,
        "created_at": image.created_at.isoformat() if image.created_at else None,
    }


@router.get("/{product_code}/images")
async def list_product_images(
    product_code: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    safe_code = _sanitize_code(product_code)
    rows = (await db.execute(
        select(ProductImage)
        .where(ProductImage.product_code == safe_code)
        .order_by(ProductImage.sort_order.asc(), ProductImage.id.asc())
    )).scalars().all()
    return {
        "product_code": safe_code,
        "total": len(rows),
        "data": [
            {
                "id": r.id,
                "product_code": r.product_code,
                "image_url": r.image_url,
                "sort_order": r.sort_order,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


@router.delete("/images/{image_id}")
async def delete_product_image(
    image_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    if current_user.role not in ("boss", "sales"):
        raise HTTPException(status_code=403, detail="您没有权限删除商品图片")

    row = (await db.execute(
        select(ProductImage).where(ProductImage.id == image_id)
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="商品图片不存在")

    # 从磁盘删除文件
    try:
        url = row.image_url or ""
        rel = url[len(WEB_PREFIX):].lstrip("/") if url.startswith(WEB_PREFIX) else None
        if rel:
            file_path = (IMAGE_ROOT / rel).resolve()
            file_path.relative_to(IMAGE_ROOT.resolve())  # 防穿越
            if file_path.is_file():
                await aio_remove(str(file_path))
    except Exception:
        pass  # 文件不存在不影响数据库清理

    await db.delete(row)
    await db.commit()

    db.add(OperationLog(
        username=current_user.username,
        operation_type="删除商品图片",
        operation_content=f"删除商品图片 id={image_id} ({row.image_url})",
    ))
    await db.commit()

    return {"message": "商品图片删除成功", "id": image_id}