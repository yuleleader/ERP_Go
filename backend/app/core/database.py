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
            if "refund_note" not in cols:
                await conn.execute(text("ALTER TABLE orders ADD COLUMN refund_note TEXT"))
                logger.info("已为 orders 表新增 refund_note 列")
            if "detected_country" not in cols:
                await conn.execute(text("ALTER TABLE orders ADD COLUMN detected_country VARCHAR(100)"))
                logger.info("已为 orders 表新增 detected_country 列")
            if "logistics_no_2" not in cols:
                await conn.execute(text("ALTER TABLE orders ADD COLUMN logistics_no_2 VARCHAR(100)"))
                logger.info("已为 orders 表新增 logistics_no_2 列（运单号2）")
        except Exception as e:
            logger.warning(f"列迁移检查失败（可忽略，新建库已包含该列）: {e}")

        # 一次性迁移：将金额字段由 VARCHAR 改为 REAL（数字类型），并转换旧数据。幂等，失败自动回滚。
        try:
            await _migrate_amount_columns(conn)
        except Exception as e:
            logger.warning(
                "⚠️ 金额列迁移失败：数据库金额字段可能仍为文本类型，统计/排序可能出现精度或顺序问题。"
                "本次已自动回滚、未改动数据，系统仍可启动；建议人工检查数据库后再次重启重试。详情: %s", e
            )

        # 一次性迁移：去掉 shops 表 shop_name/shop_account 的全局唯一约束
        # （网店账号一般是邮箱，不同平台可用同一邮箱注册；唯一性改为"名称+账号"组合，由应用层校验）
        try:
            await _rebuild_table_drop_unique(conn, "shops", {"shop_name", "shop_account"})
        except Exception as e:
            logger.warning(
                "⚠️ shops 表唯一约束迁移失败：同名/同邮箱网店仍可能被数据库拦截，系统仍可启动。详情: %s", e
            )


async def _migrate_amount_columns(conn):
    """检查并将金额字段从文本类型改为 REAL 数字类型（一次性、幂等）。"""
    await _rebuild_numeric_table(conn, "orders", ["sales_amount", "commission_amount", "freight"])
    await _rebuild_numeric_table(conn, "shop_withdraw_record", ["withdraw_amount"], not_null_cols={"withdraw_amount"})


