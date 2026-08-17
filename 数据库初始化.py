# -*- coding: utf-8 -*-
"""
数据库初始化脚本
================
用途：在项目部署时自动创建数据库、数据表、初始配置数据及默认账号。
特性：幂等（可重复执行）、跨平台兼容、无需依赖 FastAPI 运行环境。

使用方法：
    python 数据库初始化.py              # 交互确认模式
    python 数据库初始化.py --force      # 跳过确认，强制初始化
    python 数据库初始化.py --reset      # 删除旧库，完全重建（危险！）
"""

import os
import sys
import sqlite3
import shutil
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 强制 UTF-8 输出：脚本内含 ✓/✗ 等符号，在 Windows 管道(GBK)下 print 会 UnicodeEncodeError 崩溃
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ==================== 路径配置 ====================
BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / "backend"
DATA_DIR = BACKEND_DIR / "data"
DB_DIR = DATA_DIR / "db"
IMAGES_DIR = DATA_DIR / "images"
TEMP_DIR = IMAGES_DIR / "temp"
OFFICIAL_DIR = IMAGES_DIR / "official"
PRODUCT_DIR = IMAGES_DIR / "product"   # 商品图片目录（商品档案上传的图片）
BACKUP_DIR = DATA_DIR / "backup"
LOGS_DIR = DATA_DIR / "logs"
QR_CACHE_DIR = DATA_DIR / "qr_codes"
DB_PATH = DB_DIR / "order_system.db"


# ==================== 哈希工具 ====================
def get_password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
    ).hex()
    return f"{salt}${pwd_hash}"


# ==================== 目录初始化 ====================
def create_directories():
    dirs = [DATA_DIR, DB_DIR, IMAGES_DIR, TEMP_DIR, OFFICIAL_DIR, PRODUCT_DIR, BACKUP_DIR, LOGS_DIR, QR_CACHE_DIR]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    print("✓ 目录结构初始化完成")


# ==================== 建表 ====================
def create_tables(conn: sqlite3.Connection):
    """创建/确认全部数据表结构。

    方案A：直接委托后端 SQLAlchemy ORM（backend/app/models/models.py）建表，
    与运行时模型永远同步（18 张表 + 全部新列），避免手写 SQL 滞后。
    """
    cursor = conn.cursor()

    # 让后端模型可导入：把 backend 目录加入 sys.path
    backend_dir = str(BACKEND_DIR)
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    # 导入 Base 与全部模型（import 模型类即注册到 Base.metadata）
    from app.core.database import Base
    import app.models.models  # noqa: F401  触发全部 __tablename__ 注册
    from sqlalchemy import create_engine

    # 用独立的同步 engine 指向同一 SQLite 文件执行 create_all
    # （不能用后端 AsyncEngine.sync_engine：它是异步驱动包装，脱离 greenlet 上下文会报错）
    sync_engine = create_engine(f"sqlite:///{DB_PATH}")
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    # 打印已存在的表清单（供界面/日志反馈）
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    for i, t in enumerate(tables, 1):
        print(f"  [{i:02d}] {t}")
    conn.commit()
    print(f"✓ 共 {len(tables)} 张数据表创建/确认完成（由 SQLAlchemy ORM 生成）")


# ==================== 初始数据 ====================
def seed_default_admin(conn: sqlite3.Connection):
    """插入默认管理员账号"""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = '1001'")
    if cursor.fetchone():
        print("  - 默认管理员账号已存在，跳过")
        return

    password_hash = get_password_hash("1001")
    cursor.execute(
        """INSERT INTO users (username, password_hash, real_name, role, is_active)
           VALUES ('1001', ?, '系统管理员', 'boss', 1)""",
        (password_hash,)
    )
    conn.commit()
    print("  + 已创建默认管理员账号 (1001/1001)")


