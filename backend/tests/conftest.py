import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app import db, redis_client
from app.config import settings
from app.core.rate_limit import limiter
from app.main import app

TEST_DB = "aichat_test"
_COLLECTIONS = ("users", "sessions", "messages", "tenants")


@pytest_asyncio.fixture
async def client():
    """An AsyncClient bound to the app, with a clean test DB connected."""
    settings.mongodb_db = TEST_DB
    # Off by default so shared in-memory counters don't make tests flaky;
    # the rate-limit test opts back in explicitly.
    limiter.enabled = False
    # Connect inside the test so Motor binds to the event loop pytest-asyncio
    # creates for it (avoids "attached to a different loop" errors).
    await db.connect()
    await redis_client.connect()
    for name in _COLLECTIONS:
        await db.get_db()[name].delete_many({})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    await redis_client.close()
    await db.close()