async def _rebuild_numeric_table(conn, table, amount_cols, not_null_cols=None):
    """若表内金额列仍是文本类型，则重建该表为数字类型(REAL)并迁移数据；否则跳过。失败自动回滚到原表。

    采用“显式 CREATE TABLE（基于 PRAGMA 生成）+ 数据搬迁 + 重建唯一索引”的方案，
    避免依赖 create_all 在 rename 同事务内的可见性问题。
    """
    from sqlalchemy import text
    not_null_cols = not_null_cols or set()
    info = (await conn.execute(text(f"PRAGMA table_info(\"{table}\")"))).fetchall()
    if not info:
        return
    cols = {r[1]: (r[2] or "") for r in info}
    need = any(
        ("CHAR" in cols[c].upper() or "TEXT" in cols[c].upper() or "CLOB" in cols[c].upper())
        for c in amount_cols if c in cols
    )
    if not need:
        return  # 已是数字类型，无需迁移

    logger.info(f"开始迁移表 {table} 的金额列为数字类型（REAL）...")
    old_cols = [r[1] for r in info]
    # 依据原表结构生成新表建表语句，金额列改为 REAL，保留 PK / NOT NULL / DEFAULT
    col_defs = []
    for r in info:
        cname, ctype, cnotnull, cdflt, cpk = r[1], (r[2] or ""), r[3], r[4], r[5]
        if cname in amount_cols:
            ctype = "REAL"
        ddl = f'"{cname}" {ctype}'
        if cpk:
            ddl += " PRIMARY KEY"
        if cnotnull and not cpk:
            ddl += " NOT NULL"
        if cdflt is not None:
            # 默认值可能为常量或函数表达式（如 datetime('now','localtime')），统一加括号以确保语法正确
            ddl += f" DEFAULT ({cdflt})"
        col_defs.append(ddl)
    create_sql = f'CREATE TABLE "{table}" ({", ".join(col_defs)})'
    try:
        # 1) 重命名旧表
        await conn.execute(text(f'ALTER TABLE "{table}" RENAME TO "{table}_old"'))
        # 2) 用显式语句创建新表（数字类型）
        await conn.execute(text(create_sql))
        # 3) 记录旧表唯一/普通索引信息（用于迁后重建；主键索引跳过，已在列定义中）
        idx_meta = []
        for idx in (await conn.execute(text(f'PRAGMA index_list("{table}_old")'))).fetchall():
            idx_name, idx_unique, idx_origin = idx[1], idx[2], idx[3]
            if idx_origin == "pk":
                continue
            idx_cols = [i[2] for i in (await conn.execute(text(f'PRAGMA index_info("{idx_name}")'))).fetchall()]
            if idx_cols:
                # 使用 mig_ 前缀的安全名称，避免 sqlite_ 保留前缀与旧表索引名冲突
                safe_name = f"mig_{idx_name}"
                idx_meta.append((safe_name, idx_unique, idx_cols))
        # 4) 按列名映射搬迁数据，金额列做 CAST(NULLIF(...)) 空串转 NULL/0
        col_list = ", ".join(f'"{c}"' for c in old_cols)
        select_exprs = []
        for c in old_cols:
            if c in amount_cols:
                expr = f'CAST(NULLIF("{c}", \'\') AS REAL)'
                if c in not_null_cols:
                    expr = f'COALESCE({expr}, 0)'
                select_exprs.append(expr)
            else:
                select_exprs.append(f'"{c}"')
        select_list = ", ".join(select_exprs)
        await conn.execute(text(f'INSERT INTO "{table}" ({col_list}) SELECT {select_list} FROM "{table}_old"'))
        # 5) 修复自增序列，避免后续插入因 id 冲突失败
        max_id = (await conn.execute(text(f'SELECT MAX(id) FROM "{table}"'))).scalar()
        if max_id:
            await conn.execute(text(f"INSERT OR REPLACE INTO sqlite_sequence (name, seq) VALUES ('{table}', {int(max_id)})"))
        # 6) 在新表上重建索引（使用安全名称，此时旧表尚在但名称不冲突）
        for safe_name, idx_unique, idx_cols in idx_meta:
            uniq = "UNIQUE " if idx_unique else ""
            col_csv = ", ".join(f'"{c}"' for c in idx_cols)
            await conn.execute(text(f'CREATE {uniq}INDEX IF NOT EXISTS "{safe_name}" ON "{table}" ({col_csv})'))
        # 7) 删除旧表（同时删除其索引），至此迁移完成
        await conn.execute(text(f'DROP TABLE "{table}_old"'))
        logger.info(f"表 {table} 金额列迁移完成")
    except Exception as e:
        logger.error(f"表 {table} 金额列迁移失败，回滚到原表: {e}")
        try:
            await conn.execute(text(f'DROP TABLE IF EXISTS "{table}"'))
            await conn.execute(text(f'ALTER TABLE "{table}_old" RENAME TO "{table}"'))
        except Exception as e2:
            logger.error(f"表 {table} 回滚也失败（需人工介入）: {e2}")
        # 吞掉异常，保证应用仍可启动（仅金额列仍为文本，功能不受影响）


