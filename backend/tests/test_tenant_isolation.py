"""Cross-tenant isolation (Phase 6, increment 4).

Two registrations = two tenants. Tenant B must not be able to see, read, delete,
or chat into tenant A's session. Every cross-tenant access returns 404 (we don't
leak that another tenant's session exists).
"""


async def _auth(client, email: str) -> dict:
    body = {"email": email, "password": "password123"}
    await client.post("/auth/register", json=body)
    resp = await client.post("/auth/login", json=body)
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_tenant_cannot_touch_another_tenants_session(client):
    a = await _auth(client, "alice@example.com")
    b = await _auth(client, "bob@example.com")

    # Alice creates a session.
    created = await client.post("/sessions", json={"title": "alice-secret"}, headers=a)
    sid = created.json()["id"]

    # Bob's session list does not include it.
    b_list = await client.get("/sessions", headers=b)
    assert all(s["id"] != sid for s in b_list.json()["items"])

    # Bob cannot read its messages, delete it, or chat into it — all 404.
    assert (await client.get(f"/sessions/{sid}/messages", headers=b)).status_code == 404
    assert (await client.delete(f"/sessions/{sid}", headers=b)).status_code == 404
    chat = await client.post(f"/chat/{sid}", json={"content": "hi"}, headers=b)
    assert chat.status_code == 404

    # And Alice's session is untouched — she can still read it.
    assert (await client.get(f"/sessions/{sid}/messages", headers=a)).status_code == 200
