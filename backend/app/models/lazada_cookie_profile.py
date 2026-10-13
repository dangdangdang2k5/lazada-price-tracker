import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from app.core.database import Base


class LazadaCookieProfile(Base):
    """Non-secret metadata for a user-owned Lazada session cookie set."""

    __tablename__ = "lazada_cookie_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    label = Column(String(100), nullable=False)
    priority = Column(Integer, nullable=False, default=1, index=True)
    # The file is stored in the deployment secrets directory. Cookie values are
    # deliberately never placed in SQLite, API responses, logs, or Git.
    cookie_file = Column(Text, nullable=False, unique=True)
    status = Column(String(32), nullable=False, default="UNKNOWN")
    last_error_code = Column(String(64), nullable=True)
    last_verified_at = Column(DateTime, nullable=True)
    last_checked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)


class LazadaCookieState(Base):
    """Singleton state which remembers the selected cookie profile."""

    __tablename__ = "lazada_cookie_state"

    id = Column(Integer, primary_key=True, default=1)
    active_profile_id = Column(Integer, ForeignKey("lazada_cookie_profiles.id"), nullable=True)
    paused = Column(Boolean, nullable=False, default=False)
    all_invalid_notified = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
