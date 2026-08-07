"""
orders 表新增 gross_profit（毛利）列并回填存量数据。
- 加列：ALTER TABLE ADD COLUMN gross_profit REAL（可空，直接执行）
- 回填：毛利 = CAST(sales_amount AS REAL) - 商品成本价（products 表按 product_name 匹配，
  无匹配或未填成本按 0）；销售金额为空/非数字按 0 处理
安全：表/列存在才操作；products 表不存在时跳过回填。
"""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "db" / "order_system.db"


def has_table(conn, table):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def has_column(conn, table, col):
    return any(r[1] == col for r in conn.execute(f"PRAGMA table_info({table})").fetchall())


def main():
    if not DB.exists():
        print(f"[skip] 数据库不存在: {DB}")
        return
    conn = sqlite3.connect(str(DB))
    try:
        if not has_table(conn, "orders"):
            print("[skip] orders 表不存在")
            return
        if not has_column(conn, "orders", "gross_profit"):
            conn.execute("ALTER TABLE orders ADD COLUMN gross_profit REAL")
            conn.commit()
            print("[ok] 已添加 orders.gross_profit")
        else:
            print("[skip] orders.gross_profit 已存在")

        # 回填存量：毛利 = 销售额 - 成本价（products 按商品名匹配）
        if has_table(conn, "products"):
            conn.execute("""
                UPDATE orders
                SET gross_profit = ROUND(
                    COALESCE(CAST(sales_amount AS REAL), 0)
                    - COALESCE((SELECT cost_price FROM products
                                WHERE products.product_name = orders.product_name
                                LIMIT 1), 0), 2)
            """)
            conn.commit()
            n = conn.execute(
                "SELECT COUNT(*) FROM orders WHERE gross_profit IS NOT NULL"
            ).fetchone()[0]
            print(f"[ok] 已回填毛利，共 {n} 条订单有毛利值")
        else:
            print("[warn] products 表不存在，跳过存量回填（新建订单时仍会计算）")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
