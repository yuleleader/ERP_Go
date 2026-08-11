# -*- coding: utf-8 -*-
"""
日志清理服务模块
提供日志自动清理功能，支持手动触发和定时任务
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, and_
from sqlalchemy.exc import SQLAlchemyError
from ..models.models import (
    OperationLog,
    LoginLog,
    LogCleanupRecord,
    SystemSetting,
    Notification
)

logger = logging.getLogger(__name__)

# 默认保留天数：2年
DEFAULT_RETENTION_DAYS = 730
# 站内信默认保留天数：360天（最少存储360天）
NOTIFICATION_DEFAULT_RETENTION_DAYS = 360
# 最大重试次数
MAX_RETRY_ATTEMPTS = 3
# 每次删除的批量大小
BATCH_DELETE_SIZE = 1000


class LogCleanupService:
    """日志清理服务"""

    @staticmethod
    async def get_retention_days(db: AsyncSession) -> int:
        """
        获取日志保留天数配置
        优先读 log_retention_days（标准键）；兼容历史键 log_cleanup_retention_days；
        均未配置则返回默认值。
        """
        for key in ("log_retention_days", "log_cleanup_retention_days"):
            try:
                result = await db.execute(
                    select(SystemSetting.value).where(
                        SystemSetting.key == key
                    )
                )
                value = result.scalar_one_or_none()
                if value:
                    days = int(value)
                    if days < 30:  # 最小保留30天
                        logger.warning(f"保留天数配置 {days} 小于30天，使用默认值")
                        return DEFAULT_RETENTION_DAYS
                    return days
            except (ValueError, SQLAlchemyError) as e:
                logger.warning(f"读取保留天数配置({key})失败: {e}")

        return DEFAULT_RETENTION_DAYS

    @staticmethod
    async def set_retention_days(db: AsyncSession, days: int, operator: Optional[str] = None) -> bool:
        """
        设置日志保留天数配置
        """
        if days < 30:
            raise ValueError("保留天数不能小于30天")

        try:
            result = await db.execute(
                select(SystemSetting).where(
                    SystemSetting.key == "log_retention_days"
                )
            )
            setting = result.scalar_one_or_none()

            if setting:
                setting.value = str(days)
                setting.updated_at = func.now()
            else:
                setting = SystemSetting(
                    key="log_retention_days",
                    value=str(days),
                    description="日志保留天数（天）"
                )
                db.add(setting)

            await db.commit()
            logger.info(f"日志保留天数已更新为 {days} 天，操作者: {operator}")
            return True
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"更新保留天数配置失败: {e}")
            raise

    @staticmethod
    def calculate_cutoff_date(retention_days: int) -> datetime:
        """
        计算日志删除的截止日期
        """
        return datetime.now() - timedelta(days=retention_days)

    @staticmethod
    async def count_old_logs(db: AsyncSession, cutoff_date: datetime) -> Dict[str, int]:
        """
        统计将被删除的旧日志数量
        """
        counts = {}

        # 统计操作日志
        op_result = await db.execute(
            select(func.count(OperationLog.id)).where(
                OperationLog.created_at < cutoff_date
            )
        )
        counts["operation"] = op_result.scalar_one_or_none() or 0

        # 统计登录日志
        login_result = await db.execute(
            select(func.count(LoginLog.id)).where(
                LoginLog.login_time < cutoff_date
            )
        )
        counts["login"] = login_result.scalar_one_or_none() or 0

        counts["total"] = counts["operation"] + counts["login"]
        return counts

    @staticmethod
    async def delete_old_operation_logs(db: AsyncSession, cutoff_date: datetime) -> int:
        """
        批量删除旧的操作日志
        """
        total_deleted = 0

        while True:
            # SQLite 不支持 DELETE ... LIMIT，使用子查询方式
            subquery = select(OperationLog.id).where(
                OperationLog.created_at < cutoff_date
            ).limit(BATCH_DELETE_SIZE)
            result = await db.execute(
                delete(OperationLog).where(
                    OperationLog.id.in_(subquery)
                )
            )
            await db.commit()
            deleted = result.rowcount
            total_deleted += deleted

            if deleted < BATCH_DELETE_SIZE:
                break

            logger.info(f"已删除 {deleted} 条操作日志，累计 {total_deleted} 条")

        return total_deleted

    @staticmethod
    async def delete_old_login_logs(db: AsyncSession, cutoff_date: datetime) -> int:
        """
        批量删除旧的登录日志
        """
        total_deleted = 0

        while True:
            subquery = select(LoginLog.id).where(
                LoginLog.login_time < cutoff_date
            ).limit(BATCH_DELETE_SIZE)
            result = await db.execute(
                delete(LoginLog).where(
                    LoginLog.id.in_(subquery)
                )
            )
            await db.commit()
            deleted = result.rowcount
            total_deleted += deleted

            if deleted < BATCH_DELETE_SIZE:
                break

            logger.info(f"已删除 {deleted} 条登录日志，累计 {total_deleted} 条")

        return total_deleted

    @staticmethod
    async def create_cleanup_record(db: AsyncSession, cleanup_type: str, triggered_by: str, operator_username: Optional[str] = None, retention_days: Optional[int] = None) -> LogCleanupRecord:
        """
        创建清理记录
        """
        if retention_days is None:
            retention_days = await LogCleanupService.get_retention_days(db)
        record = LogCleanupRecord(
            cleanup_type=cleanup_type,
            retention_days=retention_days,
            status="pending",
            triggered_by=triggered_by,
            operator_username=operator_username
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def update_cleanup_record(db: AsyncSession, record_id: int, status: str, deleted_count: int = 0, error_message: Optional[str] = None) -> None:
        """
        更新清理记录状态
        """
        result = await db.execute(
            select(LogCleanupRecord).where(LogCleanupRecord.id == record_id)
        )
        record = result.scalar_one_or_none()
        if record:
            record.status = status
            record.deleted_count = deleted_count
            if error_message:
                record.error_message = error_message
            record.end_time = func.now()
            await db.commit()

    @staticmethod
    async def cleanup_logs(
        db: AsyncSession,
        cleanup_type: str = "all",
        triggered_by: str = "manual",
        operator_username: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行日志清理
        :param cleanup_type: 'operation' | 'login' | 'all'
        :param triggered_by: 'manual' | 'scheduled'
        :param operator_username: 操作者用户名
        :return: 清理结果
        """
        record = await LogCleanupService.create_cleanup_record(
            db, cleanup_type, triggered_by, operator_username
        )

        try:
            retention_days = await LogCleanupService.get_retention_days(db)
            cutoff_date = LogCleanupService.calculate_cutoff_date(retention_days)

            # 先统计
            counts = await LogCleanupService.count_old_logs(db, cutoff_date)
            logger.info(f"开始清理日志，截止日期: {cutoff_date}")
            logger.info(f"预计删除 - 操作日志: {counts['operation']}, 登录日志: {counts['login']}")

            total_deleted = 0

            # 重试机制
            for attempt in range(MAX_RETRY_ATTEMPTS):
                try:
                    if cleanup_type in ["operation", "all"]:
                        total_deleted += await LogCleanupService.delete_old_operation_logs(db, cutoff_date)

                    if cleanup_type in ["login", "all"]:
                        total_deleted += await LogCleanupService.delete_old_login_logs(db, cutoff_date)

                    break  # 成功则退出重试

                except SQLAlchemyError as e:
                    logger.warning(f"清理尝试 {attempt + 1} 失败: {e}")
                    if attempt == MAX_RETRY_ATTEMPTS - 1:
                        raise
                    await db.rollback()
                    continue

            await LogCleanupService.update_cleanup_record(
                db, record.id, "success", total_deleted
            )

            logger.info(f"日志清理完成，共删除 {total_deleted} 条记录")

            return {
                "success": True,
                "retention_days": retention_days,
                "cutoff_date": cutoff_date,
                "deleted_count": total_deleted,
                "operation_deleted": counts["operation"],
                "login_deleted": counts["login"],
                "record_id": record.id
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"日志清理失败: {error_msg}", exc_info=True)
            await LogCleanupService.update_cleanup_record(
                db, record.id, "failed", 0, error_msg
            )
            raise

    # ==================== 站内信清理 ====================

    @staticmethod
    async def get_notification_retention_days(db: AsyncSession) -> int:
        """
        获取站内信保留天数配置（最少存储360天）
        """
        try:
            result = await db.execute(
                select(SystemSetting.value).where(
                    SystemSetting.key == "notification_retention_days"
                )
            )
            value = result.scalar_one_or_none()
            if value:
                days = int(value)
                if days < NOTIFICATION_DEFAULT_RETENTION_DAYS:
                    logger.warning(f"站内信保留天数配置 {days} 小于{NOTIFICATION_DEFAULT_RETENTION_DAYS}天，使用默认值")
                    return NOTIFICATION_DEFAULT_RETENTION_DAYS
                return days
        except (ValueError, SQLAlchemyError) as e:
            logger.warning(f"读取站内信保留天数配置失败: {e}")
        return NOTIFICATION_DEFAULT_RETENTION_DAYS

    @staticmethod
    async def set_notification_retention_days(db: AsyncSession, days: int, operator: Optional[str] = None) -> bool:
        """
        设置站内信保留天数配置（最少360天）
        """
        if days < NOTIFICATION_DEFAULT_RETENTION_DAYS:
            raise ValueError(f"站内信保留天数不能小于{NOTIFICATION_DEFAULT_RETENTION_DAYS}天")

        try:
            result = await db.execute(
                select(SystemSetting).where(
                    SystemSetting.key == "notification_retention_days"
                )
            )
            setting = result.scalar_one_or_none()

            if setting:
                setting.value = str(days)
                setting.updated_at = func.now()
            else:
                setting = SystemSetting(
                    key="notification_retention_days",
                    value=str(days),
                    description="站内信保留天数（天）"
                )
                db.add(setting)

            await db.commit()
            logger.info(f"站内信保留天数已更新为 {days} 天，操作者: {operator}")
            return True
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"更新站内信保留天数配置失败: {e}")
            raise

    @staticmethod
    async def count_old_notifications(db: AsyncSession, cutoff_date: datetime) -> int:
        """
        统计将被删除的旧站内信数量
        """
        result = await db.execute(
            select(func.count(Notification.id)).where(
                Notification.created_at < cutoff_date
            )
        )
        return result.scalar_one_or_none() or 0

    @staticmethod
    async def delete_old_notifications(db: AsyncSession, cutoff_date: datetime) -> int:
        """
        批量删除旧的站内信
        """
        total_deleted = 0

        while True:
            subquery = select(Notification.id).where(
                Notification.created_at < cutoff_date
            ).limit(BATCH_DELETE_SIZE)
            result = await db.execute(
                delete(Notification).where(
                    Notification.id.in_(subquery)
                )
            )
            await db.commit()
            deleted = result.rowcount
            total_deleted += deleted

            if deleted < BATCH_DELETE_SIZE:
                break

            logger.info(f"已删除 {deleted} 条站内信，累计 {total_deleted} 条")

        return total_deleted

    @staticmethod
    async def cleanup_notifications(
        db: AsyncSession,
        triggered_by: str = "manual",
        operator_username: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行站内信清理
        :param triggered_by: 'manual' | 'scheduled'
        :param operator_username: 操作者用户名
        :return: 清理结果
        """
        retention_days = await LogCleanupService.get_notification_retention_days(db)
        record = await LogCleanupService.create_cleanup_record(
            db, "notification", triggered_by, operator_username, retention_days
        )

        try:
            cutoff_date = LogCleanupService.calculate_cutoff_date(retention_days)

            count = await LogCleanupService.count_old_notifications(db, cutoff_date)
            logger.info(f"开始清理站内信，截止日期: {cutoff_date}")
            logger.info(f"预计删除站内信: {count}")

            total_deleted = 0

            for attempt in range(MAX_RETRY_ATTEMPTS):
                try:
                    total_deleted = await LogCleanupService.delete_old_notifications(db, cutoff_date)
                    break
                except SQLAlchemyError as e:
                    logger.warning(f"站内信清理尝试 {attempt + 1} 失败: {e}")
                    if attempt == MAX_RETRY_ATTEMPTS - 1:
                        raise
                    await db.rollback()
                    continue

            await LogCleanupService.update_cleanup_record(
                db, record.id, "success", total_deleted
            )

            logger.info(f"站内信清理完成，共删除 {total_deleted} 条")

            return {
                "success": True,
                "retention_days": retention_days,
                "cutoff_date": cutoff_date,
                "deleted_count": total_deleted,
                "record_id": record.id
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"站内信清理失败: {error_msg}", exc_info=True)
            await LogCleanupService.update_cleanup_record(
                db, record.id, "failed", 0, error_msg
            )
            raise
