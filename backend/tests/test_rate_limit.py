"""Locks the rate-limit contract: /auth/login returns a 429 in our error
envelope once the per-IP limit is exceeded, and the limit is read from config."""

import pytest

from app.config import settings
from app.core.rate_limit import limiter

LOGIN = {"email": "nobody@example.com", "password": "wrongpass"}


@pytest.fixture
def rate_limited():
    """Enable the limiter for one test, then turn it back off."""
    limiter.reset()
    limiter.enabled = True
    yield
    limiter.enabled = False
    limiter.reset()


async def test_login_rate_limited(client, rate_limited):
    # Default auth_rate_limit is 10/minute; the 11th attempt is rejected.
    statuses = []
    for _ in range(11):
        resp = await client.post("/auth/login", json=LOGIN)
        statuses.append(resp.status_code)
    assert statuses[:10] == [401] * 10
    assert statuses[10] == 429

    body = (await client.post("/auth/login", json=LOGIN)).json()
    assert body["error"]["code"] == "rate_limited"


async def test_limit_is_config_driven(client, rate_limited, monkeypatch):
    """The limit comes from settings at request time: lowering it takes effect
    without touching code or restarting (proves the callable, not a frozen literal)."""
    monkeypatch.setattr(settings, "auth_rate_limit", "3/minute")

    statuses = []
    for _ in range(4):
        resp = await client.post("/auth/login", json=LOGIN)
        statuses.append(resp.status_code)
    assert statuses[:3] == [401] * 3
    assert statuses[3] == 429
