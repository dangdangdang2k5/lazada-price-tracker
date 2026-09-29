import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.core.database import Base


class TelegramConfig(Base):
    __tablename__ = "telegram_configs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    bot_token = Column(String(255), nullable=True)
    chat_id = Column(String(100), nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<TelegramConfig id={self.id} enabled={self.enabled}>"
