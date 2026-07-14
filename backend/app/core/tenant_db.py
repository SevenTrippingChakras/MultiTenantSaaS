"""Tenant-scoped data access.

The core multi-tenancy discipline: every query must be filtered by tenant_id and
every insert must carry it. Instead of trusting each call site to remember,
`scoped(tenant_id)` returns collection handles that inject tenant_id
automatically, so a forgotten filter is structurally hard (arch B1).

The same handles also enforce soft deletes: every filter carries `deleted_at:
None` (which in Mongo matches null *or* missing), so soft-deleted rows are
invisible to reads and writes alike without any call site remembering to exclude
them. The background purge job removes them for good on the raw `get_db()`.

Only tenant-owned collections go through here (sessions, messages). `users` and
`tenants` are resolved during auth, before a tenant is known, so they stay on the
raw `get_db()`.
"""

from bson import ObjectId
from motor.motor_asyncio import (
    AsyncIOMotorClientSession,
    AsyncIOMotorCollection,
    AsyncIOMotorCursor,
)
from pymongo.results import DeleteResult, InsertOneResult, UpdateResult

from app.db import get_db


class ScopedCollection:
    """Wraps a Mongo collection, merging tenant_id into every filter and insert.

    An optional client session joins each write to a multi-document transaction
    (see `db.transaction`); it is forwarded to every operation as `session=`.
    """

    def __init__(
        self,
        collection: AsyncIOMotorCollection,
        tenant_id: ObjectId,
        session: AsyncIOMotorClientSession | None = None,
    ) -> None:
        self._c = collection
        self._tenant_id = tenant_id
        self._session = session

    def _scope(self, flt: dict | None) -> dict:
        # `deleted_at: None` matches both a null value and a missing field, so
        # live rows (no such field) stay visible and soft-deleted ones drop out.
        return {**(flt or {}), "tenant_id": self._tenant_id, "deleted_at": None}

    def find(self, flt: dict | None = None) -> AsyncIOMotorCursor:
        return self._c.find(self._scope(flt), session=self._session)

    async def find_one(self, flt: dict | None = None) -> dict | None:
        return await self._c.find_one(self._scope(flt), session=self._session)

    async def insert_one(self, doc: dict) -> InsertOneResult:
        return await self._c.insert_one(
            {**doc, "tenant_id": self._tenant_id}, session=self._session
        )

    async def update_one(self, flt: dict, update: dict) -> UpdateResult:
        return await self._c.update_one(self._scope(flt), update, session=self._session)

    async def delete_one(self, flt: dict) -> DeleteResult:
        return await self._c.delete_one(self._scope(flt), session=self._session)

    async def count_documents(self, flt: dict | None = None) -> int:
        return await self._c.count_documents(self._scope(flt), session=self._session)


class TenantScope:
    """Tenant-scoped handles for the collections that carry tenant_id."""

    def __init__(
        self, tenant_id: ObjectId, session: AsyncIOMotorClientSession | None = None
    ) -> None:
        self._tenant_id = tenant_id
        self._session = session

    @property
    def sessions(self) -> ScopedCollection:
        return ScopedCollection(get_db().sessions, self._tenant_id, self._session)

    @property
    def messages(self) -> ScopedCollection:
        return ScopedCollection(get_db().messages, self._tenant_id, self._session)


def scoped(
    tenant_id: ObjectId, session: AsyncIOMotorClientSession | None = None
) -> TenantScope:
    return TenantScope(tenant_id, session)
