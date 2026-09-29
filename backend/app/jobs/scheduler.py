from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.core.config import settings
from app.core.logging import logger
from app.jobs.price_checker import check_all_products_job

scheduler = AsyncIOScheduler()


def start_scheduler() -> None:
    """
    Initialize and start the background task scheduler.
    """
    if scheduler.running:
        return

    min_sec = max(30, settings.PRICE_CHECK_MIN_INTERVAL_SECONDS)
    max_sec = max(min_sec, settings.PRICE_CHECK_MAX_INTERVAL_SECONDS)
    base_sec = int((min_sec + max_sec) / 2)
    jitter_sec = int((max_sec - min_sec) / 2)

    scheduler.add_job(
        check_all_products_job,
        trigger=IntervalTrigger(seconds=base_sec, jitter=jitter_sec),
        id="check_all_products",
        name="Lazada Periodic Price Checker",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        f"[SCHEDULER] Started background scheduler with randomized interval: {min_sec}s - {max_sec}s (~{min_sec//60}-{max_sec//60} mins, base={base_sec}s, jitter=±{jitter_sec}s)."
    )


def shutdown_scheduler() -> None:
    """
    Stop the scheduler gracefully on application teardown.
    """
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[SCHEDULER] Background scheduler shut down.")
