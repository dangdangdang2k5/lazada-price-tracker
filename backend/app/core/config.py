import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Lazada Price Tracker"
    DEBUG: bool = True
    LAZADA_DEBUG: bool = False
    DATABASE_URL: str = "sqlite+aiosqlite:///./lazada_tracker.db"
    # Keep deployment data outside the source tree on a VPS.
    LAZADA_COOKIE_FILE: str = "cache/lazada_cookies.json"
    LAZADA_DEBUG_DIR: str = "debug/lazada"
    
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

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_flag(cls, v):
        # Existing deployments use DEBUG=release/development as a mode name.
        if isinstance(v, str) and v.lower() in {"release", "production", "prod", "false", "0"}:
            return False
        if isinstance(v, str) and v.lower() in {"development", "dev", "true", "1"}:
            return True
        return v

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
