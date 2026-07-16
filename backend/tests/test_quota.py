"""Quota enforcement (Phase 11): plan allowance blocks the hot path."""

from app import plans
from app.repositories import tenant_repo, user_repo
from app.services import metering, quota_service


async def _auth(client, email: str) -> dict:
    body = {"email": email, "password": "password123"}
    await client.post("/auth/register", json=body)
    resp = await client.post("/auth/login", json=body)
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _spend_tokens(user: dict, tokens: int) -> None:
    """Fold usage into the month-to-date Redis counters (as metering does)."""
    await metering.bump_counters(
        {
            "tenant_id": str(user["tenant_id"]),
            "user_id": str(user["_id"]),
            "total_tokens": tokens,
            "cost_usd": 0.0,
        }
    )


async def test_over_quota_blocks_chat(client):
    h = await _auth(client, "q@example.com")
    user = await user_repo.find_by_email("q@example.com")
    sid = (await client.post("/sessions", json={"title": "x"}, headers=h)).json()["id"]

    # Push the Free tenant past its monthly allowance.
    await _spend_tokens(user, plans.get_plan(plans.FREE).monthly_token_limit + 1)

    resp = await client.post(f"/chat/{sid}", json={"content": "hi"}, headers=h)
    assert resp.status_code == 402
    assert resp.json()["error"]["code"] == "quota_exceeded"


async def test_unlimited_plan_never_blocks(client):
    await _auth(client, "e@example.com")
    user = await user_repo.find_by_email("e@example.com")
    await tenant_repo.set_plan(user["tenant_id"], plans.ENTERPRISE)
    await _spend_tokens(user, 10_000_000)

    # check() must not raise for an unlimited plan, even far past any number.
    await quota_service.check(user["tenant_id"])


async def test_status_reports_remaining(client):
    await _auth(client, "s@example.com")
    user = await user_repo.find_by_email("s@example.com")
    await _spend_tokens(user, 25_000)

    free_limit = plans.get_plan(plans.FREE).monthly_token_limit
    s = await quota_service.status(user["tenant_id"])
    assert s["plan"] == plans.FREE
    assert s["used_tokens"] == 25_000
    assert s["remaining_tokens"] == free_limit - 25_000


async def test_usage_endpoint_includes_quota(client):
    h = await _auth(client, "u@example.com")
    resp = await client.get("/usage", headers=h)
    assert resp.status_code == 200
    quota = resp.json()["quota"]
    assert quota["plan"] == plans.FREE
    assert quota["remaining_tokens"] == plans.get_plan(plans.FREE).monthly_token_limit


async def test_plans_catalog_is_public(client):
    resp = await client.get("/plans")
    assert resp.status_code == 200
    names = {p["name"] for p in resp.json()["plans"]}
    assert names == {plans.FREE, plans.PRO, plans.ENTERPRISE}