async def _rebuild_table_drop_unique(conn, table, drop_unique_cols):
    """重建表以去掉指定列上的 UNIQUE 约束（SQLite 不支持 ALTER DROP UNIQUE，须重建表）。

    - 仅当『被放开列的单一唯一索引』仍存在时才执行（幂等，新库直接跳过）；
    - 保留主键 / NOT NULL / DEFAULT 与其它索引（如 shop_id 的唯一索引）；
    - 只跳过『唯一且列集 ⊆ drop_unique_cols』的索引（即 shop_name / shop_account 的全局唯一）；
    - 失败自动回滚到原表，绝不阻塞启动。
    """
    from sqlalchemy import text
    drop_unique_cols = set(drop_unique_cols)
    info = (await conn.execute(text(f'PRAGMA table_info("{table}")'))).fetchall()
    if not info:
        return
    # 幂等判断：被放开列是否仍存在唯一索引
    need = False
    for idx in (await conn.execute(text(f'PRAGMA index_list("{table}")'))).fetchall():
        idx_name, idx_unique, idx_origin = idx[1], idx[2], idx[3]
        if not idx_unique or idx_origin == "pk":
            continue
        idx_cols = [i[2] for i in (await conn.execute(text(f'PRAGMA index_info("{idx_name}")'))).fetchall()]
        if set(idx_cols).issubset(drop_unique_cols):
            need = True
            break
    if not need:
        return

    logger.info(f"开始迁移表 {table}：去掉 {sorted(drop_unique_cols)} 的全局唯一约束 ...")
    old_cols = [r[1] for r in info]
    col_defs = []
    for r in info:
        cname, ctype, cnotnull, cdflt, cpk = r[1], (r[2] or ""), r[3], r[4], r[5]
        ddl = f'"{cname}" {ctype}'
        if cpk:
            ddl += " PRIMARY KEY"
        elif cnotnull:
            ddl += " NOT NULL"
        if cdflt is not None:
            ddl += f" DEFAULT ({cdflt})"
        col_defs.append(ddl)
    create_sql = f'CREATE TABLE "{table}" ({", ".join(col_defs)})'
    try:
        # 1) 重命名旧表
        await conn.execute(text(f'ALTER TABLE "{table}" RENAME TO "{table}_old"'))
        # 2) 创建新表（不含被放开列的唯一约束）
        await conn.execute(text(create_sql))
        # 3) 收集需要重建的索引（跳过"唯一且列集 ⊆ 被放开列"的索引）
        idx_meta = []
        for idx in (await conn.execute(text(f'PRAGMA index_list("{table}_old")'))).fetchall():
            idx_name, idx_unique, idx_origin = idx[1], idx[2], idx[3]
            if idx_origin == "pk":
                continue
            idx_cols = [i[2] for i in (await conn.execute(text(f'PRAGMA index_info("{idx_name}")'))).fetchall()]
            if not idx_cols:
                continue
            if idx_unique and set(idx_cols).issubset(drop_unique_cols):
                continue
            safe_name = f"mig_{idx_name}"
            idx_meta.append((safe_name, idx_unique, idx_cols))
        # 4) 搬迁数据
        col_list = ", ".join(f'"{c}"' for c in old_cols)
        await conn.execute(text(f'INSERT INTO "{table}" ({col_list}) SELECT {col_list} FROM "{table}_old"'))
        # 5) 修复自增序列
        max_id = (await conn.execute(text(f'SELECT MAX(id) FROM "{table}"'))).scalar()
        if max_id:
            await conn.execute(text(f"INSERT OR REPLACE INTO sqlite_sequence (name, seq) VALUES ('{table}', {int(max_id)})"))
        # 6) 重建保留的索引
        for safe_name, idx_unique, idx_cols in idx_meta:
            uniq = "UNIQUE " if idx_unique else ""
            col_csv = ", ".join(f'"{c}"' for c in idx_cols)
            await conn.execute(text(f'CREATE {uniq}INDEX IF NOT EXISTS "{safe_name}" ON "{table}" ({col_csv})'))
        # 7) 删除旧表
        await conn.execute(text(f'DROP TABLE "{table}_old"'))
        logger.info(f"表 {table} 已去掉 {sorted(drop_unique_cols)} 的全局唯一约束")
    except Exception as e:
        logger.error(f"表 {table} 去唯一约束失败，回滚到原表: {e}")
        try:
            await conn.execute(text(f'DROP TABLE IF EXISTS "{table}"'))
            await conn.execute(text(f'ALTER TABLE "{table}_old" RENAME TO "{table}"'))
        except Exception as e2:
            logger.error(f"表 {table} 回滚也失败（需人工介入）: {e2}")