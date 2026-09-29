import os
import sys
import json
import sqlite3
import subprocess

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
db_path = os.path.join(root_dir, "backend", "lazada_tracker.db")
products_file = os.path.join(root_dir, "products.json")

if not os.path.exists(db_path):
    print(f"[ERROR] Database not found at: {db_path}")
    sys.exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get products and their target price from alerts if any
cursor.execute("""
    SELECT p.id, p.name, p.url, p.current_price, 
           (SELECT threshold_value FROM alerts a WHERE a.product_id = p.id AND a.alert_type = 'TARGET_PRICE' LIMIT 1) as target_price
    FROM products p
    WHERE p.active = 1
""")
rows = cursor.fetchall()

products_data = []
for row in rows:
    # Get price history
    cursor.execute("SELECT price, checked_at FROM price_histories WHERE product_id = ? ORDER BY checked_at DESC LIMIT 50", (row["id"],))
    hist_rows = cursor.fetchall()
    history = [{"price": h["price"], "timestamp": h["checked_at"]} for h in reversed(hist_rows)]

    products_data.append({
        "id": row["id"],
        "name": row["name"],
        "url": row["url"],
        "target_price": int(row["target_price"]) if row["target_price"] else int(row["current_price"] * 0.9),
        "last_price": int(row["current_price"]),
        "history": history
    })

conn.close()

with open(products_file, "w", encoding="utf-8") as f:
    json.dump(products_data, f, ensure_ascii=False, indent=2)

print(f"[OK] Đã xuất {len(products_data)} sản phẩm từ Web vào file products.json.")

# Git auto push
try:
    print("[GIT] Đang tự động đẩy lên GitHub Actions...")
    subprocess.run(["git", "add", "products.json"], check=True, cwd=root_dir)
    subprocess.run(["git", "commit", "-m", f"Sync {len(products_data)} products from Web UI"], cwd=root_dir)
    subprocess.run(["git", "push", "origin", "main"], check=True, cwd=root_dir)
    print("[SUCCESS] Đã đồng bộ lên GitHub thành công! GitHub Actions sẽ tự động quét các sản phẩm này.")
except Exception as e:
    print(f"[NOTE] Đã lưu file nhưng chưa push git: {e}")
