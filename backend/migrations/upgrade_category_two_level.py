# -*- coding: utf-8 -*-
"""
数据库迁移脚本：类别表升级为两级结构

迁移说明：
- category_code 由 INTEGER 改为 TEXT（一级三位 002，二级六位 002001）
- 新增 parent_id（上级类别 id，空表示一级）
- 新增 level（1=一级，2=二级）
- 存量一级类别编码统一补零为三位字符串

幂等：重复执行不会破坏数据；若 categories 表尚未创建则直接跳过（由 create_all 建新表）。

用法：cd backend && python migrations/upgrade_category_two_level.py
"""

import os
import sqlite3

DB_PATH = os.path.join("data", "db", "order_system.db")


def migrate(db_path: str = DB_PATH):
    if not os.path.exists(db_path):
        print(f"数据库不存在：{db_path}，跳过迁移")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    exists = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='categories'"
    ).fetchone()
    if not exists:
        print("categories 表尚未创建，跳过迁移（首次启动后端会按新结构自动建表）")
        conn.close()
        return

    cols = {row[1]: row[2].upper() for row in cur.execute("PRAGMA table_info(categories)").fetchall()}
    need_rebuild = cols.get("category_code", "").startswith("INT")
    need_parent = "parent_id" not in cols
    need_level = "level" not in cols

    if not (need_rebuild or need_parent or need_level):
        print("categories 表已是两级结构，无需迁移")
        conn.close()
        return

    if need_rebuild:
        # SQLite 的 INTEGER 亲和性会把 '002' 转回数字 2，必须重建表才能保留前导零
        print("重建 categories 表（category_code -> TEXT）...")
        rows = cur.execute("SELECT id, category_code, category_name, created_by, created_at, updated_at FROM categories").fetchall()
        cur.execute("ALTER TABLE categories RENAME TO categories_old_migrate")
        cur.execute("""
            CREATE TABLE categories (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                category_code VARCHAR(20) NOT NULL,
                category_name VARCHAR(100) NOT NULL,
                parent_id INTEGER,
                level INTEGER NOT NULL DEFAULT 1,
                created_by VARCHAR(50),
                created_at DATETIME,
                updated_at DATETIME
            )
        """)
        for _id, code, name, created_by, created_at, updated_at in rows:
            new_code = str(code or "").zfill(3)
            cur.execute(
                "INSERT INTO categories (id, category_code, category_name, parent_id, level, created_by, created_at, updated_at)"
                " VALUES (?, ?, ?, NULL, 1, ?, ?, ?)",
                (_id, new_code, name, created_by, created_at, updated_at)
            )
        cur.execute("DROP TABLE categories_old_migrate")
        print(f"✓ 已迁移 {len(rows)} 条类别数据")
    else:
        if need_parent:
            cur.execute("ALTER TABLE categories ADD COLUMN parent_id INTEGER")
            print("✓ 已添加 parent_id 字段")
        if need_level:
            cur.execute("ALTER TABLE categories ADD COLUMN level INTEGER NOT NULL DEFAULT 1")
            print("✓ 已添加 level 字段")

    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_categories_category_code ON categories (category_code)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_categories_parent_id ON categories (parent_id)")

    conn.commit()
    total = cur.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    conn.close()
    print(f"\n✅ 迁移完成，当前类别共 {total} 条")


if __name__ == "__main__":
    migrate()
