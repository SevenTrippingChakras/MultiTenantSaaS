"""Tenant-scoped data access.

The core multi-tenancy discipline: every query must be filtered by tenant_id and
every insert must carry it. Instead of trusting each call site to remember,
`scoped(tenant_id)` returns collection handles that inject tenant_id
automatically, so a forgotten filter is structurally hard (arch B1).

Only tenant-owned collections go through here (sessions, messages). `users` and
`tenants` are resolved during auth, before a tenant is known, so they stay on the
raw `get_db()`.
"""

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorCursor
from pymongo.results import DeleteResult, InsertOneResult, UpdateResult

from app.db import get_db


class ScopedCollection:
    """Wraps a Mongo collection, merging tenant_id into every filter and insert."""

    def __init__(self, collection: AsyncIOMotorCollection, tenant_id: ObjectId) -> None:
        self._c = collection
        self._tenant_id = tenant_id

    def _scope(self, flt: dict | None) -> dict:
        return {**(flt or {}), "tenant_id": self._tenant_id}

    def find(self, flt: dict | None = None) -> AsyncIOMotorCursor:
        return self._c.find(self._scope(flt))

    async def find_one(self, flt: dict | None = None) -> dict | None:
        return await self._c.find_one(self._scope(flt))

    async def insert_one(self, doc: dict) -> InsertOneResult:
        return await self._c.insert_one({**doc, "tenant_id": self._tenant_id})

    async def update_one(self, flt: dict, update: dict) -> UpdateResult:
        return await self._c.update_one(self._scope(flt), update)

    async def delete_one(self, flt: dict) -> DeleteResult:
        return await self._c.delete_one(self._scope(flt))


class TenantScope:
    """Tenant-scoped handles for the collections that carry tenant_id."""

    def __init__(self, tenant_id: ObjectId) -> None:
        self._tenant_id = tenant_id

    @property
    def sessions(self) -> ScopedCollection:
        return ScopedCollection(get_db().sessions, self._tenant_id)

    @property
    def messages(self) -> ScopedCollection:
        return ScopedCollection(get_db().messages, self._tenant_id)


def scoped(tenant_id: ObjectId) -> TenantScope:
    return TenantScope(tenant_id)
