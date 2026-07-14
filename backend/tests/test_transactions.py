"""Multi-document transactions commit together or roll back together (Phase 9)."""

import pytest
from bson import ObjectId

from app import db
from app.repositories import message_repo, session_repo


async def test_transaction_commits_paired_writes(client):
    tenant_id = ObjectId()
    session = await session_repo.insert(tenant_id, ObjectId(), "t")
    sid = session["_id"]

    async with db.transaction() as txn:
        await message_repo.insert(tenant_id, sid, "user", "hi", txn=txn)
        await session_repo.set_title(tenant_id, sid, "renamed", txn=txn)

    assert await message_repo.count_by_session(tenant_id, sid) == 1
    assert (await session_repo.find_by_id(tenant_id, str(sid)))["title"] == "renamed"


async def test_transaction_rolls_back_on_error(client):
    tenant_id = ObjectId()
    session = await session_repo.insert(tenant_id, ObjectId(), "t")
    sid = session["_id"]

    with pytest.raises(RuntimeError):
        async with db.transaction() as txn:
            await message_repo.insert(tenant_id, sid, "user", "hi", txn=txn)
            await session_repo.set_title(tenant_id, sid, "renamed", txn=txn)
            raise RuntimeError("boom mid-transaction")

    # Neither write survived the abort.
    assert await message_repo.count_by_session(tenant_id, sid) == 0
    assert (await session_repo.find_by_id(tenant_id, str(sid)))["title"] == "t"
