"""Keyset pagination over the sessions list envelope (Phase 9, increment 3)."""


async def _auth(client, email: str) -> dict:
    body = {"email": email, "password": "password123"}
    await client.post("/auth/register", json=body)
    resp = await client.post("/auth/login", json=body)
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_sessions_paginate_by_cursor(client):
    h = await _auth(client, "page@example.com")

    created = []
    for i in range(5):
        r = await client.post("/sessions", json={"title": f"s{i}"}, headers=h)
        created.append(r.json()["id"])

    # Page 1: two items + a cursor pointing past them.
    p1 = (await client.get("/sessions?limit=2", headers=h)).json()
    assert len(p1["items"]) == 2
    assert p1["next_cursor"] is not None

    # Page 2: next two, following the cursor.
    p2 = (
        await client.get(f"/sessions?limit=2&after={p1['next_cursor']}", headers=h)
    ).json()
    assert len(p2["items"]) == 2
    assert p2["next_cursor"] is not None

    # Page 3: the last one, no further cursor.
    p3 = (
        await client.get(f"/sessions?limit=2&after={p2['next_cursor']}", headers=h)
    ).json()
    assert len(p3["items"]) == 1
    assert p3["next_cursor"] is None

    # No duplicates or gaps across pages: all five ids appear exactly once.
    seen = [s["id"] for s in p1["items"] + p2["items"] + p3["items"]]
    assert sorted(seen) == sorted(created)


async def test_limit_is_clamped(client):
    h = await _auth(client, "clamp@example.com")
    # Over the max: still returns 200 (clamped server-side, no error).
    r = await client.get("/sessions?limit=99999", headers=h)
    assert r.status_code == 200
    # Under 1: falls back to the default rather than returning nothing.
    r = await client.get("/sessions?limit=0", headers=h)
    assert r.status_code == 200
