# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import List, Optional
from datetime import datetime
from ..core.database import get_db
from ..core.security import get_current_active_user, require_role
from ..models.models import (
    OperationLog,
    LoginLog,
    User,
    LogCleanupRecord
)
from ..services.log_cleanup import (
    LogCleanupService,
    DEFAULT_RETENTION_DAYS,
    NOTIFICATION_DEFAULT_RETENTION_DAYS
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/logs", tags=["日志管理"])

@router.get("/operations")
async def get_operation_logs(
    username: Optional[str] = None,
    operation_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("boss"))
):
    # 构建查询
    query = select(OperationLog)

    if username:
        query = query.where(OperationLog.username.like(f"%{username}%"))
    if operation_type:
        query = query.where(OperationLog.operation_type == operation_type)
    if start_date:
        query = query.where(OperationLog.created_at >= datetime.strptime(start_date, "%Y-%m-%d"))
    if end_date:
        query = query.where(OperationLog.created_at <= datetime.strptime(end_date + " 23:59:59", "%Y-%m-%d %H:%M:%S"))

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 获取分页数据
    query = query.order_by(desc(OperationLog.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()

    log_responses = []
    for log in logs:
        log_dict = {
            "id": log.id,
            "username": log.username,
            "operation_type": log.operation_type,
            "operation_content": log.operation_content,
            "ip_address": log.ip_address,
            "created_at": log.created_at
        }
        if log.username:
            creator_result = await db.execute(
                select(User.real_name).where(User.username == log.username)
            )
            log_dict["real_name"] = creator_result.scalar() or log.username
        else:
            log_dict["real_name"] = log.username
        log_responses.append(log_dict)

    return {
        "items": log_responses,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.get("/login", response_model=List[dict])
async def get_login_logs(
    username: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("boss"))
):
    query = select(LoginLog)

    if username:
        query = query.where(LoginLog.username.like(f"%{username}%"))
    if status:
        query = query.where(LoginLog.status == status)

    query = query.order_by(desc(LoginLog.login_time)).offset(skip).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        {
            "id": log.id,
            "username": log.username,
            "login_time": log.login_time,
            "ip_address": log.ip_address,
            "status": log.status
        }
        for log in logs
    ]

@router.post("/migrate-history")
async def migrate_history_logs(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("boss"))
):
    """临时接口：迁移历史日志数据，将'操作用户ID=1'格式改为'操作用户=真实姓名'"""
    import re
    
    # 获取所有用户映射
    user_result = await db.execute(select(User))
    users = user_result.scalars().all()
    user_map = {str(user.id): user.real_name or user.username for user in users}
    
    # 获取所有日志
    log_result = await db.execute(select(OperationLog))
    logs = log_result.scalars().all()
    
    updated_count = 0
    for log in logs:
        if log.operation_content:
            # 匹配"操作用户ID=数字"格式
            match = re.search(r'操作用户ID=(\d+)', log.operation_content)
            if match:
                user_id = match.group(1)
                real_name = user_map.get(user_id, user_id)
                # 替换为"操作用户=真实姓名"
                new_content = re.sub(
                    r'操作用户ID=\d+',
                    f'操作用户={real_name}',
                    log.operation_content
                )
                log.operation_content = new_content
                
                # 同时更新username字段
                if log.user_id:
                    for user in users:
                        if user.id == log.user_id:
                            log.username = user.username
                            break
                
                updated_count += 1
    
    await db.commit()
    return {"message": f"成功更新 {updated_count} 条日志记录"}


# ==================== 日志清理管理接口 ====================

@router.get("/cleanup/config")
async def get_cleanup_config(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("boss"))
):
    """获取日志清理配置"""
    retention_days = await LogCleanupService.get_retention_days(db)
    cutoff_date = LogCleanupService.calculate_cutoff_date(retention_days)
    counts = await LogCleanupService.count_old_logs(db, cutoff_date)

    return {
        "retention_days": retention_days,
        "cutoff_date": cutoff_date,
        "pending_deletion": counts
    }


@router.put("/cleanup/config")
async def update_cleanup_config(
    retention_days: int = Query(..., description="保留天数，最小30天"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("boss"))
):
    """更新日志清理配置"""
    try:
        username = getattr(current_user, "username", "unknown")
        await LogCleanupService.set_retention_days(db, retention_days, username)

        cutoff_date = LogCleanupService.calculate_cutoff_date(retention_days)
        counts = await LogCleanupService.count_old_logs(db, cutoff_date)

        return {
            "success": True,
            "retention_days": retention_days,
            "cutoff_date": cutoff_date,
            "pending_deletion": counts
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cleanup/preview")
async def preview_cleanup(
    retention_days: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("boss"))
):
    """
    预览日志清理效果
    返回将要删除的日志数量统计，不实际删除
    """
    if retention_days:
        if retention_days < 30:
            raise HTTPException(status_code=400, detail="保留天数不能小于30天")
    else:
        retention_days = await LogCleanupService.get_retention_days(db)

    cutoff_date = LogCleanupService.calculate_cutoff_date(retention_days)
    counts = await LogCleanupService.count_old_logs(db, cutoff_date)

    return {
        "retention_days": retention_days,
        "cutoff_date": cutoff_date,
        "operation_logs": counts["operation"],
        "login_logs": counts["login"],
        "total_logs": counts["total"]
    }


