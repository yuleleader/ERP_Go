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
        # SQLite 不会自动 ALTER：为已存在的 orders 表补充 freight 列（带存在性判定，可重复执行）
        try:
            from sqlalchemy import text
            cols = [r[1] for r in (await conn.execute(text("PRAGMA table_info(orders)"))).fetchall()]
            if "freight" not in cols:
                await conn.execute(text("ALTER TABLE orders ADD COLUMN freight VARCHAR(20)"))
                logger.info("已为 orders 表新增 freight 列")
        except Exception as e:
            logger.warning(f"freight 列迁移检查失败（可忽略，新建库已包含该列）: {e}")