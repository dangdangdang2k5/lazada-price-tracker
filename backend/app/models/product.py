import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(500), nullable=False)
    url = Column(Text, nullable=False, unique=True, index=True)
    sku_id = Column(String(100), nullable=True)
    sku_name = Column(String(255), nullable=True)
    note = Column(Text, nullable=True)
    category = Column(String(100), nullable=True, index=True)
    image_url = Column(Text, nullable=True)
    current_price = Column(Integer, nullable=False, default=0)
    original_price = Column(Integer, nullable=True)
    lowest_price = Column(Integer, nullable=False, default=0)
    highest_price = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
    last_checked_at = Column(DateTime, nullable=True)

    # Relationships
    price_histories = relationship("PriceHistory", back_populates="product", cascade="all, delete-orphan", order_by="PriceHistory.checked_at.desc()")
    alerts = relationship("Alert", back_populates="product", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Product id={self.id} name='{self.name[:30]}' price={self.current_price}>"
