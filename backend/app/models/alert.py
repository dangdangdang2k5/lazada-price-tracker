import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class AlertType(str, Enum):
    TARGET_PRICE = "TARGET_PRICE"
    PRICE_DROP = "PRICE_DROP"
    PRICE_INCREASE = "PRICE_INCREASE"
    PERCENT_DROP = "PERCENT_DROP"
    NEW_LOWEST_PRICE = "NEW_LOWEST_PRICE"


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)  # TARGET_PRICE, PRICE_DROP, etc.
    target_price = Column(Integer, nullable=True)     # For TARGET_PRICE
    percentage = Column(Float, nullable=True)         # For PERCENT_DROP (e.g. 10.0 = 10%)
    enabled = Column(Boolean, default=True, nullable=False)
    
    # Anti-spam and trigger tracking state
    is_triggered = Column(Boolean, default=False, nullable=False)
    last_triggered_price = Column(Integer, nullable=True)
    last_triggered_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    # Relationship
    product = relationship("Product", back_populates="alerts")

    def __repr__(self) -> str:
        return f"<Alert id={self.id} type={self.alert_type} target={self.target_price} enabled={self.enabled}>"
