from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


def start_scheduler() -> None:
    if scheduler.running:
        return

    from app.tasks.content_fetcher import run_content_fetcher_job
    from app.tasks.publisher import run_publisher_job

    scheduler.add_job(
        run_content_fetcher_job,
        trigger=CronTrigger(minute=0),
        id="content_fetcher_job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        run_publisher_job,
        trigger=CronTrigger(minute="*/5"),
        id="publisher_job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()
    logger.info("Scheduler started with automation jobs.")


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down.")
