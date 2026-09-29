from urllib.parse import urlparse
from app.services.providers.base import BasePriceProvider
from app.services.providers.lazada import LazadaPriceProvider


def get_price_provider_for_url(url: str) -> BasePriceProvider:
    """
    Factory function returning the appropriate provider based on the product URL.
    Enables future integration of ShopeePriceProvider, TikTokShopPriceProvider, etc.
    """
    domain = urlparse(url).netloc.lower()
    if "lazada" in domain:
        return LazadaPriceProvider()
    # Default to Lazada provider for lazada URLs or as primary fallback
    return LazadaPriceProvider()
