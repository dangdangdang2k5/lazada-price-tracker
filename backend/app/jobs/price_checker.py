import asyncio
import random
from app.core.logging import logger
from app.core.database import AsyncSessionLocal
from app.repositories.product_repo import ProductRepository
from app.services.product_service import ProductService
from app.services.lazada_cookie_manager import cookie_manager

# Concurrency lock to prevent overlapping check jobs
_is_checking = False


def is_price_check_running() -> bool:
    """Return whether a scheduled or on-demand full scan is currently running."""
    return _is_checking


async def check_all_products_job() -> bool:
    """
    Background job triggered periodically by APScheduler.
    Iterates through all active products and performs price refresh & alert triggers
    concurrently using asyncio.Semaphore(5) and asyncio.gather with polite jitter (0.5s - 1.5s).
    """
    global _is_checking
    if _is_checking:
        logger.warning("[SCHEDULER] Previous price check job is still in progress. Skipping this iteration.")
        return False

    _is_checking = True
    logger.info("[SCHEDULER] Starting periodic price check for all active products...")

    try:
        if await cookie_manager.is_paused():
            logger.warning("[SCHEDULER] Lazada session requests are paused until a valid cookie profile is updated.")
            return True

        # Fetch all active products
        async with AsyncSessionLocal() as init_session:
            repo = ProductRepository(init_session)
            active_products = await repo.get_all_active()
            product_list = list(active_products)

        if not product_list:
            logger.info("[SCHEDULER] No active products found to check.")
            return True

        logger.info(f"[SCHEDULER] Found {len(product_list)} active products to check (Concurrency: Semaphore=5).")
        random.shuffle(product_list)

        semaphore = asyncio.Semaphore(5)

        async def check_single_product(prod_id: int, prod_name: str) -> None:
            async with semaphore:
                # Polite random delay between 0.5s and 1.5s to avoid bursts
                jitter = round(random.uniform(0.5, 1.5), 2)
                await asyncio.sleep(jitter)

                # Isolated DB session per concurrent task
                async with AsyncSessionLocal() as session:
                    try:
                        logger.info(f"[SCHEDULER] Checking price for product ID {prod_id} - '{prod_name[:30]}'")
                        service = ProductService(session)
                        await service.refresh_product_price(prod_id)
                        await session.commit()
                    except Exception as prod_err:
                        await session.rollback()
                        logger.error(f"[SCHEDULER ERROR] Failed checking product ID {prod_id}: {str(prod_err)}")

        tasks = [check_single_product(p.id, p.name) for p in product_list]
        await asyncio.gather(*tasks)

    except Exception as db_err:
        logger.error(f"[SCHEDULER DATABASE ERROR] {str(db_err)}")
    finally:
        _is_checking = False
        logger.info("[SCHEDULER] Periodic price check completed.")
    return True
