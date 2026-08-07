"""users 表新增 data_permissions（数据权限 JSON 文本）列。"""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "db" / "order_system.db"


def main():
    if not DB.exists():
        print(f"[skip] 数据库不存在: {DB}")
        return
    conn = sqlite3.connect(str(DB))
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "data_permissions" in cols:
            print("[skip] users.data_permissions 已存在")
        else:
            conn.execute("ALTER TABLE users ADD COLUMN data_permissions TEXT")
            conn.commit()
            print("[ok] 已添加 users.data_permissions")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
