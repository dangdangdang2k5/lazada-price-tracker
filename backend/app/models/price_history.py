import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base


class PriceHistory(Base):
    __tablename__ = "price_histories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    price = Column(Integer, nullable=False)
    checked_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)

    # Relationship
    product = relationship("Product", back_populates="price_histories")

    __table_args__ = (
        Index("idx_product_checked_at", "product_id", "checked_at"),
    )

    def __repr__(self) -> str:
        return f"<PriceHistory product_id={self.product_id} price={self.price} time={self.checked_at}>"
