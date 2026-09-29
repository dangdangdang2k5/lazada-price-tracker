from fastapi import APIRouter
from app.core.config import settings
from app.schemas.telegram import (
    TelegramTestRequest,
    TelegramTestResponse,
    TelegramStatusResponse,
)
from app.services.telegram_service import telegram_service

router = APIRouter(prefix="/telegram", tags=["Telegram"])


@router.post("/test", response_model=TelegramTestResponse)
async def test_telegram_connection(payload: TelegramTestRequest):
    """
    Test Telegram connection and send verification message.
    """
    result = await telegram_service.test_connection(
        bot_token=payload.bot_token,
        chat_id=payload.chat_id,
        custom_message=payload.custom_message
    )
    return TelegramTestResponse(
        success=result["success"],
        message=result["message"],
        chat_title=result.get("chat_title")
    )


@router.get("/status", response_model=TelegramStatusResponse)
async def get_telegram_status():
    """
    Check if Telegram Bot token and chat ID are configured in backend environment.
    """
    configured = telegram_service.is_configured()
    token = settings.TELEGRAM_BOT_TOKEN
    masked_token = None
    if token and len(token) > 10:
        masked_token = f"{token[:6]}...{token[-4:]}"

    return TelegramStatusResponse(
        configured=configured,
        bot_token_masked=masked_token,
        chat_id=settings.TELEGRAM_CHAT_ID if settings.TELEGRAM_CHAT_ID else None,
        is_valid=configured
    )