@router.post("/cleanup/execute")
async def execute_cleanup(
    cleanup_type: str = Query("all", description="清理类型: operation|login|all"),
    confirm: bool = Query(False, description="必须设为true以确认执行"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("boss"))
):
    """
    手动触发日志清理
    :param cleanup_type: 清理类型
    :param confirm: 必须确认才会执行
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="请设置 confirm=true 以确认执行清理操作"
        )

    if cleanup_type not in ["operation", "login", "all"]:
        raise HTTPException(
            status_code=400,
            detail="cleanup_type 必须是: operation|login|all"
        )

    try:
        username = getattr(current_user, "username", "unknown")
        result = await LogCleanupService.cleanup_logs(
            db,
            cleanup_type=cleanup_type,
            triggered_by="manual",
            operator_username=username
        )

        return result

    except Exception as e:
        logger.error(f"手动日志清理失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"日志清理执行失败: {str(e)}"
        )


@router.get("/cleanup/records")
async def get_cleanup_records(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("boss"))
):
    """获取日志清理操作记录"""
    result = await db.execute(
        select(LogCleanupRecord)
        .order_by(desc(LogCleanupRecord.start_time))
        .offset(skip)
        .limit(limit)
    )
    records = result.scalars().all()

    return [
        {
            "id": record.id,
            "cleanup_type": record.cleanup_type,
            "retention_days": record.retention_days,
            "deleted_count": record.deleted_count,
            "status": record.status,
            "error_message": record.error_message,
            "start_time": record.start_time,
            "end_time": record.end_time,
            "triggered_by": record.triggered_by,
            "operator_username": record.operator_username
        }
        for record in records
    ]


# ==================== 站内信清理管理接口 ====================

@router.get("/cleanup/notification/config")
async def get_notification_cleanup_config(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("boss"))
):
    """获取站内信清理配置"""
    retention_days = await LogCleanupService.get_notification_retention_days(db)
    cutoff_date = LogCleanupService.calculate_cutoff_date(retention_days)
    count = await LogCleanupService.count_old_notifications(db, cutoff_date)

    return {
        "retention_days": retention_days,
        "cutoff_date": cutoff_date,
        "pending_deletion": count
    }


@router.put("/cleanup/notification/config")
async def update_notification_cleanup_config(
    retention_days: int = Query(..., description="保留天数，最小360天"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("boss"))
):
    """更新站内信清理配置"""
    try:
        username = getattr(current_user, "username", "unknown")
        await LogCleanupService.set_notification_retention_days(db, retention_days, username)

        cutoff_date = LogCleanupService.calculate_cutoff_date(retention_days)
        count = await LogCleanupService.count_old_notifications(db, cutoff_date)

        return {
            "success": True,
            "retention_days": retention_days,
            "cutoff_date": cutoff_date,
            "pending_deletion": count
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cleanup/notification/preview")
async def preview_notification_cleanup(
    retention_days: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("boss"))
):
    """
    预览站内信清理效果
    返回将要删除的站内信数量，不实际删除
    """
    if retention_days:
        if retention_days < NOTIFICATION_DEFAULT_RETENTION_DAYS:
            raise HTTPException(
                status_code=400,
                detail=f"站内信保留天数不能小于{NOTIFICATION_DEFAULT_RETENTION_DAYS}天"
            )
    else:
        retention_days = await LogCleanupService.get_notification_retention_days(db)

    cutoff_date = LogCleanupService.calculate_cutoff_date(retention_days)
    count = await LogCleanupService.count_old_notifications(db, cutoff_date)

    return {
        "retention_days": retention_days,
        "cutoff_date": cutoff_date,
        "total_notifications": count
    }


@router.post("/cleanup/notification/execute")
async def execute_notification_cleanup(
    confirm: bool = Query(False, description="必须设为true以确认执行"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("boss"))
):
    """
    手动触发站内信清理
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="请设置 confirm=true 以确认执行清理操作"
        )

    try:
        username = getattr(current_user, "username", "unknown")
        result = await LogCleanupService.cleanup_notifications(
            db,
            triggered_by="manual",
            operator_username=username
        )

        return result

    except Exception as e:
        logger.error(f"手动站内信清理失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"站内信清理执行失败: {str(e)}"
        )