def seed_system_settings(conn: sqlite3.Connection):
    """插入系统默认配置"""
    defaults = [
        ("token_expire_minutes", "1440", "Token有效期（分钟），默认24小时"),
        ("temp_image_retention_hours", "24", "临时图片保留时间（小时）"),
        ("qr_code_access_expire_minutes", "60", "二维码临时访问链接有效期（分钟）"),
        ("backup_retention_days", "30", "备份文件保留天数"),
        ("auto_backup_enabled", "true", "是否启用每日自动备份"),
        ("log_retention_days", "90", "操作日志保留天数"),
        ("system_version", "1.0.0", "当前系统版本号"),
        ("default_commission_rate", "10", "默认销售提成率（%）"),
        ("overdue_order_days", "7", "超期订单预警天数（预警中心用）"),
    ]

    cursor = conn.cursor()
    inserted = 0
    for key, value, desc in defaults:
        cursor.execute("SELECT id FROM system_settings WHERE key = ?", (key,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO system_settings (key, value, description) VALUES (?, ?, ?)",
                (key, value, desc)
            )
            inserted += 1

    conn.commit()
    print(f"  + 已写入 {inserted} 条系统默认配置（共 {len(defaults)} 条）")



def seed_all(conn: sqlite3.Connection):
    print("\n>>> 写入初始数据")
    seed_default_admin(conn)
    seed_system_settings(conn)
    seed_default_category_brand(conn)
    seed_default_platforms(conn)
    clean_non_default_platforms(conn)


def seed_default_category_brand(conn: sqlite3.Connection):
    """重建默认兜底类别与品牌：
    - 类别：编码 999、名称「其他类别」（一级）；页面左侧最上方的「全部」为固定选项，无需入库。
    - 品牌：编码 999、名称「默认品牌」。
    幂等：已存在则跳过。
    """
    cursor = conn.cursor()
    if not cursor.execute("SELECT 1 FROM categories WHERE category_code='999'").fetchone():
        cursor.execute(
            "INSERT INTO categories (category_code, category_name, parent_id, level) VALUES ('999','其他类别',NULL,1)"
        )
        print("  ✓ 默认类别: 999-其他类别")
    else:
        print("  - 默认类别 999 已存在，跳过")
    if not cursor.execute("SELECT 1 FROM brands WHERE brand_code=999").fetchone():
        cursor.execute(
            "INSERT INTO brands (brand_code, brand_name) VALUES (999,'默认品牌')"
        )
        print("  ✓ 默认品牌: 999-默认品牌")
    else:
        print("  - 默认品牌 999 已存在，跳过")
    conn.commit()


def seed_default_platforms(conn: sqlite3.Connection):
    """幂等预置 5 个默认电商平台（code 01-05）并补全真实开放平台 API 配置字段。

    与后端 app/main.py 的 create_default_platforms 保持一致：
    - 新库写入完整记录（含真实网关/版本/限流/TOP·REST/Webhook 字段）；
    - 已存在仅补 API 配置字段（不动用户改过的名称/状态/备注）；
    - 用户主动删除某平台后不会自动恢复。
    限流数值为查证到的参考值，实际随账号等级与应用审核变化，接入时按官方文档微调。
    """
    cursor = conn.cursor()
    defaults = [
        {
            "platform_code": "alibaba_icbu", "platform_name": "阿里巴巴国际站",
            "api_gateway": "https://gw.api.alibaba.com/openapi/",
            "api_version": "2.0",
            "api_global_max_qps": 4,
            "top_sign_type": "hmac-sha1",
            "top_default_fields": "product_id,title,price,sku,moq,logistics",
            "rest_auth_header": "",
            "rest_token_prefix": "",
            "webhook_encrypt_type": "sha256",
            "remark": "阿里系 TOP 开放平台(ICBU)，HMAC-SHA1 签名；仅企业开发者可申请；网关路径含 param2/2.0/<method>",
        },
        {
            "platform_code": "made_in_china", "platform_name": "中国制造网",
            "api_gateway": "https://api.made-in-china.com/",
            "api_version": "2.0",
            "api_global_max_qps": 10,
            "top_sign_type": "",
            "top_default_fields": "",
            "rest_auth_header": "Authorization",
            "rest_token_prefix": "Bearer",
            "webhook_encrypt_type": "sha256",
            "remark": "MIC 开放平台，RESTful + OAuth2.0 + MD5 签名(APIKey+SecretKey+时间戳+随机数)；商品详情 /v2/product/detail",
        },
        {
            "platform_code": "globalsources", "platform_name": "环球资源",
            "api_gateway": "",
            "api_version": "",
            "api_global_max_qps": 10,
            "top_sign_type": "",
            "top_default_fields": "",
            "rest_auth_header": "",
            "rest_token_prefix": "",
            "webhook_encrypt_type": "",
            "remark": "暂无公开标准开放平台API，接入需线下向环球资源申请开发者权限",
        },
        {
            "platform_code": "dhgate", "platform_name": "敦煌网",
            "api_gateway": "http://api.dhgate.com/dop/router",
            "api_version": "1.0",
            "api_global_max_qps": 10,
            "top_sign_type": "",
            "top_default_fields": "",
            "rest_auth_header": "Authorization",
            "rest_token_prefix": "Bearer",
            "webhook_encrypt_type": "sha256",
            "remark": "DOP REST 风格，OAuth2.0 系统参数(method/v/access_token/timestamp)；每分钟≤600次；沙箱 sandbox.api.dhgate.com",
        },
        {
            "platform_code": "aliexpress", "platform_name": "速卖通",
            "api_gateway": "https://openapi.aliexpress.com/router/rest",
            "api_version": "2.0",
            "api_global_max_qps": 5,
            "top_sign_type": "hmac-sha1",
            "top_default_fields": "product_id,title,price,sku,logistics,currency",
            "rest_auth_header": "",
            "rest_token_prefix": "",
            "webhook_encrypt_type": "sha256",
            "remark": "AliExpress Open Platform(阿里系 TOP)，HMAC-SHA1 签名；分区域网关(sg/cn/us)；QPS≤5",
        },
    ]
    # 已存在分支仅补的 API 配置字段（不动名称/状态/备注，尊重用户自定义）
    api_fields = [
        "api_gateway", "api_version", "api_global_max_qps",
        "top_sign_type", "top_default_fields", "rest_auth_header", "rest_token_prefix",
        "webhook_encrypt_type",
    ]
    for d in defaults:
        name = d["platform_name"]
        # 按 platform_name 判重（名称唯一约束）：已存在则仅补 API 配置字段，
        # 不改动用户改过的 platform_name / remark / status；避免与历史数字编码(01-05)撞名崩溃
        row = cursor.execute("SELECT id FROM platforms WHERE platform_name=?", (name,)).fetchone()
        if row is None:
            cols = ["platform_code", "platform_name", "remark", "status"] + api_fields
            vals = [d["platform_code"], d["platform_name"], d["remark"], 1] + [d[k] for k in api_fields]
            placeholders = ",".join(["?"] * len(cols))
            cursor.execute(
                f"INSERT INTO platforms ({','.join(cols)}) VALUES ({placeholders})", vals
            )
            print(f"  + 已预置平台: {d['platform_code']}-{name}")
        else:
            sets = ", ".join(f"{k}=?" for k in api_fields)
            cursor.execute(
                f"UPDATE platforms SET {sets} WHERE platform_name=?",
                [d[k] for k in api_fields] + [name],
            )
    conn.commit()
    print("  ✓ 默认平台预置/补全完成（共 5 个，含真实开放平台 API 字段）")


# 系统默认平台标识（语义编码 + 中文名，两种编码方案都保护）：
# 真实库历史为数字编码 01-05，新库/设计文档为语义编码；两者均视为系统默认项
SYSTEM_DEFAULT_PLATFORM_CODES = {
    "alibaba_icbu", "made_in_china", "globalsources", "dhgate", "aliexpress",
}
SYSTEM_DEFAULT_PLATFORM_NAMES = {
    "阿里巴巴国际站", "中国制造网", "环球资源", "敦煌网", "速卖通",
}


def clean_non_default_platforms(conn: sqlite3.Connection):
    """清理非系统默认平台：仅保留 5 个系统默认项，删除其余平台。

    - 被网店引用的平台不会被删除（避免破坏业务数据），仅打印警告；
    - 系统默认项由 SYSTEM_DEFAULT_PLATFORM_CODES / _NAMES 定义（按编码或名称任一命中即保留）。
    配合 init_database 使用时，clean_user_data 已先清空 shops，故可安全删除全部非默认项。
    """
    cursor = conn.cursor()
    rows = cursor.execute("SELECT id, platform_code, platform_name FROM platforms").fetchall()
    deleted = 0
    skipped = 0
    for pid, code, name in rows:
        is_default = (code in SYSTEM_DEFAULT_PLATFORM_CODES) or (name in SYSTEM_DEFAULT_PLATFORM_NAMES)
        if is_default:
            continue
        ref = cursor.execute("SELECT COUNT(*) FROM shops WHERE platform_id=?", (pid,)).fetchone()[0]
        if ref > 0:
            print(f"  ! 跳过平台(被 {ref} 个网店引用，不删除): {code}-{name}")
            skipped += 1
            continue
        cursor.execute("DELETE FROM platforms WHERE id=?", (pid,))
        print(f"  - 已清理非默认平台: {code}-{name}")
        deleted += 1
    conn.commit()
    if deleted == 0 and skipped == 0:
        print("  无需清理：当前平台均为系统默认项")
    else:
        print(f"✓ 共清理 {deleted} 个非默认平台（保留 {len(rows) - deleted - skipped} 个系统默认项"
              + (f"，跳过 {skipped} 个被引用平台" if skipped else "") + "）")


# ==================== 兼容性检查 ====================
def ensure_columns(conn: sqlite3.Connection):
    """
    向后兼容：为旧数据库补充缺失字段（仅当数据库已存在且缺列时执行）。
    新库由 ORM create_all 直接建全，无需迁移。
    """
    cursor = conn.cursor()

    migrations = {
        "users": [
            ("commission_rate", "INTEGER"),
            ("price_permissions", "VARCHAR(100)"),
            ("data_permissions", "TEXT"),
        ],
        "orders": [
            ("order_days", "INTEGER DEFAULT 0"),
            ("commission_paid", "BOOLEAN DEFAULT 0"),
            ("commission_rate", "INTEGER"),
            ("commission_amount", "VARCHAR(20)"),
            ("produce_status", "VARCHAR(20) DEFAULT 'unproduce'"),
            ("produce_status_update_at", "TIMESTAMP"),
            ("produce_status_update_user", "VARCHAR(50)"),
            ("logistics_no_2", "VARCHAR(100)"),
            ("freight", "VARCHAR(20)"),
            ("detected_country", "VARCHAR(100)"),
            ("refund_note", "TEXT"),
            ("last_print_at", "TIMESTAMP"),
            ("gross_profit", "FLOAT"),
        ],
        "products": [
            ("category_id", "INTEGER"),
            ("brand_id", "INTEGER"),
            ("cost_price", "FLOAT"),
            ("retail_price", "FLOAT"),
            ("min_price", "FLOAT"),
            ("remark1", "VARCHAR(500)"),
            ("remark2", "VARCHAR(500)"),
            ("remark3", "VARCHAR(500)"),
        ],
        "shops": [
            ("platform_code", "VARCHAR(20)"),
            ("platform_id", "INTEGER"),
            ("api_app_key", "VARCHAR(255)"),
            ("api_app_secret", "TEXT"),
            ("api_access_token", "TEXT"),
            ("api_refresh_token", "TEXT"),
            ("api_token_expire", "DATETIME"),
            ("api_auth_scope", "TEXT"),
            ("api_self_qps", "INTEGER"),
            ("sync_auto_enable", "INTEGER"),
            ("sync_order_interval", "INTEGER"),
            ("sync_time_window", "INTEGER"),
            ("last_sync_success_time", "DATETIME"),
            ("api_retry_count", "INTEGER"),
            ("api_retry_base_ms", "INTEGER"),
            ("webhook_callback", "VARCHAR(500)"),
            ("webhook_verify_key", "VARCHAR(255)"),
            ("api_ext_json", "TEXT"),
        ],
    }

    print("\n>>> 字段兼容性检查")
    migrated = 0
    for table, columns in migrations.items():
        cursor.execute(f"PRAGMA table_info({table})")
        existing = {col[1] for col in cursor.fetchall()}
        for col_name, col_def in columns:
            if col_name not in existing:
                try:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")
                    print(f"  + 补全字段: {table}.{col_name}")
                    migrated += 1
                except sqlite3.OperationalError as e:
                    print(f"  ! 字段添加失败 {table}.{col_name}: {e}")

    conn.commit()
    if migrated == 0:
        print("  所有字段已是最新，无需迁移")
    else:
        print(f"✓ 共补全 {migrated} 个字段")


# ==================== 清理业务数据 ====================
def clean_user_data(conn: sqlite3.Connection):
    """删除所有用户产生的业务数据，保留管理员账号和系统配置"""
    cursor = conn.cursor()

    # 获取管理员ID
    cursor.execute("SELECT id, username FROM users WHERE username = '1001'")
    admin = cursor.fetchone()

    tables_to_clean = [
        ("shop_withdraw_record", "提现记录"),
        ("notifications", "站内信"),
        ("log_cleanup_records", "清理记录"),
        ("login_logs", "登录日志"),
        ("operation_logs", "操作日志"),
        ("images", "图片记录"),
        ("product_images", "商品图片记录"),
        ("order_imports", "订单导入临时表"),
        ("non_trade_transactions", "非交易收支流水"),
        ("accounting_codes", "账务代码"),
        ("orders", "订单"),
        ("shops", "网店"),
        ("products", "商品"),
        ("categories", "类别"),
        ("brands", "品牌"),
        ("logistics_companies", "物流公司"),
    ]

    print("\n>>> 清理业务数据（保留管理员和系统配置）")
    total = 0
    for table, label in tables_to_clean:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        if count > 0:
            cursor.execute(f"DELETE FROM {table}")
            print(f"  - {label}: {count} 条")
            total += count
        else:
            print(f"  - {label}: 0 条（无需清理）")

    # 删除除 admin 外的所有用户
    cursor.execute("SELECT COUNT(*) FROM users WHERE username != '1001'")
    other_users = cursor.fetchone()[0]
    if other_users > 0:
        # 先查出名称用于打印
        cursor.execute("SELECT username, real_name FROM users WHERE username != '1001'")
        user_list = cursor.fetchall()
        cursor.execute("DELETE FROM users WHERE username != '1001'")
        for u in user_list:
            print(f"  - 用户: {u[0]} ({u[1]})")
        total += other_users

    conn.commit()
    if total > 0:
        print(f"✓ 共清理 {total} 条数据")
    else:
        print("  数据库已是最干净状态，无需清理")


# ==================== 清理磁盘图片 ====================
def clean_disk_images():
    """删除所有业务上传的图片文件及其目录（临时图 / 订单正式图 / 商品图）。

    无论 --reset 还是 --force 都会执行；删除后由 create_directories 重建空目录。
    """
    print("\n>>> 清理磁盘图片（临时图 / 订单正式图 / 商品图）")
    total = 0
    for d, label in [
        (TEMP_DIR, "临时图片"),
        (OFFICIAL_DIR, "订单正式图片"),
        (PRODUCT_DIR, "商品图片"),
    ]:
        if d.exists():
            files = [f for f in d.rglob("*") if f.is_file()]
            shutil.rmtree(d, ignore_errors=True)
            total += len(files)
            print(f"  - {label}: 删除 {len(files)} 个文件，目录 {d.name}/ 已清除")
        else:
            print(f"  - {label}: 无（目录不存在）")
    if total == 0:
        print("  ✓ 磁盘上未发现已上传图片")
    else:
        print(f"  ✓ 共删除 {total} 个图片文件")
    return total


# ==================== 验证 ====================
def verify(conn: sqlite3.Connection):
    print("\n>>> 初始化验证")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]

    cursor.execute("SELECT username, role FROM users WHERE username = '1001'")
    admin = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) FROM system_settings")
    setting_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM logistics_companies")
    company_count = cursor.fetchone()[0]

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    print(f"  数据表总数: {len(tables)}")
    print(f"  用户数:     {user_count}")
    print(f"  管理员账号: {admin[0] if admin else '未创建'} (角色: {admin[1] if admin else 'N/A'})")
    print(f"  系统配置项: {setting_count}")
    print(f"  物流公司数: {company_count}")
    print(f"  数据库路径: {DB_PATH.absolute()}")
    print(f"  数据库大小: {DB_PATH.stat().st_size / 1024:.1f} KB" if DB_PATH.exists() else "  数据库大小: N/A")


