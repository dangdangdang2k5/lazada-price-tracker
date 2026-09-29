from fastapi import APIRouter
from app.api.products import router as products_router
from app.api.alerts import router as alerts_router
from app.api.telegram import router as telegram_router
from app.api.stats import router as stats_router

api_router = APIRouter(prefix="/api")
api_router.include_router(products_router)
api_router.include_router(alerts_router)
api_router.include_router(telegram_router)
api_router.include_router(stats_router)

__all__ = ["api_router"]
