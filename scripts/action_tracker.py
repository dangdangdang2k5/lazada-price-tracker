import os
import sys
import json
import asyncio
from datetime import datetime
import httpx

from dotenv import load_dotenv
load_dotenv()

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add backend to path to reuse providers and utilities
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
backend_dir = os.path.join(root_dir, "backend")
sys.path.insert(0, backend_dir)

from app.services.providers.lazada import LazadaPriceProvider
from app.utils.currency import format_currency

PRODUCTS_FILE = os.path.join(root_dir, "products.json")


async def send_telegram_alert(bot_token: str, chat_id: str, message: str) -> bool:
    if not bot_token or not chat_id:
        print("[TELEGRAM] Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID. Skipping notification.")
        return False
    
    telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(telegram_url, json=payload)
            if resp.status_code == 200:
                print(f"[TELEGRAM] Sent message to chat {chat_id} successfully.")
                return True
            else:
                print(f"[TELEGRAM ERROR] Status: {resp.status_code}, Body: {resp.text}")
    except Exception as e:
        print(f"[TELEGRAM ERROR] Failed to send: {str(e)}")
    return False


async def check_products_round(provider: LazadaPriceProvider, products: list, bot_token: str, chat_id: str, round_num: int) -> bool:
    updated = False
    now_iso = datetime.utcnow().isoformat() + "Z"
    print(f"\n==================== [ROUND {round_num}] STARTING PRICE CHECK ====================")
    print(f"[INFO] Time: {datetime.now().strftime('%H:%M:%S')} - Checking {len(products)} product(s)...")

    for item in products:
        url = item.get("url")
        if not url:
            continue

        print(f"\n[CHECKING] {item.get('name', 'Product')} -> {url}")
        res = await provider.get_product_info(url)

        if not res.success or res.price <= 0:
            print(f"[FAILED] Could not get price: {res.error_message}")
            continue

        current_price = res.price
        old_price = item.get("last_price", 0)
        target_price = item.get("target_price", 0)
        product_name = res.name or item.get("name", "Lazada Product")

        print(f"[PRICE] Current: {format_currency(current_price)} (Old: {format_currency(old_price)}, Target: {format_currency(target_price)})")

        # Check conditions
        price_dropped = old_price > 0 and current_price < old_price
        price_increased = old_price > 0 and current_price > old_price
        target_hit = target_price > 0 and current_price <= target_price
        first_tracking = old_price == 0

        should_alert = price_dropped or price_increased or target_hit or first_tracking

        if should_alert:
            if target_hit:
                header = "🎯 <b>ĐÃ ĐẠT GIÁ MỤC TIÊU!</b>"
            elif price_dropped:
                pct = round(((old_price - current_price) / old_price) * 100, 1)
                header = f"🔥 <b>GIÁ ĐÃ GIẢM {pct}%!</b>"
            elif price_increased:
                pct = round(((current_price - old_price) / old_price) * 100, 1)
                header = f"📈 <b>GIÁ ĐÃ TĂNG (+{pct}%)!</b>"
            else:
                header = "🚀 <b>BẮT ĐẦU THEO DÕI SẢN PHẨM MỚI</b>"

            msg = (
                f"{header}\n\n"
                f"📦 <b>Sản phẩm:</b> {product_name}\n"
            )
            sku_name = item.get("sku_name") or res.sku_name
            if sku_name:
                msg += f"🏷️ <b>Phân loại:</b> {sku_name}\n"

            note = item.get("note")
            if note:
                msg += f"📝 <b>Ghi chú:</b> <i>{note}</i>\n"

            msg += f"💵 <b>Giá hiện tại:</b> <code>{format_currency(current_price)}</code>\n"
            if old_price > 0:
                msg += f"📊 <b>Giá trước đó:</b> <s>{format_currency(old_price)}</s>\n"
            if target_price > 0:
                msg += f"🎯 <b>Mục tiêu:</b> <code>{format_currency(target_price)}</code>\n"

            msg += f"\n🔗 <a href='{url}'>Mở link sản phẩm trên Lazada</a>"

            await send_telegram_alert(bot_token, chat_id, msg)

        # Update product data
        item["name"] = product_name
        if res.sku_name and not item.get("sku_name"):
            item["sku_name"] = res.sku_name
        item["last_price"] = current_price
        item["last_checked"] = now_iso
        if "history" not in item:
            item["history"] = []
        item["history"].append({
            "price": current_price,
            "timestamp": now_iso
        })
        # Keep last 50 history entries
        item["history"] = item["history"][-50:]
        updated = True

        # Small polite delay between products
        await asyncio.sleep(2.0)

    return updated


async def main():
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    if not os.path.exists(PRODUCTS_FILE):
        print(f"[ERROR] Products file not found: {PRODUCTS_FILE}")
        return

    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
        try:
            products = json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to read JSON: {e}")
            return

    if not products:
        print("[INFO] No products in list. Exiting.")
        return

    provider = LazadaPriceProvider()

    # ROUND 1 (At minute 0:00)
    updated_1 = await check_products_round(provider, products, bot_token, chat_id, round_num=1)

    # Sleep 140 seconds (~2.3 minutes) before Round 2
    SLEEP_SECONDS = 140
    print(f"\n[SLEEP] Waiting {SLEEP_SECONDS} seconds (~2.3 mins) for Round 2...")
    await asyncio.sleep(SLEEP_SECONDS)

    # ROUND 2 (At minute 2:30)
    updated_2 = await check_products_round(provider, products, bot_token, chat_id, round_num=2)

    # If manually triggered from GitHub Actions (workflow_dispatch) or requested via FORCE_REPORT, send an on-demand summary report
    event_name = os.environ.get("GITHUB_EVENT_NAME", "").strip()
    force_report = os.environ.get("FORCE_REPORT", "").strip() == "1"
    
    if (event_name == "workflow_dispatch" or force_report) and products:
        report_msg = (
            f"📋 <b>BÁO CÁO TRẠNG THÁI GIÁ LAZADA (Thủ công)</b>\n\n"
            f"⏰ <b>Thời gian:</b> {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n"
            f"📊 <b>Tổng theo dõi:</b> {len(products)} sản phẩm\n\n"
        )
        for idx, item in enumerate(products, 1):
            p_name = item.get("name", "Sản phẩm")
            p_price = item.get("last_price", 0)
            p_target = item.get("target_price", 0)
            p_sku = item.get("sku_name", "")
            p_note = item.get("note", "")

            report_msg += f"{idx}️⃣ <b>{p_name[:35]}...</b>\n"
            if p_sku:
                report_msg += f"🏷️ Phân loại: {p_sku}\n"
            if p_note:
                report_msg += f"📝 Ghi chú: {p_note}\n"
            report_msg += f"💵 Giá: <code>{format_currency(p_price)}</code> | 🎯 Mục tiêu: <code>{format_currency(p_target)}</code>\n\n"

        report_msg += "<i>✅ Tất cả sản phẩm đang được theo dõi tự động 24/7!</i>"
        await send_telegram_alert(bot_token, chat_id, report_msg)

    if updated_1 or updated_2:
        with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        print("\n[SUCCESS] Updated products.json with new price data.")
    
    print("\n[COMPLETE] 2-Round check completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
