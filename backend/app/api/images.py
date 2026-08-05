# -*- coding: utf-8 -*-
import os
import hashlib 
import uuid 
from datetime import datetime, timedelta 
from ..models.models import beijing_now
from pathlib import Path 
import asyncio

from aiofiles import open as aio_open 
from aiofiles.os import rename, makedirs, listdir, stat, remove as aio_remove
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException 
from sqlalchemy.ext.asyncio import AsyncSession 
from sqlalchemy import select, update, func 

from app.core.database import get_db 
from app.core.security import get_current_active_user 
from app.models.models import Image, User, Order, OperationLog 
from app.services.notification_service import NotificationService 

router = APIRouter(prefix="/api/images", tags=["图片管理"]) 

# ====================== 目录配置（我们约定的最终结构）====================== 
BASE_DIR = Path(__file__).parent.parent.parent 
IMAGE_ROOT = BASE_DIR / "data" / "images" 
TEMP_DIR = IMAGE_ROOT / "temp" 
OFFICIAL_DIR = IMAGE_ROOT / "official" 

# 自动创建目录 
TEMP_DIR.mkdir(parents=True, exist_ok=True) 
OFFICIAL_DIR.mkdir(parents=True, exist_ok=True) 

# 前端访问路径 
WEB_PREFIX = "/data/images" 

# ====================== 系统规则（我们约定的配置）====================== 
MAX_SIZE = 5 * 1024 * 1024  # 5MB 
ALLOWED_EXTS = {".jpg", ".jpeg", ".png"} 
EXPIRE_HOURS = 48  # 临时图48小时过期 


# ====================== 工具函数 ====================== 
def get_layer_by_role(role: str) -> str: 
    """根据用户角色自动获取图片目录层（兼容旧逻辑）""" 
    if role == "sales": 
        return "sales" 
    elif role == "factory": 
        return "factory" 
    elif role == "shipping": 
        return "shipping" 
    elif role == "boss": 
        return "sales"  # 管理员默认归 sales 
    return "sales" 
 

def get_layer_by_module(module: str) -> str: 
    """根据上传模块确定文件夹，而非用户角色""" 
    module_map = { 
        "product": "sales",      # 商品图片 → sales文件夹 
        "production": "factory", # 生产进度 → factory文件夹 
        "shipping": "shipping"   # 发货凭证 → shipping文件夹 
    } 
    return module_map.get(module, "sales")  # 默认sales 
 

def calculate_md5(content: bytes) -> str: 
    return hashlib.md5(content).hexdigest() 


def validate_file(filename: str, size: int): 
    ext = os.path.splitext(filename)[-1].lower() 
    if ext not in ALLOWED_EXTS: 
        raise HTTPException(400, "仅支持 jpg、jpeg、png 格式") 
    if size > MAX_SIZE: 
        raise HTTPException(400, "图片不能超过 5MB") 


def sanitize_path_component(name: str) -> str:
    """防止路径遍历攻击：移除 ..  /  \\ 等危险字符"""
    import re
    sanitized = re.sub(r'[\.]{2,}|[/\\]', '_', name)
    return sanitized.strip('._') or 'unknown'


# ====================== 接口1：临时上传（创建订单前）====================== 
@router.post("/upload-temp") 
async def upload_temp( 
    file: UploadFile = File(...), 
    module: str = None, 
    current_user: User = Depends(get_current_active_user), 
    db: AsyncSession = Depends(get_db) 
): 
    validate_file(file.filename, file.size) 
    content = await file.read() 
    file_hash = calculate_md5(content) 
    ext = os.path.splitext(file.filename)[-1].lower() 
    filename = f"{uuid.uuid4()}{ext}" 
    save_path = TEMP_DIR / filename 
 
    async with aio_open(save_path, "wb") as f: 
        await f.write(content) 
 
    temp_id = str(uuid.uuid4()) 
    # 优先使用前端传递的module确定文件夹，否则使用用户角色默认值 
    if module: 
        layer = get_layer_by_module(module) 
        image_type = module 
    else: 
        layer = get_layer_by_role(current_user.role) 
        image_type = "product" 
 
    image = Image(
        temp_id=temp_id,
        order_id=None,
        layer=layer,
        image_url=f"{WEB_PREFIX}/temp/{filename}",
        image_hash=file_hash,
        uploaded_by=current_user.username,
        image_type=image_type
    ) 
    db.add(image) 
    await db.commit() 
    await db.refresh(image) 
 
    return { 
        "code": 200, 
        "temp_id": temp_id, 
        "url": image.image_url, 
        "layer": layer 
    } 


