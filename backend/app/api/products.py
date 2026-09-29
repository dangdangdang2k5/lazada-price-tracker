import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.repositories.price_history_repo import PriceHistoryRepository
from app.schemas.product import (
    ProductCreate,
    ProductResponse,
    ProductListResponse,
    ProductPreviewRequest,
    ProductPreviewResponse,
)
from app.schemas.price_history import PriceHistoryResponse, PriceHistoryListResponse
from app.services.product_service import ProductService
from app.utils.currency import format_currency

router = APIRouter(prefix="/products", tags=["Products"])


@router.post("/preview", response_model=ProductPreviewResponse)
async def preview_product(
    payload: ProductPreviewRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch and preview Lazada product information before adding to tracking.
    """
    service = ProductService(db)
    result = await service.preview_product(payload.url)
    return result


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Add a new Lazada product to tracking list with initial alert configurations.
    """
    service = ProductService(db)
    try:
        product = await service.create_product(payload)
        return service._format_product_response(product)
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi thêm sản phẩm: {str(e)}")


@router.get("", response_model=ProductListResponse)
async def list_products(
    search: Optional[str] = Query(None, description="Search keyword for product title"),
    sort_by: Optional[str] = Query(None, description="Sorting mode: price_asc, price_desc, discount_desc, drop_desc"),
    filter_status: Optional[str] = Query(None, description="Filter mode: target_reached, price_drop"),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve all tracked products with search, sorting, and filter capabilities.
    """
    service = ProductService(db)
    items = await service.list_products(search=search, sort_by=sort_by, filter_status=filter_status)
    return ProductListResponse(total=len(items), items=items)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed product data by ID.
    """
    service = ProductService(db)
    product = await service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại")
    return service._format_product_response(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a product and all its history and alerts.
    """
    service = ProductService(db)
    success = await service.delete_product(product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại")
    return None


@router.post("/{product_id}/refresh", response_model=ProductResponse)
async def refresh_product_price(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Immediately trigger a live price check for a single product.
    """
    service = ProductService(db)
    result = await service.refresh_product_price(product_id)
    if not result:
        raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại")
    return result


@router.get("/{product_id}/history", response_model=PriceHistoryListResponse)
async def get_product_price_history(
    product_id: int,
    range: Optional[str] = Query("all", description="Time range: 24h, 7d, 30d, all"),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve historical price entries for plotting graphs and inspection.
    """
    repo = PriceHistoryRepository(db)
    now = datetime.datetime.utcnow()
    since = None

    if range == "24h":
        since = now - datetime.timedelta(hours=24)
    elif range == "7d":
        since = now - datetime.timedelta(days=7)
    elif range == "30d":
        since = now - datetime.timedelta(days=30)

    histories = await repo.get_by_product(product_id=product_id, since=since)
    
    items = [
        PriceHistoryResponse(
            id=h.id,
            product_id=h.product_id,
            price=h.price,
            checked_at=h.checked_at,
            formatted_price=format_currency(h.price)
        )
        for h in histories
    ]
    return PriceHistoryListResponse(product_id=product_id, total=len(items), items=items)
