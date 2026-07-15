"""Usage dashboard endpoint (Phase 10): GET /usage.

Drives the read path a user's dashboard uses: live month-to-date counters plus
the daily summaries the worker rolls up. Seeds both through the same code paths
(metering emit + aggregation) so the endpoint is exercised end to end.
"""

from bson import ObjectId

from app import db
from app.jobs.usage import aggregate_usage
from app.services import metering


async def _auth(client) -> dict:
    body = {"email": "usage@example.com", "password": "password123"}
    await client.post("/auth/register", json=body)
    resp = await client.post("/auth/login", json=body)
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_usage_requires_auth(client):
    assert (await client.get("/usage")).status_code == 401


async def test_usage_returns_month_to_date_and_daily(client):
    headers = await _auth(client)
    me = (await client.get("/auth/me", headers=headers)).json()
    user_id = me["id"]
    user = await db.get_db().users.find_one({"_id": ObjectId(user_id)})
    tenant_id = str(user["tenant_id"])

    # Live counters (month-to-date).
    await metering.bump_counters(
        metering.build_event(tenant_id, user_id, "S1", "gpt-4o-mini", 1000, 500)
    )
    # A raw event aggregated into a daily summary.
    period = metering.period_key()
    event = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "session_id": "S1",
        "model": "gpt-4o-mini",
        "prompt_tokens": 1000,
        "completion_tokens": 500,
        "total_tokens": 1500,
        "cost_usd": 0.00045,
        "ts": f"{period[:4]}-{period[4:]}-01T10:00:00+00:00",
        "aggregated": False,
    }
    await metering.store_event(event)
    await aggregate_usage({})

    resp = await client.get("/usage", headers=headers)
    assert resp.status_code == 200
    body = resp.json()

    assert body["period"] == period
    assert body["month_to_date"]["user"]["total_tokens"] == 1500
    assert body["month_to_date"]["tenant"]["total_tokens"] == 1500
    assert body["month_to_date"]["user"]["cost_usd"] > 0

    assert len(body["daily"]) == 1
    row = body["daily"][0]
    assert row["model"] == "gpt-4o-mini"
    assert row["total_tokens"] == 1500
    assert row["cost_usd"] > 0
