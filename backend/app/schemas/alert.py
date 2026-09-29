import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.alert import AlertType


class AlertBase(BaseModel):
    alert_type: AlertType = Field(..., description="Alert type enum")
    target_price: Optional[int] = Field(None, description="Target price in VND for TARGET_PRICE alerts")
    percentage: Optional[float] = Field(None, description="Percentage for PERCENT_DROP alerts")
    enabled: bool = True


class AlertCreateInput(AlertBase):
    pass


class AlertCreate(AlertBase):
    product_id: int


class AlertUpdate(BaseModel):
    alert_type: Optional[AlertType] = None
    target_price: Optional[int] = None
    percentage: Optional[float] = None
    enabled: Optional[bool] = None


class AlertResponse(BaseModel):
    id: int
    product_id: int
    alert_type: str
    target_price: Optional[int] = None
    percentage: Optional[float] = None
    enabled: bool
    is_triggered: bool
    last_triggered_price: Optional[int] = None
    last_triggered_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime

    # Presentation helper
    formatted_target_price: Optional[str] = None

    model_config = {"from_attributes": True}
