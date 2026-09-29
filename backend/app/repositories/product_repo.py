import datetime
from typing import Optional, List
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.product import Product


class ProductRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, product_id: int) -> Optional[Product]:
        query = (
            select(Product)
            .where(Product.id == product_id)
            .options(selectinload(Product.alerts), selectinload(Product.price_histories))
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_by_url(self, url: str) -> Optional[Product]:
        query = (
            select(Product)
            .where(Product.url == url)
            .options(selectinload(Product.alerts))
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_all_active(self) -> List[Product]:
        query = (
            select(Product)
            .where(Product.active == True)
            .options(selectinload(Product.alerts), selectinload(Product.price_histories))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_all(self, search: Optional[str] = None) -> List[Product]:
        query = select(Product).options(selectinload(Product.alerts), selectinload(Product.price_histories))
        if search:
            query = query.where(Product.name.ilike(f"%{search}%"))
        query = query.order_by(Product.created_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, product: Product) -> Product:
        self.session.add(product)
        await self.session.flush()
        await self.session.refresh(product)
        return product

    async def update(self, product: Product) -> Product:
        product.updated_at = datetime.datetime.utcnow()
        await self.session.flush()
        await self.session.refresh(product)
        return product

    async def delete(self, product: Product) -> None:
        await self.session.delete(product)
        await self.session.flush()
