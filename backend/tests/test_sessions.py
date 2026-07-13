"""Happy-path session flow through the tenant-scoped stack (Phase 6, increment 3)."""


async def _auth(client, email: str) -> dict:
    body = {"email": email, "password": "password123"}
    await client.post("/auth/register", json=body)
    resp = await client.post("/auth/login", json=body)
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_create_list_and_read_session(client):
    h = await _auth(client, "s@example.com")

    created = await client.post("/sessions", json={"title": "hi"}, headers=h)
    assert created.status_code == 201
    sid = created.json()["id"]

    listed = await client.get("/sessions", headers=h)
    assert listed.status_code == 200
    assert any(s["id"] == sid for s in listed.json())

    msgs = await client.get(f"/sessions/{sid}/messages", headers=h)
    assert msgs.status_code == 200
    assert msgs.json() == []

    deleted = await client.delete(f"/sessions/{sid}", headers=h)
    assert deleted.status_code == 204
    after = await client.get("/sessions", headers=h)
    assert all(s["id"] != sid for s in after.json())
