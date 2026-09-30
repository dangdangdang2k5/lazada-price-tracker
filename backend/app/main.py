import os
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings
from app.core.database import init_db, AsyncSessionLocal
from app.core.logging import logger
from app.jobs.scheduler import start_scheduler, shutdown_scheduler
from app.api import api_router


from sqlalchemy import select
from app.models.product import Product
from app.models.alert import Alert, AlertType


async def auto_seed_products():
    """
    Automatically import products from products.json on startup if DB is empty or has missing items.
    """
    products_file = None
    for p in ["products.json", "../products.json", "/app/products.json"]:
        if os.path.exists(p):
            products_file = p
            break
    if not products_file:
        return
    try:
        with open(products_file, "r", encoding="utf-8") as f:
            items = json.load(f)
        if not items:
            return
        async with AsyncSessionLocal() as session:
            for it in items:
                url = it.get("url")
                if not url:
                    continue
                stmt = select(Product).where(Product.url == url)
                res = await session.execute(stmt)
                existing = res.scalar_one_or_none()
                if not existing:
                    p = Product(
                        name=it.get("name") or "Lazada Product",
                        url=url,
                        current_price=it.get("last_price", 0),
                        lowest_price=it.get("last_price", 0),
                        highest_price=it.get("last_price", 0),
                        active=True
                    )
                    session.add(p)
                    await session.flush()
                    target_price = it.get("target_price", 0)
                    if target_price > 0:
                        alert = Alert(
                            product_id=p.id,
                            alert_type=AlertType.TARGET_PRICE,
                            target_price=target_price,
                            enabled=True
                        )
                        session.add(alert)
            await session.commit()
            logger.info("[INIT] Auto-seeded products from products.json into database.")
    except Exception as e:
        logger.warning(f"[INIT] Auto-seed products skipped or failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing application and database schemas...")
    await init_db()
    await auto_seed_products()
    logger.info("Starting background scheduler...")
    start_scheduler()
    yield
    logger.info("Shutting down application scheduler...")
    shutdown_scheduler()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Automated price tracking and Telegram alert system for Lazada products",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attach API routes
app.include_router(api_router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "debug": settings.DEBUG,
    }


# Static frontend serving (for unified Docker deployment)
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_dir = os.path.join(base_dir, "static")
if not os.path.exists(static_dir):
    static_dir = os.path.join(os.getcwd(), "static")

if os.path.exists(static_dir):
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("redoc") or full_path.startswith("openapi.json"):
            return FileResponse(os.path.join(static_dir, "index.html"))
        file_path = os.path.join(static_dir, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(static_dir, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
