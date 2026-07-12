"""Locks the liveness/readiness contract: /health is a dependency-free 'process
is up' check; /ready pings Mongo and Redis and reports each store's status."""


async def test_health_is_ok(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_ready_reflects_both_stores(client):
    resp = await client.get("/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["checks"] == {"mongo": "ok", "redis": "ok"}
