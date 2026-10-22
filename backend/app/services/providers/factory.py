from typing import Optional
from urllib.parse import urlparse

from app.core.config import settings
from app.services.providers.base import BasePriceProvider
from app.services.providers.lazada import LazadaPriceProvider
from app.services.providers.lazada_authenticated import AuthenticatedLazadaPriceProvider
from app.services.providers.lazada_api import LazadaApiProvider


def get_price_provider_for_url(url: str, mode: Optional[str] = None) -> BasePriceProvider:
    """
    Factory function returning the appropriate provider based on the product URL
    and the configured PRICE_PROVIDER_MODE ('api' or 'scraper').
    """
    selected_mode = (mode or getattr(settings, "PRICE_PROVIDER_MODE", "api")).strip().lower()

    if selected_mode == "scraper":
        return LazadaPriceProvider()

    # Default to AuthenticatedLazadaPriceProvider (pure async HTTP + MTOP enrichment)
    return AuthenticatedLazadaPriceProvider()
