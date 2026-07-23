"""
数据库迁移脚本：为订单表添加滞留时长字段

迁移说明：
- 添加 order_days 字段（整型，单位：天）
- 计算并更新现有订单的滞留时长
"""

import sqlite3
from datetime import datetime

def migrate():
    db_path = "data/db/order_system.db"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. 检查字段是否已存在
    cursor.execute("PRAGMA table_info(orders)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "order_days" not in columns:
        print("添加 order_days 字段...")
        cursor.execute("ALTER TABLE orders ADD COLUMN order_days INTEGER DEFAULT 0")
        print("✓ order_days 字段已添加")
    else:
        print("order_days 字段已存在，跳过")
    
    # 2. 更新现有订单的滞留时长
    print("计算并更新现有订单的滞留时长...")
    
    cursor.execute("SELECT id, created_at FROM orders WHERE created_at IS NOT NULL")
    orders = cursor.fetchall()
    
    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day)
    
    updated_count = 0
    for order_id, created_at in orders:
        try:
            if isinstance(created_at, str):
                order_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            else:
                order_date = created_at
            
            order_date_start = datetime(order_date.year, order_date.month, order_date.day)
            days_diff = (today_start - order_date_start).days
            days_diff = max(0, days_diff)
            
            cursor.execute("UPDATE orders SET order_days = ? WHERE id = ?", (days_diff, order_id))
            updated_count += 1
        except Exception as e:
            print(f"  警告：订单 {order_id} 计算失败: {e}")
    
    conn.commit()
    print(f"✓ 已更新 {updated_count} 条订单的滞留时长")
    
    # 3. 验证
    cursor.execute("SELECT COUNT(*) FROM orders WHERE order_days IS NOT NULL")
    count = cursor.fetchone()[0]
    print(f"✓ 当前有 {count} 条订单包含滞留时长数据")
    
    conn.close()
    print("\n✅ 迁移完成！")

if __name__ == "__main__":
    migrate()
