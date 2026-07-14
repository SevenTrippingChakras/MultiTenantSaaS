"""Soft delete hides rows but keeps them; purge reclaims them (Phase 9, inc. 4)."""

from app import db
from app.jobs.purge import purge_soft_deleted


async def _auth(client, email: str) -> dict:
    body = {"email": email, "password": "password123"}
    await client.post("/auth/register", json=body)
    resp = await client.post("/auth/login", json=body)
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_delete_is_soft_then_purged(client):
    h = await _auth(client, "soft@example.com")
    sid = (await client.post("/sessions", json={"title": "x"}, headers=h)).json()["id"]

    await client.delete(f"/sessions/{sid}", headers=h)

    # Hidden from the API...
    listed = (await client.get("/sessions", headers=h)).json()
    assert all(s["id"] != sid for s in listed["items"])
    assert (await client.get(f"/sessions/{sid}/messages", headers=h)).status_code == 404

    # ...but the row still exists with a deleted_at stamp (recoverable).
    from bson import ObjectId

    raw = await db.get_db().sessions.find_one({"_id": ObjectId(sid)})
    assert raw is not None and raw["deleted_at"] is not None

    # Purge with a zero-day window reclaims it for good.
    counts = await purge_soft_deleted(retention_days=0)
    assert counts["sessions"] >= 1
    assert await db.get_db().sessions.find_one({"_id": ObjectId(sid)}) is None


async def test_purge_leaves_recent_soft_deletes(client):
    h = await _auth(client, "recent@example.com")
    sid = (await client.post("/sessions", json={"title": "y"}, headers=h)).json()["id"]
    await client.delete(f"/sessions/{sid}", headers=h)

    # Default retention (30 days) must not reap a just-now delete.
    counts = await purge_soft_deleted()
    assert counts["sessions"] == 0

    from bson import ObjectId

    assert await db.get_db().sessions.find_one({"_id": ObjectId(sid)}) is not None
