# -*- coding: utf-8 -*-
"""
站内信通知API接口
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from ..core.database import get_db
from ..core.security import get_current_active_user, ensure_data_permission
from ..services.notification_service import NotificationService
from ..models.models import User

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@router.get("/")
async def get_notifications(
    order_id: Optional[str] = Query(None, description="按订单ID筛选"),
    event_type: Optional[str] = Query(None, description="按事件类型筛选"),
    is_read: Optional[bool] = Query(None, description="按阅读状态筛选"),
    keyword: Optional[str] = Query(None, description="模糊搜索关键词（匹配标题、内容、订单号）"),
    skip: int = Query(0, description="跳过数量"),
    limit: int = Query(50, description="返回数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    查询站内信列表
    
    支持按订单ID、事件类型、阅读状态筛选，以及关键词模糊搜索
    """
    result = await NotificationService.get_notifications(
        db=db,
        recipient_username=current_user.username,
        order_id=order_id,
        event_type=event_type,
        is_read=is_read,
        keyword=keyword,
        skip=skip,
        limit=limit
    )
    
    # 转换为字典列表
    notifications = []
    for item in result['items']:
        notifications.append({
            'id': item.id,
            'order_id': item.order_id,
            'event_type': item.event_type,
            'title': item.title,
            'content': item.content,
            'is_read': item.is_read,
            'read_at': item.read_at,
            'created_at': item.created_at
        })
    
    return {
        'total': result['total'],
        'items': notifications,
        'skip': result['skip'],
        'limit': result['limit']
    }

@router.get("/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取未读消息数量
    """
    count = await NotificationService.get_unread_count(
        db=db,
        recipient_username=current_user.username
    )
    
    return {'unread_count': count}

@router.put("/{notification_id}/read")
async def mark_as_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    标记单条消息为已读
    """
    success = await NotificationService.mark_as_read(
        db=db,
        notification_id=notification_id,
        recipient_username=current_user.username
    )
    
    if success:
        return {'message': '标记成功'}
    else:
        return {'message': '标记失败，通知不存在或不属于当前用户'}

@router.put("/all/read")
async def mark_all_as_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    标记所有消息为已读
    """
    count = await NotificationService.mark_all_as_read(
        db=db,
        recipient_username=current_user.username
    )
    
    return {'message': f'成功标记 {count} 条消息为已读'}

@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    删除单条消息
    """
    ensure_data_permission(current_user, '/notifications', 'delete')
    success = await NotificationService.delete_notification(
        db=db,
        notification_id=notification_id,
        recipient_username=current_user.username
    )
    
    if success:
        return {'message': '删除成功'}
    else:
        return {'message': '删除失败，通知不存在或不属于当前用户'}