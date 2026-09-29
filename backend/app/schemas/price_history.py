import datetime
from typing import Optional, List
from pydantic import BaseModel


class PriceHistoryCreate(BaseModel):
    product_id: int
    price: int
    checked_at: Optional[datetime.datetime] = None


class PriceHistoryResponse(BaseModel):
    id: int
    product_id: int
    price: int
    checked_at: datetime.datetime
    formatted_price: Optional[str] = None

    model_config = {"from_attributes": True}


class PriceHistoryListResponse(BaseModel):
    product_id: int
    total: int
    items: List[PriceHistoryResponse]