# ==================== 主流程 ====================
def init_database(reset: bool = False):
    print("=" * 60)
    print("  电商产销协同管理系统 - 数据库初始化")
    print("=" * 60)

    if reset and DB_PATH.exists():
        print(f"\n[警告] 删除旧数据库: {DB_PATH}")
        try:
            DB_PATH.unlink()
        except PermissionError:
            print("✗ 数据库文件被占用，请先停止后端服务后再执行 --reset")
            sys.exit(1)
        for suffix in ["-wal", "-shm"]:
            f = Path(str(DB_PATH) + suffix)
            if f.exists():
                f.unlink()
        print("✓ 旧数据库已删除")

        # 清理二维码缓存
        if QR_CACHE_DIR.exists():
            shutil.rmtree(QR_CACHE_DIR)
            print("✓ 二维码缓存已清除")

    # 创建目录
    create_directories()

    # 连接数据库
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    try:
        # 建表
        print("\n>>> 创建/确认数据表结构")
        create_tables(conn)

        # 字段补全（向后兼容）
        ensure_columns(conn)

        # 清理业务数据（保留管理员和系统配置）：含全部图片的数据库记录
        clean_user_data(conn)

        # 清理磁盘图片文件与目录（临时图/订单正式图/商品图，含 --force 与 --reset）
        clean_disk_images()

        # 初始数据（补充缺失的管理员/配置）
        seed_all(conn)

        # 验证
        verify(conn)

    finally:
        conn.close()

    print("\n" + "=" * 60)
    print("  初始化成功！系统已就绪。")
    print("  默认管理员账号: 1001")
    print("  默认管理员密码: 1001")
    print("=" * 60)
    return True


