"""Chat LLM path (Phase 7): prompt shaping + usage accounting.

The OpenAI call is replaced with a fake stream so these run offline. We assert
that the prompt starts with the system prefix and that the token usage the LLM
reports is persisted onto the assistant message.
"""

from app import db, llm
from tests.conftest import TEST_DB

FAKE_USAGE = {"prompt_tokens": 11, "completion_tokens": 2, "total_tokens": 13}


def _fake_stream_factory(captured: dict):
    async def fake_stream(messages, usage_out=None):
        captured["messages"] = messages
        for tok in ["Hello", " world"]:
            yield tok
        if usage_out is not None:
            usage_out.update(FAKE_USAGE)

    return fake_stream


async def _auth(client) -> dict:
    body = {"email": "chat@example.com", "password": "password123"}
    await client.post("/auth/register", json=body)
    resp = await client.post("/auth/login", json=body)
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_prompt_is_shaped_and_usage_persisted(client, monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(llm, "stream", _fake_stream_factory(captured))

    headers = await _auth(client)
    sid = (await client.post("/sessions", json={"title": "t"}, headers=headers)).json()[
        "id"
    ]

    resp = await client.post(f"/chat/{sid}", json={"content": "hi"}, headers=headers)
    assert resp.status_code == 200
    assert '"delta": "Hello"' in resp.text
    assert '"delta": " world"' in resp.text
    assert '"done": true' in resp.text

    # Prompt shaping: the stable system prefix leads the prompt.
    prompt = captured["messages"]
    assert prompt[0]["role"] == "system"
    assert prompt[-1] == {"role": "user", "content": "hi"}

    # Usage accounting: the reported token counts land in the assistant message.
    settings_db = db.get_db()
    assert settings_db.name == TEST_DB
    assistant = await settings_db.messages.find_one({"role": "assistant"})
    assert assistant["content"] == "Hello world"
    assert assistant["metadata"]["usage"] == FAKE_USAGE
