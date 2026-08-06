# -*- coding: utf-8 -*-
"""
迁移脚本：为 products 表新增价格与备注字段。
- cost_price   FLOAT     # 成本价
- retail_price FLOAT     # 零售价
- min_price    FLOAT     # 最低售价
- remark1      VARCHAR(500)
- remark2      VARCHAR(500)
- remark3      VARCHAR(500)

商品图片表 product_images 由 init_db() 的 Base.metadata.create_all 自动创建，
无需手工迁移。
"""
import os
import sqlite3
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "db", "order_system.db")

ADD_COLUMNS = [
    ("cost_price", "FLOAT"),
    ("retail_price", "FLOAT"),
    ("min_price", "FLOAT"),
    ("remark1", "VARCHAR(500)"),
    ("remark2", "VARCHAR(500)"),
    ("remark3", "VARCHAR(500)"),
]


def main():
    if not os.path.exists(DB_PATH):
        print(f"[跳过] 数据库文件不存在: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

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