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

# ==================== 路径配置 ====================
BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / "backend"
DATA_DIR = BACKEND_DIR / "data"
DB_DIR = DATA_DIR / "db"
IMAGES_DIR = DATA_DIR / "images"
TEMP_DIR = IMAGES_DIR / "temp"
OFFICIAL_DIR = IMAGES_DIR / "official"
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
    dirs = [DATA_DIR, DB_DIR, IMAGES_DIR, TEMP_DIR, OFFICIAL_DIR, BACKUP_DIR, LOGS_DIR, QR_CACHE_DIR]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    print("✓ 目录结构初始化完成")


# ==================== 建表 ====================
def create_tables(conn: sqlite3.Connection):
    cursor = conn.cursor()

    tables_sql = [
        # 用户表
        """CREATE TABLE IF NOT EXISTS users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            username        VARCHAR(50)  NOT NULL UNIQUE,
            password_hash   VARCHAR(255) NOT NULL,
            real_name       VARCHAR(100),
            role            VARCHAR(20)  NOT NULL DEFAULT 'sales',
            commission_rate INTEGER,
            is_active       BOOLEAN      DEFAULT 1,
            created_at      TIMESTAMP    DEFAULT (datetime('now', 'localtime')),
            updated_at      TIMESTAMP    DEFAULT (datetime('now', 'localtime'))
        )""",

        # 网店表
        """CREATE TABLE IF NOT EXISTS shops (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_id      VARCHAR(100) NOT NULL UNIQUE,
            shop_name    VARCHAR(100) NOT NULL UNIQUE,
            shop_account VARCHAR(100) NOT NULL UNIQUE,
            status       VARCHAR(20)  DEFAULT 'normal',
            creator      VARCHAR(50)  NOT NULL,
            create_time  TIMESTAMP    DEFAULT (datetime('now', 'localtime')),
            update_time  TIMESTAMP    DEFAULT (datetime('now', 'localtime'))
        )""",

        # 订单表
        """CREATE TABLE IF NOT EXISTS orders (
            id                       INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id                 VARCHAR(100) NOT NULL UNIQUE,
            shop_id                  VARCHAR(100),
            product_name             VARCHAR(255),
            platform_order_no        VARCHAR(100) NOT NULL UNIQUE,
            sales_amount             VARCHAR(20),
            shipping_status          VARCHAR(20)  DEFAULT 'pending',
            logistics_company        VARCHAR(100),
            logistics_no             VARCHAR(100),
            shipping_operator        VARCHAR(50),
            shipping_time            TIMESTAMP,
            receiver_address         TEXT,
            remark                   TEXT,
            commission_rate          INTEGER,
            commission_amount        VARCHAR(20),
            created_by               VARCHAR(50),
            created_at               TIMESTAMP    DEFAULT (datetime('now', 'localtime')),
            order_days               INTEGER      DEFAULT 0,
            commission_paid          BOOLEAN      DEFAULT 0,
            produce_status           VARCHAR(20)  DEFAULT 'unproduce',
            produce_status_update_at TIMESTAMP,
            produce_status_update_user VARCHAR(50),
            updated_at               TIMESTAMP    DEFAULT (datetime('now', 'localtime'))
        )""",

        # 图片表
        """CREATE TABLE IF NOT EXISTS images (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id      VARCHAR(100),
            temp_id       VARCHAR(100),
            image_type    VARCHAR(50),
            image_url     VARCHAR(500),
            thumbnail_url VARCHAR(500),
            image_hash    VARCHAR(64),
            is_main       INTEGER DEFAULT 0,
            uploaded_by   VARCHAR(50),
            is_locked     INTEGER DEFAULT 0,
            layer         VARCHAR(20)  DEFAULT 'sales',
            created_at    TIMESTAMP    DEFAULT (datetime('now', 'localtime')),
            updated_at    TIMESTAMP    DEFAULT (datetime('now', 'localtime'))
        )""",

        # 操作日志表
        """CREATE TABLE IF NOT EXISTS operation_logs (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id           INTEGER,
            username          VARCHAR(50),
            operation_type    VARCHAR(50) NOT NULL,
            operation_content TEXT,
            ip_address        VARCHAR(50),
            user_agent        TEXT,
            created_at        TIMESTAMP   DEFAULT (datetime('now', 'localtime'))
        )""",

        # 登录日志表
        """CREATE TABLE IF NOT EXISTS login_logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   VARCHAR(50) NOT NULL,
            login_time TIMESTAMP   DEFAULT (datetime('now', 'localtime')),
            ip_address VARCHAR(50),
            user_agent TEXT,
            status     VARCHAR(20) DEFAULT 'success'
        )""",

        # 系统设置表
        """CREATE TABLE IF NOT EXISTS system_settings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            key         VARCHAR(100) NOT NULL UNIQUE,
            value       TEXT,
            description VARCHAR(255),
            created_at  TIMESTAMP    DEFAULT (datetime('now', 'localtime')),
            updated_at  TIMESTAMP    DEFAULT (datetime('now', 'localtime'))
        )""",

        # 物流公司表
        """CREATE TABLE IF NOT EXISTS logistics_companies (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            company_code   VARCHAR(50)  NOT NULL UNIQUE,
            company_name   VARCHAR(100) NOT NULL UNIQUE,
            contact_person VARCHAR(50),
            contact_phone  VARCHAR(20),
            status         VARCHAR(20)  DEFAULT 'active',
            created_by     VARCHAR(50),
            created_at     TIMESTAMP    DEFAULT (datetime('now', 'localtime')),
            updated_at     TIMESTAMP    DEFAULT (datetime('now', 'localtime'))
        )""",

        # 日志清理记录表
        """CREATE TABLE IF NOT EXISTS log_cleanup_records (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            cleanup_type      VARCHAR(50)  NOT NULL,
            retention_days    INTEGER      NOT NULL,
            deleted_count     INTEGER      DEFAULT 0,
            status            VARCHAR(20)  DEFAULT 'pending',
            error_message     TEXT,
            start_time        TIMESTAMP    DEFAULT (datetime('now', 'localtime')),
            end_time          TIMESTAMP,
            triggered_by      VARCHAR(50),
            operator_username VARCHAR(50)
        )""",

        # 站内信表
        """CREATE TABLE IF NOT EXISTS notifications (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient_username VARCHAR(50)  NOT NULL,
            order_id           VARCHAR(100),
            event_type         VARCHAR(50)  NOT NULL,
            title              VARCHAR(200) NOT NULL,
            content            TEXT         NOT NULL,
            is_read            BOOLEAN      DEFAULT 0,
            read_at            TIMESTAMP,
            created_at         TIMESTAMP    DEFAULT (datetime('now', 'localtime'))
        )""",

        # 商品表
        """CREATE TABLE IF NOT EXISTS products (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            product_code   VARCHAR(50)  NOT NULL UNIQUE,
            product_name   VARCHAR(100) NOT NULL,
            product_remark TEXT,
            status         VARCHAR(20)  DEFAULT 'active',
            created_by     VARCHAR(50),
            created_at     TIMESTAMP    DEFAULT (datetime('now', 'localtime')),
            updated_at     TIMESTAMP    DEFAULT (datetime('now', 'localtime'))
        )""",

        # 网店提现记录表
        """CREATE TABLE IF NOT EXISTS shop_withdraw_record (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_id              VARCHAR(64)  NOT NULL,
            withdraw_date        VARCHAR(20)  NOT NULL,
            withdraw_amount      VARCHAR(20)  NOT NULL,
            remark               VARCHAR(500),
            create_operator_name VARCHAR(50)  NOT NULL,
            create_operator_id   INTEGER      NOT NULL,
            update_operator_name VARCHAR(50),
            update_operator_id   INTEGER,
            create_time          TIMESTAMP    DEFAULT (datetime('now', 'localtime')),
            update_time          TIMESTAMP    DEFAULT (datetime('now', 'localtime'))
        )""",
    ]

    for idx, sql in enumerate(tables_sql):
        table_name = sql.split("TABLE IF NOT EXISTS")[1].strip().split("(")[0].strip()
        cursor.execute(sql)
        print(f"  [{idx + 1:02d}] {table_name}")

    conn.commit()
    print(f"✓ 共 {len(tables_sql)} 张数据表创建/确认完成")


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
        ("log_cleanup_retention_days", "90", "操作日志保留天数"),
        ("system_version", "1.0.0", "当前系统版本号"),
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


