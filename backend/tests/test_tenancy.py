"""Tests for the tenant boundary (Phase 6)."""

from app.repositories import tenant_repo, user_repo


async def test_registration_creates_a_tenant(client):
    await client.post(
        "/auth/register", json={"email": "a@example.com", "password": "password123"}
    )
    user = await user_repo.find_by_email("a@example.com")
    assert user is not None
    assert user["tenant_id"] is not None
    # The tenant entity actually exists.
    tenant = await tenant_repo.find_by_id(user["tenant_id"])
    assert tenant is not None and tenant["name"] == "a@example.com"


async def test_each_registration_gets_its_own_tenant(client):
    await client.post(
        "/auth/register", json={"email": "a@example.com", "password": "password123"}
    )
    await client.post(
        "/auth/register", json={"email": "b@example.com", "password": "password123"}
    )
    a = await user_repo.find_by_email("a@example.com")
    b = await user_repo.find_by_email("b@example.com")
    assert a["tenant_id"] != b["tenant_id"]
