from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.repositories.product_repo import ProductRepository

router = APIRouter(prefix="/stats", tags=["Statistics"])


@router.get("")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Get aggregated statistics for Dashboard KPI metrics.
    """
    repo = ProductRepository(db)
    products = await repo.get_all()

    total_products = len(products)
    active_tracking = sum(1 for p in products if p.active)
    
    reached_target_count = 0
    total_alerts_count = 0
    price_drops_count = 0

    for p in products:
        if p.alerts:
            total_alerts_count += len(p.alerts)
            for a in p.alerts:
                if a.alert_type == "TARGET_PRICE" and a.target_price:
                    if p.current_price <= a.target_price:
                        reached_target_count += 1

        if p.price_histories and len(p.price_histories) >= 2:
            if p.current_price < p.price_histories[1].price:
                price_drops_count += 1

    return {
        "total_products": total_products,
        "active_tracking": active_tracking,
        "reached_target_count": reached_target_count,
        "total_alerts_count": total_alerts_count,
        "price_drops_count": price_drops_count,
    }
