"""ARQ worker entrypoint — the process that runs periodic metering jobs.

Run separately from the API: `uv run arq app.worker.WorkerSettings`. It opens its
own Mongo connection on startup and runs `aggregate_usage` once a minute to roll
durable raw `usage_events` into `usage_daily` summaries off the hot path (arch
A2). Raw events are written on the request path now, so the worker no longer
consumes enqueued jobs — it only shares Redis for ARQ's cron bookkeeping.
"""

import logging

from arq import cron

from app import db, task_queue
from app.config import settings
from app.core.logging import configure_logging
from app.jobs.usage import aggregate_usage

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

    # No enqueued jobs: usage events are written durably by the API.
    functions: list = []
    # Roll raw events into daily summaries at the top of every minute.
    cron_jobs = [cron(aggregate_usage, second=0, run_at_startup=False)]
    redis_settings = task_queue.redis_settings()
    on_startup = startup
    on_shutdown = shutdown
