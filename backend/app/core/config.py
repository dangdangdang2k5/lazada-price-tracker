import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Lazada Price Tracker"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite+aiosqlite:///./lazada_tracker.db"
    
    # Telegram credentials
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    
    # Scheduler interval (Randomized between MIN and MAX seconds)
    PRICE_CHECK_MIN_INTERVAL_SECONDS: int = 120  # 2 minutes
    PRICE_CHECK_MAX_INTERVAL_SECONDS: int = 180  # 3 minutes
    PRICE_CHECK_INTERVAL_MINUTES: int = 2
    
    # CORS Origins
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
