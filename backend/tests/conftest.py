import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app import db
from app.config import settings
from app.main import app

TEST_DB = "aichat_test"
_COLLECTIONS = ("users", "sessions", "messages")


@pytest_asyncio.fixture
async def client():
    """An AsyncClient bound to the app, with a clean test DB connected."""
    settings.mongodb_db = TEST_DB
    # Connect inside the test so Motor binds to the event loop pytest-asyncio
    # creates for it (avoids "attached to a different loop" errors).
    await db.connect()
    for name in _COLLECTIONS:
        await db.get_db()[name].delete_many({})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    await db.close()
