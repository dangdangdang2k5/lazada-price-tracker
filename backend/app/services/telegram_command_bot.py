"""Small Telegram long-polling command listener for the single FastAPI process."""

import asyncio
import datetime
import html
import json
import time
from pathlib import Path
from typing import Any, Optional

import httpx
from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.jobs.price_checker import check_all_products_job, is_price_check_running
from app.jobs.scheduler import scheduler
from app.models.product import Product
from app.services.telegram_service import telegram_service
from app.utils.currency import format_currency


COMMAND_KEYBOARD = {
    "keyboard": [["/status", "/check"], ["/products", "/session"], ["/help"]],
    "resize_keyboard": True,
    "is_persistent": True,
}


class TelegramCommandBot:
    """Process updates from the configured chat only; no public webhook is needed."""

    def __init__(self) -> None:
        self._task: Optional[asyncio.Task[None]] = None
        self._on_demand_check_task: Optional[asyncio.Task[None]] = None
        self._offset = 0
        self._started_at: Optional[datetime.datetime] = None
        self._offset_file = Path(settings.TELEGRAM_UPDATE_OFFSET_FILE).expanduser() if settings.TELEGRAM_UPDATE_OFFSET_FILE else None

    def enabled(self) -> bool:
        return settings.TELEGRAM_COMMAND_POLLING_ENABLED and telegram_service.is_configured()

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if not self.enabled():
            logger.info("[TELEGRAM BOT] Command polling disabled or Telegram is not configured.")
            return
        if self.running:
            return
        self._offset = self._load_offset()
        self._started_at = datetime.datetime.now(datetime.timezone.utc)
        self._task = asyncio.create_task(self._poll_forever(), name="telegram-command-poller")
        logger.info("[TELEGRAM BOT] Command polling started for the configured chat.")

    async def stop(self) -> None:
        if self._on_demand_check_task and not self._on_demand_check_task.done():
            self._on_demand_check_task.cancel()
            try:
                await self._on_demand_check_task
            except asyncio.CancelledError:
                pass
        if not self._task:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("[TELEGRAM BOT] Command polling stopped.")

    def _load_offset(self) -> int:
        if not self._offset_file or not self._offset_file.exists():
            return 0
        try:
            return max(0, int(json.loads(self._offset_file.read_text(encoding="utf-8")).get("offset", 0)))
        except Exception as exc:
            logger.warning(f"[TELEGRAM BOT] Could not read update offset: {exc}")
            return 0

    def _save_offset(self) -> None:
        if not self._offset_file:
            return
        try:
            self._offset_file.parent.mkdir(parents=True, exist_ok=True)
            temp_file = self._offset_file.with_suffix(self._offset_file.suffix + ".tmp")
            temp_file.write_text(json.dumps({"offset": self._offset}), encoding="utf-8")
            temp_file.replace(self._offset_file)
        except Exception as exc:
            logger.warning(f"[TELEGRAM BOT] Could not save update offset: {exc}")

    async def _poll_forever(self) -> None:
        token = telegram_service.bot_token
        if not token:
            return
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        timeout = max(5, min(settings.TELEGRAM_COMMAND_POLL_TIMEOUT_SECONDS, 50))
        async with httpx.AsyncClient(timeout=timeout + 10) as client:
            if self._offset == 0:
                await self._discard_pending_updates(client, url)
            while True:
                try:
                    response = await client.post(url, json={
                        "offset": self._offset,
                        "timeout": timeout,
                        "allowed_updates": ["message"],
                    })
                    payload = response.json()
                    if response.status_code != 200 or not payload.get("ok"):
                        logger.error(f"[TELEGRAM BOT] getUpdates failed: {response.status_code} {payload}")
                        await asyncio.sleep(5)
                        continue
                    for update in payload.get("result", []):
                        self._offset = max(self._offset, int(update["update_id"]) + 1)
                        self._save_offset()
                        await self._handle_update(update)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.error(f"[TELEGRAM BOT] Polling error: {exc}")
                    await asyncio.sleep(5)

    async def _discard_pending_updates(self, client: httpx.AsyncClient, url: str) -> None:
        """Do not execute old /check commands when polling is enabled for the first time."""
        try:
            response = await client.post(url, json={"offset": -1, "limit": 1, "timeout": 0, "allowed_updates": ["message"]})
            payload = response.json()
            updates = payload.get("result", []) if response.status_code == 200 and payload.get("ok") else []
            if updates:
                self._offset = int(updates[-1]["update_id"]) + 1
                self._save_offset()
                logger.info("[TELEGRAM BOT] Discarded pending updates before command polling started.")
        except Exception as exc:
            logger.warning(f"[TELEGRAM BOT] Could not discard pending updates: {exc}")

    async def _handle_update(self, update: dict[str, Any]) -> None:
        message = update.get("message") or {}
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id", ""))
        text = (message.get("text") or "").strip()
        if not text:
            return
        if chat_id != str(settings.TELEGRAM_CHAT_ID):
            logger.warning(f"[TELEGRAM BOT] Ignored command from unauthorized chat {chat_id}.")
            return

        command = text.split(maxsplit=1)[0].split("@", 1)[0].lower()
        handlers = {
            "/start": self._send_help,
            "/help": self._send_help,
            "/status": self._send_status,
            "/session": self._send_session_status,
            "/products": self._send_products,
            "/check": self._start_price_check,
        }
        handler = handlers.get(command)
        if handler:
            await handler()
        else:
            await telegram_service.send_message("Không nhận ra lệnh. Gõ /help để xem các lệnh có sẵn.", reply_markup=COMMAND_KEYBOARD)

    async def _send_help(self) -> None:
        await telegram_service.send_message(
            "<b>Lazada Price Tracker Bot</b>\n\n"
            "/status — tình trạng service và scheduler\n"
            "/check — quét giá ngay (không chạy trùng)\n"
            "/products — danh sách sản phẩm đang theo dõi\n"
            "/session — tình trạng cookie Lazada",
            reply_markup=COMMAND_KEYBOARD,
        )

    async def _send_status(self) -> None:
        total, active = await self._product_counts()
        uptime = "chưa rõ"
        if self._started_at:
            elapsed = datetime.datetime.now(datetime.timezone.utc) - self._started_at
            uptime = str(elapsed).split(".", 1)[0]
        await telegram_service.send_message(
            "<b>Trạng thái tracker</b>\n\n"
            "✅ FastAPI: đang chạy\n"
            f"{'🟡' if is_price_check_running() else '✅'} Quét giá: {'đang chạy' if is_price_check_running() else 'rảnh'}\n"
            f"{'✅' if scheduler.running else '❌'} Scheduler: {'đang chạy' if scheduler.running else 'dừng'}\n"
            f"📦 Sản phẩm: {active}/{total} active\n"
            f"⏱ Uptime bot: {uptime}",
            reply_markup=COMMAND_KEYBOARD,
        )

    async def _send_session_status(self) -> None:
        cookie_file = Path(settings.LAZADA_COOKIE_FILE).expanduser()
        if not cookie_file.exists():
            text = "<b>Session Lazada</b>\n\n❌ Chưa có cookie được lưu."
        else:
            try:
                cookies = json.loads(cookie_file.read_text(encoding="utf-8"))
                now = time.time()
                expired = sum(1 for item in cookies if item.get("expirationDate") and float(item["expirationDate"]) <= now)
                status = "⚠️ Cần cập nhật" if cookies and expired == len(cookies) else "✅ Đang có thể dùng"
                text = f"<b>Session Lazada</b>\n\n{status}\nCookie: {len(cookies)}\nĐã hết hạn: {expired}"
            except Exception:
                text = "<b>Session Lazada</b>\n\n❌ File cookie không hợp lệ."
        await telegram_service.send_message(text, reply_markup=COMMAND_KEYBOARD)

    async def _send_products(self) -> None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Product).where(Product.active.is_(True)).order_by(Product.updated_at.desc()).limit(10))
            products = list(result.scalars().all())
            total = await session.scalar(select(func.count()).select_from(Product).where(Product.active.is_(True))) or 0
        if not products:
            text = "<b>Sản phẩm đang theo dõi</b>\n\nChưa có sản phẩm active."
        else:
            lines = [f"<b>Sản phẩm đang theo dõi ({total})</b>"]
            for product in products:
                name = html.escape(product.name)
                lines.append(f"• {name[:55]} — <b>{format_currency(product.current_price)}</b>")
            if total > len(products):
                lines.append(f"\n… và {total - len(products)} sản phẩm khác.")
            text = "\n".join(lines)
        await telegram_service.send_message(text, reply_markup=COMMAND_KEYBOARD)

    async def _start_price_check(self) -> None:
        if is_price_check_running() or (self._on_demand_check_task and not self._on_demand_check_task.done()):
            await telegram_service.send_message("🟡 Một lượt quét giá đang chạy. Không khởi tạo lượt thứ hai.", reply_markup=COMMAND_KEYBOARD)
            return
        await telegram_service.send_message("🔄 Đã bắt đầu quét giá. Mình sẽ báo khi hoàn tất.", reply_markup=COMMAND_KEYBOARD)
        self._on_demand_check_task = asyncio.create_task(self._run_price_check(), name="telegram-on-demand-price-check")

    async def _run_price_check(self) -> None:
        try:
            completed = await check_all_products_job()
            if completed:
                await telegram_service.send_message("✅ Đã quét xong danh sách sản phẩm.", reply_markup=COMMAND_KEYBOARD)
        except Exception as exc:
            logger.exception("[TELEGRAM BOT] On-demand price check failed")
            await telegram_service.send_message(f"❌ Quét giá thất bại: {str(exc)[:180]}", reply_markup=COMMAND_KEYBOARD)

    async def _product_counts(self) -> tuple[int, int]:
        async with AsyncSessionLocal() as session:
            total = await session.scalar(select(func.count()).select_from(Product)) or 0
            active = await session.scalar(select(func.count()).select_from(Product).where(Product.active.is_(True))) or 0
            return total, active


telegram_command_bot = TelegramCommandBot()
