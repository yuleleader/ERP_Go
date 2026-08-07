# -*- coding: utf-8 -*-
"""
迁移脚本：users 表新增 price_permissions（价格权限）字段。
- price_permissions VARCHAR(100) NULL，逗号分隔（如 "cost_price,retail_price,min_price"）
- NULL/空 = 全部可见（老用户向后兼容，不做变更）
"""
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "db", "order_system.db")


def main():
    if not os.path.exists(DB_PATH):
        print(f"[跳过] 数据库文件不存在: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    existing = {row[1] for row in cur.execute("PRAGMA table_info(users)").fetchall()}
    if "price_permissions" in existing:
        print("[已存在] users.price_permissions 已存在，跳过")
    else:
        cur.execute("ALTER TABLE users ADD COLUMN price_permissions VARCHAR(100)")
        print("[完成] users 表已新增列 price_permissions")

    conn.commit()
    conn.close()
    print("[完成] 迁移结束")


if __name__ == "__main__":
    main()
