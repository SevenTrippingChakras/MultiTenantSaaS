"""ARQ worker entrypoint — the process that consumes the task queue.

Run separately from the API: `uv run arq app.worker.WorkerSettings`. It shares
Redis with the API (which enqueues via `app/task_queue.py`) and opens its own
Mongo connection on startup. It handles enqueued jobs (`store_usage_event`) and
runs periodic cron jobs (`aggregate_usage`, once a minute) for off-hot-path
metering aggregation (arch A2).
"""

import logging

from arq import cron

from app import db, task_queue
from app.config import settings
from app.core.logging import configure_logging
from app.jobs.usage import aggregate_usage, store_usage_event

configure_logging(settings.log_level)
logger = logging.getLogger("aichat")


async def startup(ctx: dict) -> None:
    await db.connect()
    logger.info("Worker connected to MongoDB (db=%s)", db.get_db().name)


async def shutdown(ctx: dict) -> None:
    await db.close()
    logger.info("Worker MongoDB connection closed")


class WorkerSettings:
    """Discovered by `arq app.worker.WorkerSettings`."""

    functions = [store_usage_event]
    # Roll raw events into daily summaries at the top of every minute.
    cron_jobs = [cron(aggregate_usage, second=0, run_at_startup=False)]
    redis_settings = task_queue.redis_settings()
    on_startup = startup
    on_shutdown = shutdown
