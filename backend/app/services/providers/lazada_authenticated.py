import logging
import time
from typing import Any, Dict, Optional

from app.services.providers.base import BasePriceProvider, ProductScrapedData
from app.services.providers.lazada_pdp_client import LazadaPdpClient
from app.utils.validators import is_valid_lazada_url

logger = logging.getLogger("AuthenticatedLazadaPriceProvider")


class AuthenticatedLazadaPriceProvider(BasePriceProvider):
    """
    High-performance price provider for Lazada.
    Uses LazadaPdpClient with pure asynchronous HTTP (httpx) and MTOP price enrichment.
    Zero Playwright / Headless Browser dependencies.
    """

    CACHE_TTL_SECONDS = 60
    _price_cache: Dict[str, Any] = {}

    def __init__(self, timeout_seconds: float = 15.0):
        self.pdp_client = LazadaPdpClient(timeout_seconds=timeout_seconds)

    async def get_product_info(
        self,
        url: str,
        use_cache: bool = True,
        watch_item_id: Optional[Any] = None,
    ) -> ProductScrapedData:
        """
        Fetch and parse product details from given URL.
        Converts PdpSnapshotResult to standard ProductScrapedData.
        """
        if not is_valid_lazada_url(url):
            return ProductScrapedData(
                name="Unknown Product",
                price=0,
                url=url,
                success=False,
                error_message="Invalid or unsupported Lazada product URL",
                error_code="PRODUCT_NOT_FOUND",
            )

        logger.info(
            f"Fetching product prices for watchItemId={watch_item_id or 'unknown'} url={url}"
        )

        item_id, sku_id = self.pdp_client.extract_item_and_sku_id(url)
        cache_key = f"{item_id or url}:{sku_id or ''}"

        if use_cache and cache_key in self._price_cache:
            entry = self._price_cache[cache_key]
            if time.monotonic() - entry["at"] < self.CACHE_TTL_SECONDS:
                return entry["data"].model_copy(deep=True)

        snapshot = await self.pdp_client.fetch_pdp_snapshot(url)

        if not snapshot.success or not snapshot.chosen_variation:
            return ProductScrapedData(
                name=snapshot.title or "Lazada Product",
                price=0,
                url=snapshot.resolved_url or url,
                success=False,
                error_message=snapshot.error_message or "Failed to extract product price",
                error_code=snapshot.error_code or "PRICE_EXTRACTION_FAILED",
            )

        chosen = snapshot.chosen_variation
        variations_list = [
            {
                "sku_id": v.sku_id,
                "name": v.variant_name,
                "price": v.price,
                "original_price": v.original_price,
                "available": v.available,
                "image": v.image,
                "url": v.url,
            }
            for v in snapshot.variations
        ]

        data = ProductScrapedData(
            name=snapshot.title,
            price=chosen.price,
            original_price=chosen.original_price if (chosen.original_price and chosen.original_price > chosen.price) else None,
            sku_id=chosen.sku_id,
            sku_name=chosen.variant_name,
            image_url=chosen.image or snapshot.main_image,
            url=chosen.url or snapshot.resolved_url,
            variations=variations_list,
            success=True,
        )

        if use_cache and data.price > 0:
            self._price_cache[cache_key] = {"at": time.monotonic(), "data": data}

        return data