# ==================== 可视化交互窗口（PySide6） ====================
def _db_status() -> dict:
    """读取数据库当前状态，返回统计信息（库不存在时返回空字典）。"""
    if not DB_PATH.exists():
        return {"exists": False}
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=5)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in c.fetchall()]
        counts = {}
        for t in tables:
            try:
                c.execute(f"SELECT COUNT(*) FROM {t}")
                counts[t] = c.fetchone()[0]
            except Exception:
                counts[t] = None
        admin = None
        try:
            c.execute("SELECT username, role FROM users WHERE username='1001'")
            admin = c.fetchone()
        except Exception:
            pass
        settings = None
        try:
            c.execute("SELECT COUNT(*) FROM system_settings")
            settings = c.fetchone()[0]
        except Exception:
            pass
        # 平台统计：区分系统默认项与自定义项（用于直观确认清理是否生效）
        plat_total = plat_default = plat_custom = None
        try:
            c.execute("SELECT platform_code, platform_name FROM platforms")
            rows = c.fetchall()
            plat_total = len(rows)
            plat_default = sum(
                1 for code, name in rows
                if code in SYSTEM_DEFAULT_PLATFORM_CODES or name in SYSTEM_DEFAULT_PLATFORM_NAMES
            )
            plat_custom = plat_total - plat_default
        except Exception:
            pass
        conn.close()
        return {
            "exists": True,
            "tables": tables,
            "counts": counts,
            "admin": admin,
            "settings": settings,
            "platforms_detail": {
                "total": plat_total,
                "default": plat_default,
                "custom": plat_custom,
            },
            "size_kb": DB_PATH.stat().st_size / 1024 if DB_PATH.exists() else 0,
        }
    except Exception as e:
        return {"exists": True, "error": str(e)}


