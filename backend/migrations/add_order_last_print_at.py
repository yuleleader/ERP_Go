"""
为 orders 表新增 last_print_at（上次打印时间）。
安全：表存在才执行；列存在则跳过；SQLite 可空列直接 ADD COLUMN。
"""
import sqlite3, sys
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "db" / "order_system.db"


def has_column(conn, table, col):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == col for row in cur.fetchall())


def main():
    if not DB.exists():
        print(f"[skip] 数据库不存在: {DB}")
        return
    conn = sqlite3.connect(str(DB))
    try:
        if has_column(conn, "orders", "last_print_at"):
            print("[skip] orders.last_print_at 已存在")
        else:
            conn.execute("ALTER TABLE orders ADD COLUMN last_print_at DATETIME")
            conn.commit()
            print("[ok] 已添加 orders.last_print_at")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
