# -*- coding: utf-8 -*-
"""
定时任务调度模块
使用APScheduler实现日志自动清理
"""
import logging
from typing import Optional
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from .log_cleanup import LogCleanupService

logger = logging.getLogger(__name__)

# 全局调度器实例
_scheduler: Optional[AsyncIOScheduler] = None


async def scheduled_log_cleanup():
    """
    定时执行的日志清理任务
    每日凌晨2点执行
    """
    logger.info("开始执行定时日志清理任务")

    # 使用项目统一的 AsyncSessionLocal，避免碎片化连接池
    from ..core.database import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as db:
            result = await LogCleanupService.cleanup_logs(
                db,
                cleanup_type="all",
                triggered_by="scheduled"
            )
            logger.info(f"定时日志清理完成: {result}")

    except Exception as e:
        logger.error(f"定时日志清理任务执行失败: {e}", exc_info=True)


async def scheduled_notification_cleanup():
    """
    定时执行的站内信清理任务
    每日凌晨2:10执行（在日志清理之后）
    """
    logger.info("开始执行定时站内信清理任务")

    from ..core.database import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as db:
            result = await LogCleanupService.cleanup_notifications(
                db,
                triggered_by="scheduled"
            )
            logger.info(f"定时站内信清理完成: {result}")

    except Exception as e:
        logger.error(f"定时站内信清理任务执行失败: {e}", exc_info=True)


def setup_scheduler(app: FastAPI):
    """
    初始化并启动调度器
    """
    global _scheduler

    if _scheduler and _scheduler.running:
        logger.warning("调度器已在运行")
        return

    _scheduler = AsyncIOScheduler()

    # 添加日志清理任务：每天凌晨2点执行
    _scheduler.add_job(
        scheduled_log_cleanup,
        trigger=CronTrigger(hour=2, minute=0),
        id="daily_log_cleanup",
        name="每日日志清理",
        misfire_grace_time=3600,  # 1小时宽限期
        max_instances=1,
        replace_existing=True
    )

    # 添加站内信清理任务：每天凌晨2:10执行（日志清理之后）
    _scheduler.add_job(
        scheduled_notification_cleanup,
        trigger=CronTrigger(hour=2, minute=10),
        id="daily_notification_cleanup",
        name="每日站内信清理",
        misfire_grace_time=3600,
        max_instances=1,
        replace_existing=True
    )

    _scheduler.start()
    logger.info("定时任务调度器已启动")


def shutdown_scheduler():
    """
    关闭调度器
    """
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        _scheduler = None
        logger.info("定时任务调度器已关闭")


def get_scheduler() -> Optional[AsyncIOScheduler]:
    """
    获取调度器实例
    """
    return _scheduler