# ====================== 接口2：直接上传（已有订单）====================== 
@router.post("/upload-direct/{order_id}") 
async def upload_direct( 
    order_id: str, 
    file: UploadFile = File(...), 
    module: str = None, 
    current_user: User = Depends(get_current_active_user), 
    db: AsyncSession = Depends(get_db) 
): 
    validate_file(file.filename, file.size) 
    content = await file.read() 
    file_hash = calculate_md5(content) 
    ext = os.path.splitext(file.filename)[-1].lower() 
    filename = f"{uuid.uuid4()}{ext}" 
    
    # 优先使用前端传递的module确定文件夹，否则使用用户角色默认值 
    if module: 
        layer = get_layer_by_module(module) 
        image_type = module 
    else: 
        layer = get_layer_by_role(current_user.role) 
        image_type = "product" 
 
    target_dir = OFFICIAL_DIR / sanitize_path_component(order_id) / layer 
    await makedirs(target_dir, exist_ok=True) 
    save_path = target_dir / filename 
 
    async with aio_open(save_path, "wb") as f: 
        await f.write(content) 
 
    image = Image(
        temp_id=None,
        order_id=order_id,
        layer=layer,
        image_url=f"{WEB_PREFIX}/official/{sanitize_path_component(order_id)}/{layer}/{filename}",
        image_hash=file_hash,
        uploaded_by=current_user.username,
        image_type=image_type
    ) 
    db.add(image) 
    await db.commit() 
    await db.refresh(image) 

    if current_user.role == "factory" and layer == "factory":
        order_result = await db.execute(select(Order).where(Order.order_id == order_id))
        order = order_result.scalar_one_or_none()
        if order and order.produce_status != "producing":
            old_status = order.produce_status
            order.produce_status = "producing"
            order.produce_status_update_at = beijing_now()
            order.produce_status_update_user = "system-auto"
            
            log = OperationLog(
                username="system-auto",
                operation_type="update_produce_status",
                operation_content=f"系统自动更新：工厂上传生产图片，订单生产状态由{old_status}变更为生产中"
            )
            db.add(log)
            
            await NotificationService.send_produce_status_notification(
                db=db,
                order=order,
                new_status="producing",
                operator="system-auto",
                change_type="factory_image"
            )
            
            await db.commit()

    return {"code": 200, "url": image.image_url} 


# ====================== 接口3：迁移临时图到正式目录 ====================== 
@router.post("/migrate/{temp_id}/{order_id}") 
async def migrate_image( 
    temp_id: str, 
    order_id: str, 
    current_user: User = Depends(get_current_active_user), 
    db: AsyncSession = Depends(get_db) 
): 
    result = await db.execute(select(Image).where(Image.temp_id == temp_id))
    img = result.scalar_one_or_none()
    if not img: 
        raise HTTPException(404, "临时图片不存在") 

    layer = img.layer 
    filename = os.path.basename(img.image_url) 
    src = TEMP_DIR / filename 
    target_dir = OFFICIAL_DIR / sanitize_path_component(order_id) / layer 
    await makedirs(target_dir, exist_ok=True) 
    dst = target_dir / filename 

    try: 
        await rename(str(src), str(dst)) 
    except Exception as e: 
        raise HTTPException(500, f"文件迁移失败: {str(e)}") 

    img.order_id = order_id 
    img.temp_id = None 
    img.image_url = f"{WEB_PREFIX}/official/{sanitize_path_component(order_id)}/{layer}/{filename}" 
    await db.commit() 
    await db.refresh(img) 

    # 发送图片上传完成通知给订单创建人
    await NotificationService.send_image_uploaded_notification(db=db, order_id=order_id)

    if current_user.role == "factory" and layer == "factory":
        order_result = await db.execute(select(Order).where(Order.order_id == order_id))
        order = order_result.scalar_one_or_none()
        if order and order.produce_status != "producing":
            old_status = order.produce_status
            order.produce_status = "producing"
            order.produce_status_update_at = beijing_now()
            order.produce_status_update_user = "system-auto"
            
            log = OperationLog(
                username="system-auto",
                operation_type="update_produce_status",
                operation_content=f"系统自动更新：工厂上传生产图片，订单生产状态由{old_status}变更为生产中"
            )
            db.add(log)
            
            await NotificationService.send_produce_status_notification(
                db=db,
                order=order,
                new_status="producing",
                operator="system-auto",
                change_type="factory_image"
            )
            
            await db.commit()

    return {"code": 200, "msg": "迁移成功"} 


