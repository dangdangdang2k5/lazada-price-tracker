import datetime
import html
from typing import Optional, Dict, Any, List
import httpx
from app.core.config import settings
from app.core.logging import logger
from app.utils.currency import format_currency


class TelegramService:
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or settings.TELEGRAM_CHAT_ID

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    async def send_message(
        self,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a formatted text message to Telegram channel/chat.
        Includes retry mechanism and error handling so it won't crash callers.
        """
        if not self.is_configured():
            logger.warning("[TELEGRAM] Bot token or Chat ID is not configured.")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload: Dict[str, Any] = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": False
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        async with httpx.AsyncClient(timeout=10.0) as client:
            for attempt in range(1, 3):
                try:
                    response = await client.post(url, json=payload)
                    if response.status_code == 200:
                        logger.info(f"[TELEGRAM SEND] Message successfully sent to chat {self.chat_id}")
                        return True
                    else:
                        logger.error(f"[TELEGRAM ERROR] Status {response.status_code}: {response.text}")
                except Exception as e:
                    logger.error(f"[TELEGRAM ATTEMPT {attempt} FAILED] {str(e)}")
        return False

    async def test_connection(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        custom_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Test Telegram Bot connection and send a test message.
        """
        token = bot_token or self.bot_token
        target_chat = chat_id or self.chat_id

        if not token or not target_chat:
            return {
                "success": False,
                "message": "Vui lòng cung cấp TELEGRAM_BOT_TOKEN và TELEGRAM_CHAT_ID trong .env hoặc form test."
            }

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        text = custom_message or (
            "✅ <b>KẾT NỐI TELEGRAM THÀNH CÔNG!</b>\n\n"
            "🤖 <b>Lazada Price Tracker Bot</b> đã được kết nối với chat này.\n"
            f"⏰ <b>Thời gian:</b> {now_str}\n"
            "🔔 Bạn sẽ nhận được thông báo ngay khi giá sản phẩm Lazada thay đổi hoặc đạt mục tiêu."
        )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json={
                    "chat_id": target_chat,
                    "text": text,
                    "parse_mode": "HTML"
                })
                data = res.json()
                if res.status_code == 200 and data.get("ok"):
                    chat_title = data.get("result", {}).get("chat", {}).get("title") or data.get("result", {}).get("chat", {}).get("first_name")
                    return {
                        "success": True,
                        "message": "Kết nối thành công! Đã gửi tin nhắn test tới Telegram.",
                        "chat_title": chat_title
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Telegram API Error: {data.get('description', res.text)}"
                    }
        except Exception as e:
            return {
                "success": False,
                "message": f"Network / Request Exception: {str(e)}"
            }

    async def send_product_alert(
        self,
        product_name: str,
        product_url: str,
        old_price: int,
        new_price: int,
        target_price: Optional[int] = None,
        trigger_reasons: Optional[List[str]] = None,
        image_url: Optional[str] = None
    ) -> bool:
        """
        Send a beautifully formatted alert message with product details and action button.
        """
        diff = new_price - old_price
        diff_str = format_currency(abs(diff))
        now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

        # Header and icons
        if diff < 0:
            header = "🔥 <b>GIÁ SẢN PHẨM VỪA GIẢM!</b>"
            diff_display = f"📉 <b>Giảm:</b> {diff_str} (-{abs(diff)/old_price*100:.2f}%)" if old_price > 0 else f"📉 <b>Giảm:</b> {diff_str}"
        elif diff > 0:
            header = "⚠️ <b>GIÁ SẢN PHẨM VỪA TĂNG</b>"
            diff_display = f"📈 <b>Tăng:</b> +{diff_str} (+{diff/old_price*100:.2f}%)" if old_price > 0 else f"📈 <b>Tăng:</b> +{diff_str}"
        else:
            header = "🚨 <b>LAZADA PRICE ALERT</b>"
            diff_display = "⚖️ <b>Không đổi</b>"

        safe_product_name = html.escape(product_name)
        reasons_text = ""
        if trigger_reasons:
            reasons_text = "\n".join([f"✨ <i>{html.escape(r)}</i>" for r in trigger_reasons])

        target_display = ""
        if target_price:
            target_display = f"🎯 <b>Giá mục tiêu:</b> {format_currency(target_price)}\n"
            if new_price <= target_price:
                target_display += "✅ <b>ĐÃ ĐẠT / THẤP HƠN GIÁ MỤC TIÊU!</b>\n"

        message = (
            f"{header}\n\n"
            f"📦 <b>{safe_product_name}</b>\n\n"
            f"💰 <b>Giá cũ:</b> {format_currency(old_price)}\n"
            f"🔥 <b>Giá mới:</b> {format_currency(new_price)}\n"
            f"{diff_display}\n"
            f"{target_display}"
            f"{reasons_text}\n"
            f"⏰ <i>{now_str}</i>\n"
        )

        reply_markup = {
            "inline_keyboard": [
                [{"text": "🔗 MỞ SẢN PHẨM TRÊN LAZADA", "url": product_url}]
            ]
        }

        return await self.send_message(text=message, reply_markup=reply_markup)


telegram_service = TelegramService()
