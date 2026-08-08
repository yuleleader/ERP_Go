"""
数据库迁移脚本：为订单表添加退款备注字段

迁移说明：
- 添加 refund_note 字段（文本，可空）
- 退款备注与订单普通备注（remark）是两个独立字段：
  订单状态为「已退货/退款」时编辑必填，用于记录退货退款原因
"""

import sqlite3

def migrate():
    db_path = "data/db/order_system.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 检查字段是否已存在
    cursor.execute("PRAGMA table_info(orders)")
    columns = [col[1] for col in cursor.fetchall()]

    if "refund_note" not in columns:
        print("添加 refund_note 字段...")
        cursor.execute("ALTER TABLE orders ADD COLUMN refund_note TEXT")
        conn.commit()
        print("✓ refund_note 字段已添加")
    else:
        print("refund_note 字段已存在，跳过")

    # 验证
    cursor.execute("PRAGMA table_info(orders)")
    cols = [col[1] for col in cursor.fetchall()]
    if "refund_note" in cols:
        print("✓ 当前 orders 表包含退款备注字段")

    conn.close()
    print("\n✅ 迁移完成！")

if __name__ == "__main__":
    migrate()
