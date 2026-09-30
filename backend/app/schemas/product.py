import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl
from app.schemas.alert import AlertResponse, AlertCreateInput


class ProductBase(BaseModel):
    url: str = Field(..., description="Lazada product URL")


class ProductCreate(ProductBase):
    name: Optional[str] = None
    sku_id: Optional[str] = None
    sku_name: Optional[str] = None
    note: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    current_price: Optional[int] = None
    original_price: Optional[int] = None
    # Optional list of alerts to create initially
    alerts: Optional[List[AlertCreateInput]] = None


class ProductPreviewRequest(BaseModel):
    url: str = Field(..., description="Lazada product URL to preview")


class ProductPreviewResponse(BaseModel):
    name: str
    url: str
    sku_id: Optional[str] = None
    sku_name: Optional[str] = None
    variations: Optional[List[dict]] = []
    image_url: Optional[str] = None
    price: int
    original_price: Optional[int] = None
    discount_percentage: Optional[float] = None
    formatted_price: str
    formatted_original_price: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
    error: Optional[str] = None


class ProductResponse(BaseModel):
    id: int
    name: str
    url: str
    sku_id: Optional[str] = None
    sku_name: Optional[str] = None
    note: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    current_price: int
    original_price: Optional[int] = None
    lowest_price: int
    highest_price: int
    active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime
    last_checked_at: Optional[datetime.datetime] = None
    
    # Formatted presentation helpers
    formatted_current_price: Optional[str] = None
    formatted_original_price: Optional[str] = None
    formatted_lowest_price: Optional[str] = None
    formatted_highest_price: Optional[str] = None
    discount_percent: Optional[float] = None
    price_change_from_prev: Optional[float] = None
    
    # Active alerts summary
    alerts: Optional[List[AlertResponse]] = []
    target_price: Optional[int] = None
    is_target_reached: Optional[bool] = False

    model_config = {"from_attributes": True}


class ProductListResponse(BaseModel):
    total: int
    items: List[ProductResponse]
