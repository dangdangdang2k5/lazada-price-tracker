import datetime
from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.alert import Alert


class AlertRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, alert_id: int) -> Optional[Alert]:
        query = select(Alert).where(Alert.id == alert_id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_by_product(self, product_id: int) -> List[Alert]:
        query = select(Alert).where(Alert.product_id == product_id).order_by(Alert.created_at.asc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, alert: Alert) -> Alert:
        self.session.add(alert)
        await self.session.flush()
        await self.session.refresh(alert)
        return alert

    async def update(self, alert: Alert) -> Alert:
        alert.updated_at = datetime.datetime.utcnow()
        await self.session.flush()
        await self.session.refresh(alert)
        return alert

    async def delete(self, alert: Alert) -> None:
        await self.session.delete(alert)
        await self.session.flush()
