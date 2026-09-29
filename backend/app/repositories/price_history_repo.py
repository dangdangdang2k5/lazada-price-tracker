import datetime
from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.price_history import PriceHistory


class PriceHistoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, product_id: int, price: int, checked_at: Optional[datetime.datetime] = None) -> PriceHistory:
        history = PriceHistory(
            product_id=product_id,
            price=price,
            checked_at=checked_at or datetime.datetime.utcnow()
        )
        self.session.add(history)
        await self.session.flush()
        await self.session.refresh(history)
        return history

    async def get_by_product(
        self,
        product_id: int,
        since: Optional[datetime.datetime] = None,
        limit: int = 1000
    ) -> List[PriceHistory]:
        query = select(PriceHistory).where(PriceHistory.product_id == product_id)
        if since:
            query = query.where(PriceHistory.checked_at >= since)
        query = query.order_by(PriceHistory.checked_at.asc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_latest(self, product_id: int) -> Optional[PriceHistory]:
        query = (
            select(PriceHistory)
            .where(PriceHistory.product_id == product_id)
            .order_by(PriceHistory.checked_at.desc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalars().first()