def run_gui():
    """启动可视化交互窗口（状态总览 + 一键初始化 + 实时日志）。"""
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QTextEdit, QFrame, QGridLayout, QMessageBox,
    )
    from PySide6.QtCore import Qt, QThread, Signal, QObject

    class Worker(QObject):
        """后台执行初始化，print 输出通过信号回传主线程。"""
        line = Signal(str)
        done = Signal(bool, str)

        def __init__(self, reset=False):
            super().__init__()
            self.reset = reset

        def _hook_print(self, text='', **kw):
            self.line.emit(str(text))

        def run(self):
            import builtins
            orig_print = builtins.print
            builtins.print = lambda *a, **k: self._hook_print(' '.join(str(x) for x in a))
            try:
                ok = init_database(reset=self.reset)
                self.done.emit(True, '初始化完成' if ok else '初始化返回失败')
            except Exception as e:
                self.done.emit(False, f'初始化失败: {e}')
            finally:
                builtins.print = orig_print

    class InitWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("数据库初始化工具 - 电商产销协同管理系统")
            self.resize(760, 620)
            self._build_ui()
            self._thread = None
            self._worker = None
            self.refresh_status()

        def _build_ui(self):
            central = QWidget()
            self.setCentralWidget(central)
            root = QVBoxLayout(central)
            root.setContentsMargins(18, 16, 18, 16)
            root.setSpacing(12)

            # 标题
            title = QLabel("数据库初始化工具")
            title.setStyleSheet("font: bold 20px 'Microsoft YaHei'; color:#1f2329;")
            root.addWidget(title)
            sub = QLabel("创建/校验全部数据表，补充默认管理员、系统参数与基础数据。操作幂等，可重复执行。")
            sub.setStyleSheet("font: 12px 'Microsoft YaHei'; color:#646a73;")
            root.addWidget(sub)

            # 状态总览卡片
            card = QFrame()
            card.setStyleSheet(
                "QFrame{background:#f7f8fa; border:1px solid #e5e6eb; border-radius:10px;}")
            cv = QVBoxLayout(card)
            cv.setContentsMargins(16, 14, 16, 14)
            cv.setSpacing(8)
            cv.addWidget(QLabel("📊 数据库状态总览"))
            self.grid = QGridLayout()
            self.grid.setHorizontalSpacing(24)
            self.grid.setVerticalSpacing(6)
            cv.addLayout(self.grid)
            root.addWidget(card)

            # 按钮行
            btns = QHBoxLayout()
            btns.setSpacing(10)
            self.init_btn = QPushButton("▶ 执行初始化")
            self.init_btn.setFixedHeight(42)
            self.init_btn.setStyleSheet(
                "QPushButton{background:#3370ff; color:#fff; border:none; border-radius:8px;"
                " font: bold 14px 'Microsoft YaHei'; padding:0 28px;}"
                "QPushButton:hover{background:#4c82ff;}"
                "QPushButton:disabled{background:#a8c2ff;}")
            self.init_btn.clicked.connect(self._on_init)
            btns.addWidget(self.init_btn)
            self.refresh_btn = QPushButton("刷新状态")
            self.refresh_btn.setFixedHeight(42)
            self.refresh_btn.setStyleSheet(
                "QPushButton{background:#ffffff; color:#1f2329; border:1px solid #d0d3d9;"
                " border-radius:8px; font: 13px 'Microsoft YaHei'; padding:0 20px;}"
                "QPushButton:hover{background:#f2f3f5;}")
            self.refresh_btn.clicked.connect(self.refresh_status)
            btns.addWidget(self.refresh_btn)
            btns.addStretch()
            root.addLayout(btns)

            # 日志区
            log_label = QLabel("运行日志：")
            log_label.setStyleSheet("font: bold 12px 'Microsoft YaHei'; color:#1f2329;")
            root.addWidget(log_label)
            self.log_text = QTextEdit()
            self.log_text.setReadOnly(True)
            self.log_text.setStyleSheet(
                "QTextEdit{background:#1e1e1e; color:#d4d4d4; border-radius:8px;"
                " font: 12px Consolas, 'Courier New'; padding:10px;}")
            root.addWidget(self.log_text, 1)

        def _set_grid(self, key, val):
            r = self.grid.rowCount()
            k = QLabel(key)
            k.setStyleSheet("font: 12px 'Microsoft YaHei'; color:#646a73;")
            v = QLabel(str(val))
            v.setStyleSheet("font: bold 12px 'Microsoft YaHei'; color:#1f2329;")
            v.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.grid.addWidget(k, r, 0)
            self.grid.addWidget(v, r, 1)

        def refresh_status(self):
            # 清空旧格子
            while self.grid.count():
                item = self.grid.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            st = _db_status()
            if not st.get("exists"):
                self._set_grid("数据库", "不存在（首次运行将自动创建）")
                self._set_grid("表数量", "0")
                self._set_grid("管理员", "未创建")
                self._set_grid("系统参数", "未创建")
                return
            if "error" in st:
                self._set_grid("数据库", f"读取异常: {st['error']}")
                return
            tables = st["tables"]
            counts = st["counts"]
            self._set_grid("数据库", f"存在（{st['size_kb']:.1f} KB）")
            self._set_grid("数据表", f"{len(tables)} 张")
            admin = st["admin"]
            self._set_grid("管理员", f"{admin[0]} ({admin[1]})" if admin else "未创建")
            self._set_grid("系统参数", f"{st['settings']} 条" if st["settings"] is not None else "—")
            # 平台统计（总数 + 系统默认/自定义拆分，直观确认清理是否生效）
            pd = st.get("platforms_detail")
            if pd and pd["total"] is not None:
                self._set_grid(
                    "平台",
                    f"{pd['total']} 个（系统默认 {pd['default']} / 自定义 {pd['custom']}）",
                )
            # 关键表数据量
            table_labels = [
                ("users", "用户"),
                ("orders", "订单"),
                ("shops", "网店"),
                ("products", "商品"),
                ("categories", "类别"),
                ("brands", "品牌"),
                ("product_images", "商品图片"),
                ("order_imports", "订单导入"),
                ("non_trade_transactions", "非交易收支"),
                ("accounting_codes", "账务代码"),
                ("notifications", "站内信"),
                ("login_logs", "登录日志"),
                ("operation_logs", "操作日志"),
            ]
            for t, label in table_labels:
                if t in counts:
                    self._set_grid(label, f"{counts[t]} 条")
            self.log_text.append(f"✅ 状态已刷新：{len(tables)} 张表，{st['settings']} 条系统参数")

        def _append_log(self, text):
            self.log_text.append(text)
            sb = self.log_text.verticalScrollBar()
            sb.setValue(sb.maximum())

        def _verify_password(self):
            """验证特殊操作密码（当日日期 YYYYMMDD）。输入正确返回 True，取消/错误返回 False。"""
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox, QLineEdit
            today = datetime.now().strftime('%Y%m%d')

            def to_half_width(s):
                out = []
                for ch in s:
                    code = ord(ch)
                    if code == 0x3000:
                        code = 0x20
                    elif 0xFF01 <= code <= 0xFF5E:
                        code -= 0xFEE0
                    out.append(chr(code))
                return ''.join(out)

            def ask_password(title, label):
                """中文按钮的自定义密码输入对话框，返回 (text, ok)。"""
                dlg = QDialog(self)
                dlg.setWindowTitle(title)
                layout = QVBoxLayout(dlg)
                layout.addWidget(QLabel(label))
                edit = QLineEdit()
                edit.setEchoMode(QLineEdit.Password)
                layout.addWidget(edit)
                btn_box = QDialogButtonBox()
                btn_box.addButton("确认", QDialogButtonBox.AcceptRole)
                btn_box.addButton("取消", QDialogButtonBox.RejectRole)
                btn_box.accepted.connect(dlg.accept)
                btn_box.rejected.connect(dlg.reject)
                layout.addWidget(btn_box)
                edit.returnPressed.connect(dlg.accept)  # 回车直接确认
                ok = (dlg.exec() == QDialog.Accepted)
                return edit.text(), ok

            for attempt in range(3):
                text, ok = ask_password("身份验证", "请输入特殊操作密码")
                if not ok:
                    return False
                if to_half_width(text.strip()) == today:
                    return True
                if attempt < 2:
                    QMessageBox.warning(self, "密码错误", "密码错误，请重试")
            QMessageBox.warning(self, "验证失败", "密码错误次数过多，已取消初始化")
            return False

        def _on_init(self):
            if self._thread and self._thread.isRunning():
                return
            # 密码验证：特殊操作密码 = 当日日期 YYYYMMDD（如 20260810）
            if not self._verify_password():
                self._append_log("已取消初始化（密码验证未通过）")
                return
            self.init_btn.setEnabled(False)
            self.refresh_btn.setEnabled(False)
            self._append_log("开始执行初始化…")

            self._thread = QThread()
            self._worker = Worker(reset=False)
            self._worker.moveToThread(self._thread)
            self._thread.started.connect(self._worker.run)
            self._worker.line.connect(self._append_log)
            self._worker.done.connect(self._on_done)
            self._thread.start()

        def _on_done(self, ok, msg):
            self._append_log(f"\n{'✅' if ok else '❌'} {msg}")
            self.init_btn.setEnabled(True)
            self.refresh_btn.setEnabled(True)
            if self._thread:
                self._thread.quit()
                self._thread.wait()
            self.refresh_status()

    app = QApplication.instance() or QApplication(sys.argv[:1])
    win = InitWindow()
    win.show()
    sys.exit(app.exec())


