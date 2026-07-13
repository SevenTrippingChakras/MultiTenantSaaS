"""Tests for the auto-injecting tenant-scoped wrapper (Phase 6, increment 2)."""

from bson import ObjectId

from app.core.tenant_db import scoped
from app.db import get_db

T1 = ObjectId()
T2 = ObjectId()


async def test_insert_stamps_tenant_id(client):
    res = await scoped(T1).sessions.insert_one({"title": "hi"})
    raw = await get_db().sessions.find_one({"_id": res.inserted_id})
    assert raw["tenant_id"] == T1


async def test_find_only_returns_own_tenant(client):
    await scoped(T1).sessions.insert_one({"title": "t1"})
    await scoped(T2).sessions.insert_one({"title": "t2"})
    rows = await scoped(T1).sessions.find({}).to_list(length=100)
    assert len(rows) == 1
    assert rows[0]["title"] == "t1" and rows[0]["tenant_id"] == T1


async def test_find_one_cross_tenant_is_none(client):
    res = await scoped(T2).sessions.insert_one({"title": "t2"})
    # T1 asking for T2's document by id sees nothing.
    assert await scoped(T1).sessions.find_one({"_id": res.inserted_id}) is None


async def test_update_and_delete_do_not_cross_tenants(client):
    res = await scoped(T2).sessions.insert_one({"title": "t2"})
    # T1 cannot update or delete T2's document.
    upd = await scoped(T1).sessions.update_one(
        {"_id": res.inserted_id}, {"$set": {"title": "hacked"}}
    )
    assert upd.modified_count == 0
    dele = await scoped(T1).sessions.delete_one({"_id": res.inserted_id})
    assert dele.deleted_count == 0
    # The document is untouched.
    still = await get_db().sessions.find_one({"_id": res.inserted_id})
    assert still["title"] == "t2"
