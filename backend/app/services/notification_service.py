# -*- coding: utf-8 -*-
"""
站内信通知服务
负责站内信的发送、查询、状态管理等功能
"""
import logging
from datetime import datetime
from ..models.models import beijing_now
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from ..models.models import Notification, Order, User

logger = logging.getLogger(__name__)

PRODUCE_STATUS_MAP = {
    "unproduce": "未生产",
    "producing": "生产中",
    "produced": "生产完成"
}

EVENT_TYPES = {
    'image_uploaded': '图片上传完成',
    'order_shipped': '订单已发货',
    'order_created': '新订单提醒',
    'produce_status_changed': '生产状态变更',
    'order_refunded': '订单已退款',
    'order_deleted': '订单已删除',
}

class NotificationService:
    """站内信通知服务"""

    @staticmethod
    async def send_notification(
        db: AsyncSession,
        recipient_username: str,
        order_id: str,
        event_type: str,
        title: str,
        content: str
    ) -> bool:
        """
        发送站内信通知
        
        Args:
            db: 数据库会话
            recipient_username: 接收者用户名
            order_id: 关联订单ID
            event_type: 事件类型
            title: 消息标题
            content: 消息内容
        
        Returns:
            是否发送成功
        """
        try:
            # 检查是否已有相同事件通知（包括已读和未读），避免重复发送
            existing_count = await db.execute(
                select(func.count(Notification.id)).where(
                    and_(
                        Notification.recipient_username == recipient_username,
                        Notification.order_id == order_id,
                        Notification.event_type == event_type
                    )
                )
            )
            
            if existing_count.scalar_one() > 0:
                logger.info(f"用户 {recipient_username} 已有 {event_type} 通知，订单: {order_id}，跳过重复发送")
                return False
            
            # 创建新通知
            notification = Notification(
                recipient_username=recipient_username,
                order_id=order_id,
                event_type=event_type,
                title=title,
                content=content
            )

            # 用嵌套事务（SAVEPOINT）包裹通知写入：即使通知失败也只回滚自身，
            # 绝不连带回滚调用方已做的业务修改（如订单状态、操作日志等主事务）
            async with db.begin_nested():
                db.add(notification)
                await db.flush()
            logger.info(f"站内信发送成功，接收者: {recipient_username}，订单: {order_id}，事件类型: {event_type}")
            return True

        except Exception as e:
            logger.error(f"发送站内信失败: {e}")
            return False

    @staticmethod
    async def send_image_uploaded_notification(db: AsyncSession, order_id: str) -> bool:
        """
        发送图片上传完成通知
        
        Args:
            db: 数据库会话
            order_id: 订单ID
        
        Returns:
            是否发送成功
        """
        try:
            # 获取订单信息
            result = await db.execute(
                select(Order.created_by).where(Order.order_id == order_id)
            )
            creator_username = result.scalar_one_or_none()
            
            if not creator_username:
                logger.warning(f"无法找到订单 {order_id} 的创建人")
                return False
            
            event_type = 'image_uploaded'
            title = EVENT_TYPES[event_type]
            content = f"订单 {order_id} 的图片已上传完成。\n时间: {beijing_now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            return await NotificationService.send_notification(
                db=db,
                recipient_username=creator_username,
                order_id=order_id,
                event_type=event_type,
                title=title,
                content=content
            )
            
        except Exception as e:
            logger.error(f"发送图片上传通知失败: {e}")
            return False

    @staticmethod
    async def send_order_shipped_notification(db: AsyncSession, order_id: str, logistics_company: str = None, logistics_no: str = None, logistics_no_2: str = None) -> bool:
        """
        发送订单已发货通知
        
        Args:
            db: 数据库会话
            order_id: 订单ID
            logistics_company: 物流公司
            logistics_no: 物流单号（运单号1）
            logistics_no_2: 运单号2（选填）
        
        Returns:
            是否发送成功
        """
        try:
            # 获取订单信息
            result = await db.execute(
                select(Order.created_by).where(Order.order_id == order_id)
            )
            creator_username = result.scalar_one_or_none()
            
            if not creator_username:
                logger.warning(f"无法找到订单 {order_id} 的创建人")
                return False
            
            event_type = 'order_shipped'
            title = EVENT_TYPES[event_type]
            
            content = f"订单 {order_id} 已发货。\n"
            if logistics_company:
                content += f"物流公司: {logistics_company}\n"
            if logistics_no:
                content += f"运单号1: {logistics_no}\n"
            if logistics_no_2:
                content += f"运单号2: {logistics_no_2}\n"
            content += f"时间: {beijing_now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            return await NotificationService.send_notification(
                db=db,
                recipient_username=creator_username,
                order_id=order_id,
                event_type=event_type,
                title=title,
                content=content
            )
            
        except Exception as e:
            logger.error(f"发送订单发货通知失败: {e}")
            return False

    @staticmethod
    async def send_order_refunded_notification(
        db: AsyncSession,
        order: Order,
        operator: str
    ) -> bool:
        """
        订单状态被修改为「已退款」时，发送站内信给：
        - 订单创建人
        - 所有老板端(boss)账号

        Args:
            db: 数据库会话
            order: 订单对象（需已更新为 refunded 状态）
            operator: 操作人用户名

        Returns:
            是否至少成功发送一条
        """
        try:
            event_type = 'order_refunded'
            title = EVENT_TYPES[event_type]

            operator_info = await db.execute(
                select(User.real_name).where(User.username == operator)
            )
            operator_name = operator_info.scalar() or operator

            content = (
                f"订单【{order.order_id}】已被 {operator_name} 修改为【已退款】状态。\n"
                f"商品: {order.product_name or '无'}\n"
                f"退款备注: {order.refund_note or '无'}\n"
                f"时间: {beijing_now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            recipients = []
            if order.created_by:
                recipients.append(str(order.created_by))
            result = await db.execute(select(User.username).where(User.role == "boss"))
            recipients.extend(result.scalars().all())

            # 去重（创建人本身可能也是老板，避免重复给同一人发两条）
            seen = set()
            unique_recipients = [r for r in recipients if not (r in seen or seen.add(r))]

            success_count = 0
            for recipient in unique_recipients:
                await NotificationService.send_notification(
                    db=db,
                    recipient_username=recipient,
                    order_id=order.order_id,
                    event_type=event_type,
                    title=title,
                    content=content
                )
                success_count += 1

            logger.info(f"订单退款通知已发送，订单: {order.order_id}，接收人数: {success_count}")
            return success_count > 0
        except Exception as e:
            logger.error(f"发送订单退款通知失败: {e}")
            return False

    @staticmethod
    async def send_order_deleted_notification(
        db: AsyncSession,
        order_id: str,
        created_by: str,
        operator_name: str
    ) -> bool:
        """
        订单被删除时，发送站内信给：
        - 订单创建人
        - 所有老板端(boss)账号

        Args:
            db: 数据库会话
            order_id: 被删除订单的订单号
            created_by: 被删除订单的创建人用户名（删除前已取出）
            operator_name: 操作人显示名（真实姓名或用户名）

        Returns:
            是否至少成功发送一条
        """
        try:
            event_type = 'order_deleted'
            title = EVENT_TYPES[event_type]

            content = (
                f"订单【{order_id}】已被 {operator_name} 删除。\n"
                f"时间: {beijing_now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            recipients = []
            if created_by:
                recipients.append(str(created_by))
            result = await db.execute(select(User.username).where(User.role == "boss"))
            recipients.extend(result.scalars().all())

            # 去重（创建人本身可能也是老板）
            seen = set()
            unique_recipients = [r for r in recipients if not (r in seen or seen.add(r))]

            success_count = 0
            for recipient in unique_recipients:
                await NotificationService.send_notification(
                    db=db,
                    recipient_username=recipient,
                    order_id=order_id,
                    event_type=event_type,
                    title=title,
                    content=content
                )
                success_count += 1

            logger.info(f"订单删除通知已发送，订单: {order_id}，接收人数: {success_count}")
            return success_count > 0
        except Exception as e:
            logger.error(f"发送订单删除通知失败: {e}")
            return False

    @staticmethod
    async def send_order_created_notification(db: AsyncSession, order: Order, creator_name: str) -> bool:
        """
        发送新订单创建通知给工厂端用户
        
        Args:
            db: 数据库会话
            order: 订单对象
            creator_name: 创建人真实姓名
        
        Returns:
            是否发送成功
        """
        try:
            event_type = 'order_created'
            title = EVENT_TYPES[event_type]
            created_at_str = order.created_at.strftime('%Y-%m-%d %H:%M:%S') if order.created_at else ''
            content = f"{creator_name}创建了新订单【{order.order_id}】，\n【{order.product_name or '无'}】\n【{created_at_str}】\n订单号【{order.order_id}】"
            
            result = await db.execute(select(User.username).where(User.role == "factory"))
            factory_users = result.scalars().all()
            
            success_count = 0
            for recipient in factory_users:
                await NotificationService.send_notification(
                    db=db,
                    recipient_username=recipient,
                    order_id=order.order_id,
                    event_type=event_type,
                    title=title,
                    content=content
                )
                success_count += 1
            
            logger.info(f"新订单创建通知已发送，订单: {order.order_id}，工厂端接收人数: {success_count}")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"发送新订单创建通知失败: {e}")
            return False

    @staticmethod
    async def send_produce_status_notification(
        db: AsyncSession,
        order: Order,
        new_status: str,
        operator: str,
        change_type: str = "manual",
        old_status: str = None
    ) -> bool:
        """
        发送生产状态变更通知
        
        Args:
            db: 数据库会话
            order: 订单对象
            new_status: 新的生产状态
            operator: 操作人
            change_type: 变更类型 (manual/factory_image/shipping)
            old_status: 旧的生产状态（用于手动变更场景，避免因状态已修改导致文案错误）
        
        Returns:
            是否发送成功
        """
        try:
            new_status_display = PRODUCE_STATUS_MAP.get(new_status, new_status)
            old_status_display = PRODUCE_STATUS_MAP.get(old_status, old_status or order.produce_status)
            
            if change_type == "factory_image":
                title = "订单生产进度更新"
                content = f"订单【{order.order_id}】已上传生产实拍，当前生产状态更新为：{new_status_display}"
                recipients = []
                if order.created_by:
                    recipients.append(order.created_by)
                result = await db.execute(select(User.username).where(User.role == "factory"))
                factory_users = result.scalars().all()
                recipients.extend(factory_users)
                result = await db.execute(select(User.username).where(User.role == "boss"))
                boss_users = result.scalars().all()
                recipients.extend(boss_users)
            
            elif change_type == "shipping":
                title = "订单生产全部完成"
                content = f"订单【{order.order_id}】已完成发货，生产流程结束，生产状态固定为{new_status_display}"
                recipients = []
                if order.created_by:
                    recipients.append(order.created_by)
                result = await db.execute(select(User.username).where(User.role == "factory"))
                factory_users = result.scalars().all()
                recipients.extend(factory_users)
                result = await db.execute(select(User.username).where(User.role == "boss"))
                boss_users = result.scalars().all()
                recipients.extend(boss_users)
            
            else:
                title = "订单生产状态人工调整"
                operator_info = await db.execute(
                    select(User.real_name).where(User.username == operator)
                )
                operator_name = operator_info.scalar() or operator
                content = f"用户{operator_name}手动将订单【{order.order_id}】生产状态由{old_status_display}修改为{new_status_display}"
                recipients = []
                if order.created_by:
                    recipients.append(order.created_by)
                result = await db.execute(select(User.username).where(User.role == "boss"))
                boss_users = result.scalars().all()
                recipients.extend(boss_users)
            
            event_type = 'produce_status_changed'
            success_count = 0
            for recipient in recipients:
                await NotificationService.send_notification(
                    db=db,
                    recipient_username=recipient,
                    order_id=order.order_id,
                    event_type=f'{event_type}_{change_type}',
                    title=title,
                    content=content
                )
                success_count += 1
            
            logger.info(f"生产状态变更通知已发送，订单: {order.order_id}，接收人数: {success_count}")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"发送生产状态变更通知失败: {e}")
            return False

    @staticmethod
    async def get_notifications(
        db: AsyncSession,
        recipient_username: str,
        order_id: Optional[str] = None,
        event_type: Optional[str] = None,
        is_read: Optional[bool] = None,
        keyword: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Dict[str, any]:
        """
        查询站内信列表
        
        Args:
            db: 数据库会话
            recipient_username: 接收者用户名
            order_id: 订单ID筛选（可选）
            event_type: 事件类型筛选（可选）
            is_read: 阅读状态筛选（可选）
            keyword: 模糊搜索关键词（匹配标题、内容、订单号）
            skip: 跳过数量
            limit: 返回数量
        
        Returns:
            通知列表和总数
        """
        try:
            query = select(Notification).where(
                Notification.recipient_username == recipient_username
            )
            
            if order_id:
                query = query.where(Notification.order_id == order_id)
            
            if event_type:
                query = query.where(Notification.event_type == event_type)
            
            if is_read is not None:
                query = query.where(Notification.is_read == is_read)
            
            if keyword:
                keyword_pattern = f"%{keyword}%"
                query = query.where(
                    Notification.title.like(keyword_pattern) |
                    Notification.content.like(keyword_pattern) |
                    Notification.order_id.like(keyword_pattern)
                )
            
            # 获取总数
            count_query = select(func.count(Notification.id)).where(
                Notification.recipient_username == recipient_username
            )
            if order_id:
                count_query = count_query.where(Notification.order_id == order_id)
            if event_type:
                count_query = count_query.where(Notification.event_type == event_type)
            if is_read is not None:
                count_query = count_query.where(Notification.is_read == is_read)
            if keyword:
                keyword_pattern = f"%{keyword}%"
                count_query = count_query.where(
                    Notification.title.like(keyword_pattern) |
                    Notification.content.like(keyword_pattern) |
                    Notification.order_id.like(keyword_pattern)
                )
            
            count_result = await db.execute(count_query)
            total = count_result.scalar_one()
            
            # 获取列表
            query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
            result = await db.execute(query)
            notifications = result.scalars().all()
            
            return {
                'total': total,
                'items': notifications,
                'skip': skip,
                'limit': limit
            }
            
        except Exception as e:
            logger.error(f"查询站内信失败: {e}")
            return {'total': 0, 'items': [], 'skip': skip, 'limit': limit}

    @staticmethod
    async def get_unread_count(db: AsyncSession, recipient_username: str) -> int:
        """
        获取未读消息数量
        
        Args:
            db: 数据库会话
            recipient_username: 接收者用户名
        
        Returns:
            未读消息数量
        """
        try:
            result = await db.execute(
                select(func.count(Notification.id)).where(
                    and_(
                        Notification.recipient_username == recipient_username,
                        Notification.is_read == False
                    )
                )
            )
            return result.scalar_one()
            
        except Exception as e:
            logger.error(f"获取未读消息数量失败: {e}")
            return 0

    @staticmethod
    async def mark_as_read(db: AsyncSession, notification_id: int, recipient_username: str) -> bool:
        """
        标记单条消息为已读
        
        Args:
            db: 数据库会话
            notification_id: 通知ID
            recipient_username: 接收者用户名
        
        Returns:
            是否标记成功
        """
        try:
            result = await db.execute(
                select(Notification).where(
                    and_(
                        Notification.id == notification_id,
                        Notification.recipient_username == recipient_username
                    )
                )
            )
            notification = result.scalar_one_or_none()
            
            if not notification:
                logger.warning(f"通知 {notification_id} 不存在或不属于用户 {recipient_username}")
                return False
            
            if not notification.is_read:
                notification.is_read = True
                notification.read_at = beijing_now()
                await db.commit()
                logger.info(f"通知 {notification_id} 已标记为已读")
            
            return True
            
        except Exception as e:
            logger.error(f"标记通知为已读失败: {e}")
            await db.rollback()
            return False

    @staticmethod
    async def mark_all_as_read(db: AsyncSession, recipient_username: str) -> int:
        """
        标记所有消息为已读
        
        Args:
            db: 数据库会话
            recipient_username: 接收者用户名
        
        Returns:
            标记的消息数量
        """
        try:
            result = await db.execute(
                select(Notification).where(
                    and_(
                        Notification.recipient_username == recipient_username,
                        Notification.is_read == False
                    )
                )
            )
            notifications = result.scalars().all()
            
            count = 0
            for notification in notifications:
                notification.is_read = True
                notification.read_at = beijing_now()
                count += 1
            
            if count > 0:
                await db.commit()
                logger.info(f"用户 {recipient_username} 的 {count} 条通知已标记为已读")
            
            return count
            
        except Exception as e:
            logger.error(f"标记所有通知为已读失败: {e}")
            await db.rollback()
            return 0

    @staticmethod
    async def delete_notification(db: AsyncSession, notification_id: int, recipient_username: str) -> bool:
        """
        删除单条消息
        
        Args:
            db: 数据库会话
            notification_id: 通知ID
            recipient_username: 接收者用户名
        
        Returns:
            是否删除成功
        """
        try:
            result = await db.execute(
                select(Notification).where(
                    and_(
                        Notification.id == notification_id,
                        Notification.recipient_username == recipient_username
                    )
                )
            )
            notification = result.scalar_one_or_none()
            
            if not notification:
                logger.warning(f"通知 {notification_id} 不存在或不属于用户 {recipient_username}")
                return False
            
            await db.delete(notification)
            await db.commit()
            logger.info(f"通知 {notification_id} 已删除")
            return True
            
        except Exception as e:
            logger.error(f"删除通知失败: {e}")
            await db.rollback()
            return False