# ==================== 入口 ====================
if __name__ == "__main__":
    # 默认：无参数启动可视化窗口；带 --cli/--force/--reset 走命令行模式
    if "--gui" in sys.argv or not any(a in sys.argv for a in ("--force", "--reset", "--cli")):
        run_gui()
        sys.exit(0)

    force = "--force" in sys.argv
    reset = "--reset" in sys.argv

    if reset:
        confirm = input("确定要重建数据库吗？所有数据将被删除！(yes/no): ")
        if confirm.strip().lower() != "yes":
            print("已取消")
            sys.exit(0)
    elif not force:
        if DB_PATH.exists():
            print(f"数据库已存在: {DB_PATH.absolute()}")
            print(f"大小: {DB_PATH.stat().st_size / 1024:.1f} KB")
            confirm = input("是否执行初始化（仅补充缺失表/字段/数据，不覆盖现有数据）？(yes/no): ")
            if confirm.strip().lower() != "yes":
                print("已取消")
                sys.exit(0)
        else:
            confirm = input("将创建新的数据库，是否继续？(yes/no): ")
            if confirm.strip().lower() != "yes":
                print("已取消")
                sys.exit(0)

    try:
        init_database(reset=reset)
    except Exception as e:
        print(f"\n✗ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        if not force:
            input("\n按 Enter 键退出...")
        sys.exit(1)

    if not force:
        input("\n按 Enter 键退出...")
