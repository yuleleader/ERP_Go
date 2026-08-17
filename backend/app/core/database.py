# -*- coding: utf-8 -*-
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import event
from .config import DATABASE_URL

logger = logging.getLogger(__name__)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    # ── SQLite 单写者，池不宜大 ——
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=300,
    pool_pre_ping=True,
    # 移除 pool_use_lifo —— 避免连接饥饿
    connect_args={
        "check_same_thread": False,
        "timeout": 30  # SQLite 写锁等待上限，超时抛异常而非永久阻塞
    }
)

# ── 关键加固：每个新连接开启 WAL 模式 ──
# 默认 rollback journal 模式下，读与写、进程与进程会互相加锁；
# 开启 WAL 后允许多个读并发 + 单写者并行，彻底消除“刷新时数据库锁竞争/变慢”问题。
@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_wal(dbapi_connection, connection_record):
    try:
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.close()
    except Exception as e:
        logger.warning(f"设置 SQLite WAL PRAGMA 失败（可忽略）: {e}")


AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # SQLite 不会自动 ALTER：为已存在的 orders 表补充列（带存在性判定，可重复执行）
        try:
            from sqlalchemy import text
            cols = [r[1] for r in (await conn.execute(text("PRAGMA table_info(orders)"))).fetchall()]
            if "freight" not in cols:
                await conn.execute(text("ALTER TABLE orders ADD COLUMN freight VARCHAR(20)"))
                logger.info("已为 orders 表新增 freight 列")
            if "logistics_no_2" not in cols:
                await conn.execute(text("ALTER TABLE orders ADD COLUMN logistics_no_2 VARCHAR(100)"))
                logger.info("已为 orders 表新增 logistics_no_2 列（运单号2）")
        except Exception as e:
            logger.warning(f"列迁移检查失败（可忽略，新建库已包含该列）: {e}")
        # 为已存在的 shops 表补充平台/API 相关列（关联 platforms.id；NULL=手工录入网店，API 逻辑不生效）
        try:
            from sqlalchemy import text as _text
            shop_cols = [r[1] for r in (await conn.execute(_text("PRAGMA table_info(shops)"))).fetchall()]
            shop_new_columns = {
                "platform_id": "INTEGER",
                "api_app_key": "VARCHAR(255)",
                "api_app_secret": "TEXT",
                "api_access_token": "TEXT",
                "api_refresh_token": "TEXT",
                "api_token_expire": "DATETIME",
                "api_auth_scope": "TEXT",
                "api_self_qps": "INTEGER",
                "sync_auto_enable": "INTEGER",
                "sync_order_interval": "INTEGER",
                "sync_time_window": "INTEGER",
                "last_sync_success_time": "DATETIME",
                "api_retry_count": "INTEGER",
                "api_retry_base_ms": "INTEGER",
                "webhook_callback": "VARCHAR(500)",
                "webhook_verify_key": "VARCHAR(255)",
                "api_ext_json": "TEXT",
            }
            for col_name, col_type in shop_new_columns.items():
                if col_name not in shop_cols:
                    await conn.execute(_text(f"ALTER TABLE shops ADD COLUMN {col_name} {col_type}"))
                    logger.info(f"已为 shops 表新增 {col_name} 列")
        except Exception as e:
            logger.warning(f"shops 列迁移检查失败（可忽略，新建库已包含该列）: {e}")
        # 一次性迁移：放开网店"名称/账号"的全局唯一约束（业务规则：同邮箱可在不同平台注册，
        # 唯一性=名称+账号组合，组合唯一由接口层校验）。幂等：仅删除现存的两个单列唯一索引。
        try:
            from sqlalchemy import text
            idxs = (await conn.execute(text("PRAGMA index_list('shops')"))).fetchall()
            for idx in idxs:
                if idx[2]:  # unique=1
                    cols = [r[2] for r in (await conn.execute(text(f"PRAGMA index_info('{idx[1]}')"))).fetchall()]
                    if sorted(cols) in (["shop_account"], ["shop_name"]):
                        await conn.execute(text(f'DROP INDEX IF EXISTS "{idx[1]}"'))
                        logger.info(f"已移除 shops 唯一索引 {idx[1]}（改为名称+账号组合唯一）")
        except Exception as e:
            logger.warning(f"shops 唯一约束迁移检查失败（可忽略，新建库已无该约束）: {e}")