"""Plan feature gating (Phase 11): the export feature is plan-locked."""

from app import plans
from app.repositories import tenant_repo, user_repo


async def _auth(client, email: str) -> dict:
    body = {"email": email, "password": "password123"}
    await client.post("/auth/register", json=body)
    resp = await client.post("/auth/login", json=body)
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_free_plan_cannot_export(client):
    h = await _auth(client, "f@example.com")
    sid = (await client.post("/sessions", json={"title": "x"}, headers=h)).json()["id"]

    resp = await client.get(f"/sessions/{sid}/export", headers=h)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "feature_not_available"


async def test_pro_plan_can_export(client):
    h = await _auth(client, "p@example.com")
    user = await user_repo.find_by_email("p@example.com")
    await tenant_repo.set_plan(user["tenant_id"], plans.PRO)
    sid = (await client.post("/sessions", json={"title": "x"}, headers=h)).json()["id"]

    resp = await client.get(f"/sessions/{sid}/export", headers=h)
    assert resp.status_code == 200
    body = resp.json()
    assert body["session"]["id"] == sid
    assert body["messages"] == []
