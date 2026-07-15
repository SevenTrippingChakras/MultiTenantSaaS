"""ARQ Redis settings for the metering worker.

The worker (`app/worker.py`) runs the `aggregate_usage` cron and needs ARQ's
`RedisSettings` for its own scheduling bookkeeping. The API no longer enqueues
jobs — usage events are written durably on the request path (see
`app/services/metering.py`), so there is no enqueue pool here anymore.
"""

from arq.connections import RedisSettings

from app.config import settings


def redis_settings() -> RedisSettings:
    """ARQ Redis connection settings, derived from the shared `redis_uri`."""
    return RedisSettings.from_dsn(settings.redis_uri)
