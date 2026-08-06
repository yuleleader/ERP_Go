# -*- coding: utf-8 -*-
"""
迁移脚本：为 products 表新增 category_id / brand_id 字段，
用于商品与类别、品牌的关联（商品管理页左侧类别/品牌导航筛选）。
"""
import os
import sqlite3
import sys

# 定位数据库文件（与 upgrade_category_two_level.py 一致）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "db", "order_system.db")

ADD_COLUMNS = [
    ("category_id", "INTEGER"),
    ("brand_id", "INTEGER"),
]


def main():
    if not os.path.exists(DB_PATH):
        print(f"[跳过] 数据库文件不存在: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 查询现有列
    existing = {row[1] for row in cur.execute("PRAGMA table_info(products)").fetchall()}
    added = []
    for col, col_type in ADD_COLUMNS:
        if col in existing:
            print(f"[已存在] 列 {col} 已存在，跳过")
            continue
        cur.execute(f"ALTER TABLE products ADD COLUMN {col} {col_type}")
        added.append(col)

    conn.commit()
    conn.close()

    if added:
        print(f"[完成] products 表已新增列: {', '.join(added)}")
    else:
        print("[完成] 无需变更")


if __name__ == "__main__":
    sys.exit(main())
