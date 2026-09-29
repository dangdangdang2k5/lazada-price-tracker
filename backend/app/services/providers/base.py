from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel, Field


class ProductScrapedData(BaseModel):
    name: str = Field(..., description="Product title")
    price: int = Field(..., description="Current promotional / selling price in VND")
    original_price: Optional[int] = Field(None, description="Original list price before discount in VND")
    image_url: Optional[str] = Field(None, description="Main product image URL")
    url: str = Field(..., description="Canonical product URL")
    success: bool = True
    error_message: Optional[str] = None


class BasePriceProvider(ABC):
    """
    Abstract Price Provider Interface.
    Allows seamlessly swapping implementations (e.g. Lazada, Shopee, TikTok Shop, Playwright headless, official APIs)
    without modifying business logic or alert engines.
    """

    @abstractmethod
    async def get_product_info(self, url: str) -> ProductScrapedData:
        """
        Fetch and parse product details from given URL.
        Must return normalized ProductScrapedData.
        """
        pass
