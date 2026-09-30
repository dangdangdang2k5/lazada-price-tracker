from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.alert import Alert
from app.repositories.alert_repo import AlertRepository
from app.repositories.product_repo import ProductRepository
from app.schemas.alert import (
    AlertCreate,
    AlertCreateInput,
    AlertUpdate,
    AlertResponse,
)
from app.utils.currency import format_currency

router = APIRouter(tags=["Alerts"])


def format_alert_response(alert: Alert) -> AlertResponse:
    return AlertResponse(
        id=alert.id,
        product_id=alert.product_id,
        alert_type=alert.alert_type,
        target_price=alert.target_price,
        percentage=alert.percentage,
        enabled=alert.enabled,
        is_triggered=alert.is_triggered,
        last_triggered_price=alert.last_triggered_price,
        last_triggered_at=alert.last_triggered_at,
        created_at=alert.created_at,
        formatted_target_price=format_currency(alert.target_price) if alert.target_price else None,
    )


@router.post("/products/{product_id}/alerts", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    product_id: int,
    payload: AlertCreateInput,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new alert rule for a specific product.
    """
    p_repo = ProductRepository(db)
    product = await p_repo.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại")

    a_repo = AlertRepository(db)
    alert = Alert(
        product_id=product_id,
        alert_type=payload.alert_type.value if hasattr(payload.alert_type, "value") else str(payload.alert_type),
        target_price=payload.target_price,
        percentage=payload.percentage,
        enabled=payload.enabled,
    )
    saved = await a_repo.create(alert)
    return format_alert_response(saved)


@router.get("/products/{product_id}/alerts", response_model=List[AlertResponse])
async def get_product_alerts(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all alert configurations for a product.
    """
    a_repo = AlertRepository(db)
    alerts = await a_repo.get_by_product(product_id)
    return [format_alert_response(a) for a in alerts]


@router.put("/alerts/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    payload: AlertUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing alert configuration.
    """
    a_repo = AlertRepository(db)
    alert = await a_repo.get_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Không tìm thấy cài đặt cảnh báo")

    if payload.alert_type is not None:
        alert.alert_type = payload.alert_type.value if hasattr(payload.alert_type, "value") else str(payload.alert_type)
    if payload.target_price is not None:
        alert.target_price = payload.target_price
        # Reset triggered flag when target price is modified
        alert.is_triggered = False
    if payload.percentage is not None:
        alert.percentage = payload.percentage
    if payload.enabled is not None:
        alert.enabled = payload.enabled

    saved = await a_repo.update(alert)
    return format_alert_response(saved)


@router.delete("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an alert rule.
    """
    a_repo = AlertRepository(db)
    alert = await a_repo.get_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Không tìm thấy cài đặt cảnh báo")
    await a_repo.delete(alert)
    return None


@router.post("/alerts/{alert_id}/enable", response_model=AlertResponse)
async def enable_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Enable a disabled alert rule.
    """
    a_repo = AlertRepository(db)
    alert = await a_repo.get_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Không tìm thấy cài đặt cảnh báo")
    alert.enabled = True
    alert.is_triggered = False
    saved = await a_repo.update(alert)
    return format_alert_response(saved)


@router.post("/alerts/{alert_id}/disable", response_model=AlertResponse)
async def disable_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Disable an alert rule without deleting it.
    """
    a_repo = AlertRepository(db)
    alert = await a_repo.get_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Không tìm thấy cài đặt cảnh báo")
    alert.enabled = False
    alert.is_triggered = False
    saved = await a_repo.update(alert)
    return format_alert_response(saved)
