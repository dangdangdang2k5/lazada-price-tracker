from typing import Optional
from pydantic import BaseModel


class TelegramTestRequest(BaseModel):
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None
    custom_message: Optional[str] = None


class TelegramTestResponse(BaseModel):
    success: bool
    message: str
    chat_title: Optional[str] = None


class TelegramStatusResponse(BaseModel):
    configured: bool
    bot_token_masked: Optional[str] = None
    chat_id: Optional[str] = None
    is_valid: bool
