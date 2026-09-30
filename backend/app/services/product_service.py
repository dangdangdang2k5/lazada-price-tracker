import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import logger
from app.models.product import Product
from app.models.price_history import PriceHistory
from app.models.alert import Alert, AlertType
from app.repositories.product_repo import ProductRepository
from app.repositories.price_history_repo import PriceHistoryRepository
from app.repositories.alert_repo import AlertRepository
from app.schemas.product import (
    ProductCreate,
    ProductResponse,
    ProductPreviewResponse,
)
from app.schemas.alert import AlertCreateInput, AlertResponse
from app.services.providers.factory import get_price_provider_for_url
from app.services.alert_engine import AlertEngine
from app.services.telegram_service import telegram_service
from app.utils.currency import format_currency
from app.utils.validators import normalize_lazada_url, is_valid_lazada_url


class ProductService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.product_repo = ProductRepository(session)
        self.history_repo = PriceHistoryRepository(session)
        self.alert_repo = AlertRepository(session)

    async def preview_product(self, url: str) -> ProductPreviewResponse:
        canonical_url = normalize_lazada_url(url)
        if not is_valid_lazada_url(canonical_url):
            return ProductPreviewResponse(
                name="Unknown",
                url=canonical_url,
                price=0,
                formatted_price="0đ",
                success=False,
                error_message="URL không phải đường dẫn sản phẩm Lazada hợp lệ."
            )

        provider = get_price_provider_for_url(canonical_url)
        scraped = await provider.get_product_info(canonical_url)
        if not scraped.success or scraped.price <= 0:
            return ProductPreviewResponse(
                name=scraped.name or "Sản phẩm Lazada",
                url=canonical_url,
                price=0,
                formatted_price="0đ",
                success=False,
                error_message=scraped.error_message or "Không thể lấy thông tin giá từ Lazada. Vui lòng kiểm tra lại URL."
            )

        discount_pct = None
        if scraped.original_price and scraped.original_price > scraped.price:
            discount_pct = round(((scraped.original_price - scraped.price) / scraped.original_price) * 100, 1)

        return ProductPreviewResponse(
            name=scraped.name,
            url=canonical_url,
            sku_id=scraped.sku_id,
            sku_name=scraped.sku_name,
            variations=scraped.variations or [],
            image_url=scraped.image_url,
            price=scraped.price,
            original_price=scraped.original_price,
            discount_percentage=discount_pct,
            formatted_price=format_currency(scraped.price),
            formatted_original_price=format_currency(scraped.original_price) if scraped.original_price else None,
            success=True
        )

    async def create_product(self, data: ProductCreate) -> Product:
        canonical_url = normalize_lazada_url(data.url)
        
        # Check if already tracked
        existing = await self.product_repo.get_by_url(canonical_url)
        if existing:
            return existing

        name = data.name
        price = data.current_price
        original_price = data.original_price
        image_url = data.image_url
        sku_id = data.sku_id
        sku_name = data.sku_name

        # If price or name missing, fetch via provider
        if not price or price <= 0 or not name:
            provider = get_price_provider_for_url(canonical_url)
            scraped = await provider.get_product_info(canonical_url)
            if not scraped.success or scraped.price <= 0:
                raise ValueError(scraped.error_message or "Không thể lấy thông tin sản phẩm từ URL này.")
            name = scraped.name
            price = scraped.price
            original_price = scraped.original_price
            image_url = scraped.image_url
            sku_id = sku_id or scraped.sku_id
            sku_name = sku_name or scraped.sku_name

        now = datetime.datetime.utcnow()
        product = Product(
            name=name,
            url=canonical_url,
            sku_id=sku_id,
            sku_name=sku_name,
            note=data.note,
            image_url=image_url,
            current_price=price,
            original_price=original_price,
            lowest_price=price,
            highest_price=original_price or price,
            active=True,
            created_at=now,
            updated_at=now,
            last_checked_at=now,
        )
        product = await self.product_repo.create(product)

        # Record initial price history
        await self.history_repo.add(product_id=product.id, price=price, checked_at=now)

        # Create alerts
        if data.alerts and len(data.alerts) > 0:
            for a in data.alerts:
                alert = Alert(
                    product_id=product.id,
                    alert_type=a.alert_type.value if hasattr(a.alert_type, "value") else str(a.alert_type),
                    target_price=a.target_price,
                    percentage=a.percentage,
                    enabled=a.enabled,
                    is_triggered=False,
                )
                await self.alert_repo.create(alert)
        else:
            # Default alerts: TARGET_PRICE (e.g. 90% of current) and PRICE_DROP
            default_target = int(price * 0.9)
            alert_target = Alert(
                product_id=product.id,
                alert_type=AlertType.TARGET_PRICE.value,
                target_price=default_target,
                enabled=True,
            )
            alert_drop = Alert(
                product_id=product.id,
                alert_type=AlertType.PRICE_DROP.value,
                enabled=True,
            )
            await self.alert_repo.create(alert_target)
            await self.alert_repo.create(alert_drop)

        # Re-fetch with loaded relationships
        return await self.product_repo.get_by_id(product.id)

    async def get_product(self, product_id: int) -> Optional[Product]:
        return await self.product_repo.get_by_id(product_id)

    async def list_products(
        self,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        filter_status: Optional[str] = None
    ) -> List[ProductResponse]:
        products = await self.product_repo.get_all(search=search)
        responses: List[ProductResponse] = []

        for p in products:
            res = self._format_product_response(p)
            # Filter checks
            if filter_status == "target_reached" and not res.is_target_reached:
                continue
            if filter_status == "price_drop" and (res.price_change_from_prev is None or res.price_change_from_prev >= 0):
                continue
            responses.append(res)

        # Sort
        if sort_by == "price_asc":
            responses.sort(key=lambda x: x.current_price)
        elif sort_by == "price_desc":
            responses.sort(key=lambda x: x.current_price, reverse=True)
        elif sort_by == "discount_desc":
            responses.sort(key=lambda x: x.discount_percent or 0, reverse=True)
        elif sort_by == "drop_desc":
            responses.sort(key=lambda x: x.price_change_from_prev or 0)

        return responses

    async def delete_product(self, product_id: int) -> bool:
        product = await self.product_repo.get_by_id(product_id)
        if not product:
            return False
        await self.product_repo.delete(product)
        return True

    async def refresh_product_price(self, product_id: int) -> Optional[ProductResponse]:
        product = await self.product_repo.get_by_id(product_id)
        if not product:
            return None

        provider = get_price_provider_for_url(product.url)
        scraped = await provider.get_product_info(product.url)

        if not scraped.success or scraped.price <= 0:
            logger.warning(f"[REFRESH] Could not update price for product ID {product.id}: {scraped.error_message}")
            return self._format_product_response(product)

        old_price = product.current_price
        new_price = scraped.price
        old_lowest = product.lowest_price
        now = datetime.datetime.utcnow()

        logger.info(
            f"[PRICE CHECK] Product '{product.name}' | Old: {old_price} | New: {new_price} | Diff: {new_price - old_price}"
        )

        # Update product record
        product.current_price = new_price
        if scraped.original_price:
            product.original_price = scraped.original_price
        if scraped.image_url:
            product.image_url = scraped.image_url
        if scraped.name and len(scraped.name) > 5:
            product.name = scraped.name

        product.lowest_price = min(product.lowest_price, new_price) if product.lowest_price > 0 else new_price
        product.highest_price = max(product.highest_price, new_price)
        product.last_checked_at = now
        product.updated_at = now

        # Add price history entry
        await self.history_repo.add(product_id=product.id, price=new_price, checked_at=now)

        # Evaluate alerts
        alerts = await self.alert_repo.get_by_product(product.id)
        eval_result = AlertEngine.evaluate_alerts(
            product=product,
            old_price=old_price,
            new_price=new_price,
            old_lowest_price=old_lowest,
            alerts=alerts
        )

        # Persist alert updates
        for alert in alerts:
            await self.alert_repo.update(alert)

        await self.product_repo.update(product)

        # Send Telegram notification if alerts triggered
        if eval_result.should_notify and telegram_service.is_configured():
            await telegram_service.send_product_alert(
                product_name=product.name,
                product_url=product.url,
                old_price=old_price,
                new_price=new_price,
                target_price=eval_result.target_price,
                trigger_reasons=eval_result.reasons,
                image_url=product.image_url
            )

        return self._format_product_response(product)

    def _format_product_response(self, product: Product) -> ProductResponse:
        # Compute discount percent from original price
        discount_percent = None
        if product.original_price and product.original_price > product.current_price:
            discount_percent = round(((product.original_price - product.current_price) / product.original_price) * 100, 1)

        # Compute price change from previous history
        price_change_from_prev = None
        if product.price_histories and len(product.price_histories) >= 2:
            prev_price = product.price_histories[1].price
            if prev_price > 0:
                price_change_from_prev = round(((product.current_price - prev_price) / prev_price) * 100, 2)

        # Find target price alert
        target_price = None
        is_target_reached = False
        alert_responses: List[AlertResponse] = []
        if product.alerts:
            for a in product.alerts:
                alert_resp = AlertResponse(
                    id=a.id,
                    product_id=a.product_id,
                    alert_type=a.alert_type,
                    target_price=a.target_price,
                    percentage=a.percentage,
                    enabled=a.enabled,
                    is_triggered=a.is_triggered,
                    last_triggered_price=a.last_triggered_price,
                    last_triggered_at=a.last_triggered_at,
                    created_at=a.created_at,
                    formatted_target_price=format_currency(a.target_price) if a.target_price else None,
                )
                alert_responses.append(alert_resp)
                if a.alert_type == AlertType.TARGET_PRICE.value and a.target_price:
                    target_price = a.target_price
                    if product.current_price <= a.target_price:
                        is_target_reached = True

        return ProductResponse(
            id=product.id,
            name=product.name,
            url=product.url,
            sku_id=product.sku_id,
            sku_name=product.sku_name,
            note=product.note,
            image_url=product.image_url,
            current_price=product.current_price,
            original_price=product.original_price,
            lowest_price=product.lowest_price,
            highest_price=product.highest_price,
            active=product.active,
            created_at=product.created_at,
            updated_at=product.updated_at,
            last_checked_at=product.last_checked_at,
            formatted_current_price=format_currency(product.current_price),
            formatted_original_price=format_currency(product.original_price) if product.original_price else None,
            formatted_lowest_price=format_currency(product.lowest_price),
            formatted_highest_price=format_currency(product.highest_price),
            discount_percent=discount_percent,
            price_change_from_prev=price_change_from_prev,
            alerts=alert_responses,
            target_price=target_price,
            is_target_reached=is_target_reached,
        )
