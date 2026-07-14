"""Backward (scroll-up) keyset pagination over a session's messages (Phase 9).

Messages open newest-first and page older via `?before=<id>`. History is built
through the chat endpoint with a faked LLM stream so the test runs offline; each
chat turn persists a user message and an assistant message.
"""

from app import llm
from tests.test_chat_llm import _fake_stream_factory


async def _auth(client, email: str) -> dict:
    body = {"email": email, "password": "password123"}
    await client.post("/auth/register", json=body)
    resp = await client.post("/auth/login", json=body)
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_messages_paginate_backward_by_cursor(client, monkeypatch):
    monkeypatch.setattr(llm, "stream", _fake_stream_factory({}))
    h = await _auth(client, "msgpage@example.com")
    sid = (await client.post("/sessions", json={"title": "t"}, headers=h)).json()["id"]

    # Three chat turns -> six messages (user + assistant each), chronological.
    for i in range(3):
        await client.post(f"/chat/{sid}", json={"content": f"m{i}"}, headers=h)
    full = (await client.get(f"/sessions/{sid}/messages", headers=h)).json()
    assert len(full["items"]) == 6
    assert full["next_cursor"] is None
    ordered_ids = [m["id"] for m in full["items"]]

    # Page 1: newest two, in chronological order, with a cursor to older ones.
    p1 = (await client.get(f"/sessions/{sid}/messages?limit=2", headers=h)).json()
    assert [m["id"] for m in p1["items"]] == ordered_ids[4:]
    assert p1["next_cursor"] is not None

    # Page 2: the next-older two, following `before`.
    p2 = (
        await client.get(
            f"/sessions/{sid}/messages?limit=2&before={p1['next_cursor']}",
            headers=h,
        )
    ).json()
    assert [m["id"] for m in p2["items"]] == ordered_ids[2:4]
    assert p2["next_cursor"] is not None

    # Page 3: the oldest two, no further cursor.
    p3 = (
        await client.get(
            f"/sessions/{sid}/messages?limit=2&before={p2['next_cursor']}",
            headers=h,
        )
    ).json()
    assert [m["id"] for m in p3["items"]] == ordered_ids[:2]
    assert p3["next_cursor"] is None