# ====================== 接口4：48小时临时图清理 ====================== 
@router.post("/clean-temp") 
async def clean_temp_files(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
): 
    now = datetime.now() 
    expire_time = now - timedelta(hours=EXPIRE_HOURS) 

    try:
        files = await listdir(TEMP_DIR)
        for f in files: 
            path = TEMP_DIR / f 
            file_stat = await stat(path)
            ctime = datetime.fromtimestamp(file_stat.st_ctime) 
            if ctime < expire_time: 
                try: 
                    await aio_remove(path) 
                    result = await db.execute(
                        select(Image).filter(
                            Image.image_url.endswith(f), 
                            Image.order_id.is_(None) 
                        )
                    )
                    images_to_delete = result.scalars().all()
                    for img in images_to_delete:
                        await db.delete(img)
                except Exception: 
                    continue 
        await db.commit() 
    except Exception as e:
        pass
    
    return {"code": 200, "msg": "清理完成"}


# ====================== 接口5：获取订单所有图片 ====================== 
@router.get("/list/{order_id}") 
async def get_order_image_list( 
    order_id: str, 
    current_user: User = Depends(get_current_active_user), 
    db: AsyncSession = Depends(get_db) 
): 
    # 查询该订单下所有已迁移正式图片 
    result = await db.execute(
        select(Image).filter(Image.order_id == order_id).order_by(Image.created_at.desc())
    )
    img_list = result.scalars().all()

    res = [] 
    for img in img_list: 
        res.append({ 
            "id": img.id, 
            "layer": img.layer, 
            "image_url": img.image_url, 
            "is_main": img.is_main, 
            "upload_time": img.created_at 
        }) 
    return {"code": 200, "data": res}


# ====================== 接口6：删除单张图片（删数据库记录 + 删本地文件）======================
@router.delete("/delete/{img_id}")
async def delete_image(
    img_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # 查找图片记录
    result = await db.execute(select(Image).filter(Image.id == img_id))
    img = result.scalar_one_or_none()
    if not img:
        raise HTTPException(status_code=404, detail="图片不存在")

    # 权限简易控制：只能删自己上传的；管理员可删所有
    if current_user.role != "boss" and img.uploaded_by != current_user.username:
        raise HTTPException(status_code=403, detail="无权删除该图片")

    # 删物理文件（使用安全的路径解析防止路径遍历）
    file_rel_path = img.image_url.replace(WEB_PREFIX, str(IMAGE_ROOT))
    file_path = Path(os.path.normpath(file_rel_path))
    # 确保解析后的路径仍在 IMAGE_ROOT 之下
    try:
        file_path.resolve().relative_to(IMAGE_ROOT.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="图片路径异常，无法删除")
    if file_path.is_file():
        try:
            await aio_remove(file_path)
        except Exception:
            pass

    # 删数据库记录
    await db.delete(img)
    await db.commit()
    return {"code": 200, "msg": "图片已删除"}


# ====================== 接口7：设置为订单主图（同订单只能有一张主图）======================
@router.post("/set-main/{img_id}")
async def set_main_image(
    img_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Image).filter(Image.id == img_id))
    img = result.scalar_one_or_none()
    if not img or not img.order_id:
        raise HTTPException(status_code=404, detail="图片不存在或未关联订单")

    # 权限校验
    if current_user.role != "boss" and img.uploaded_by != current_user.username:
        raise HTTPException(status_code=403, detail="无权操作")

    # 先把该订单所有图片置为非主图
    await db.execute(
        update(Image).where(Image.order_id == img.order_id).values(is_main=0)
    )

    # 当前设为主图
    img.is_main = 1
    await db.commit()
    await db.refresh(img)
    return {"code": 200, "msg": "已设为主图"}


# ====================== 接口8：获取图片统计 ======================
@router.get("/stats")
async def get_image_stats(
    layer: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = select(func.count(Image.id)).filter(Image.order_id.isnot(None))
    if layer:
        query = query.filter(Image.layer == layer)
    
    result = await db.execute(query)
    count = result.scalar() or 0
    
    return {"code": 200, "count": count}
