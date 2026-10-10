import asyncio
import random
from app.core.logging import logger
from app.core.database import AsyncSessionLocal
from app.repositories.product_repo import ProductRepository
from app.services.product_service import ProductService

# Concurrency lock to prevent overlapping check jobs
_is_checking = False


def is_price_check_running() -> bool:
    """Return whether a scheduled or on-demand full scan is currently running."""
    return _is_checking


async def check_all_products_job() -> bool:
    """
    Background job triggered periodically by APScheduler.
    Iterates through all active products and performs price refresh & alert triggers.
    """
    global _is_checking
    if _is_checking:
        logger.warning("[SCHEDULER] Previous price check job is still in progress. Skipping this iteration.")
        return False

    _is_checking = True
    logger.info("[SCHEDULER] Starting periodic price check for all active products...")

    try:
        async with AsyncSessionLocal() as session:
            try:
                repo = ProductRepository(session)
                active_products = await repo.get_all_active()
                logger.info(f"[SCHEDULER] Found {len(active_products)} active products to check.")

                # Shuffle products order to avoid repetitive crawling patterns
                product_list = list(active_products)
                random.shuffle(product_list)

                service = ProductService(session)
                for product in product_list:
                    try:
                        logger.info(f"[SCHEDULER] Checking price for product ID {product.id} - '{product.name[:30]}'")
                        await service.refresh_product_price(product.id)
                        
                        # Random polite delay between 2.0s and 4.0s to avoid bot detection/rate limit
                        delay = round(random.uniform(2.0, 4.0), 2)
                        await asyncio.sleep(delay)
                    except Exception as prod_err:
                        logger.error(f"[SCHEDULER ERROR] Failed checking product ID {product.id}: {str(prod_err)}")

                await session.commit()
            except Exception as db_err:
                await session.rollback()
                logger.error(f"[SCHEDULER DATABASE ERROR] {str(db_err)}")
    finally:
        _is_checking = False
        logger.info("[SCHEDULER] Periodic price check completed.")
    return True