# ==================== 兼容性检查 ====================
def ensure_columns(conn: sqlite3.Connection):
    """
    向后兼容：为旧数据库补充缺失字段。
    如果数据库已存在但缺少某字段，自动 ALTER TABLE 添加。
    """
    cursor = conn.cursor()

    migrations = {
        "orders": [
            ("order_days", "INTEGER DEFAULT 0"),
            ("commission_paid", "BOOLEAN DEFAULT 0"),
            ("commission_rate", "INTEGER"),
            ("commission_amount", "VARCHAR(20)"),
            ("produce_status", "VARCHAR(20) DEFAULT 'unproduce'"),
            ("produce_status_update_at", "TIMESTAMP"),
            ("produce_status_update_user", "VARCHAR(50)"),
        ],
        "users": [
            ("commission_rate", "INTEGER"),
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
        ("orders", "订单"),
        ("shops", "网店"),
        ("products", "商品"),
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

        # 清理图片存储
        if OFFICIAL_DIR.exists():
            file_count = sum(1 for _ in OFFICIAL_DIR.rglob("*") if _.is_file())
            shutil.rmtree(OFFICIAL_DIR)
            print(f"✓ 已删除 {file_count} 张已上传图片")
        if TEMP_DIR.exists():
            shutil.rmtree(TEMP_DIR)
            print("✓ 临时图片目录已清除")

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

        # 清理业务数据（保留管理员和系统配置）
        clean_user_data(conn)

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


# ==================== 入口 ====================
if __name__ == "__main__":
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
