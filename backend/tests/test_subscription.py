"""Tenant subscription state (Phase 11): plan on the tenant, get/set."""

from app import plans
from app.repositories import tenant_repo, user_repo


async def test_new_tenant_starts_on_free_plan(client):
    await client.post(
        "/auth/register", json={"email": "a@example.com", "password": "password123"}
    )
    user = await user_repo.find_by_email("a@example.com")
    assert await tenant_repo.get_plan(user["tenant_id"]) == plans.FREE


async def test_set_plan_moves_the_tenant(client):
    await client.post(
        "/auth/register", json={"email": "a@example.com", "password": "password123"}
    )
    user = await user_repo.find_by_email("a@example.com")
    await tenant_repo.set_plan(user["tenant_id"], plans.PRO)
    assert await tenant_repo.get_plan(user["tenant_id"]) == plans.PRO
