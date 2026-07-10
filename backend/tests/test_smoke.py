from app import db


async def test_health(client):
    """The app responds and routing works through the AsyncClient."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_test_db_connected_and_clean(client):
    """The fixture connects to the test DB and starts each test empty."""
    assert db.get_db().name == "aichat_test"
    assert await db.get_db().users.count_documents({}) == 0
