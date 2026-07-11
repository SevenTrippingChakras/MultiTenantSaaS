"""The error contract: every failure renders as {"error": {"code", "message"}}."""

EMAIL = "bob@example.com"
PASSWORD = "password123"


async def _token(client) -> str:
    await client.post("/auth/register", json={"email": EMAIL, "password": PASSWORD})
    login = await client.post(
        "/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    return login.json()["access_token"]


def _assert_envelope(resp, status_code: int, code: str):
    assert resp.status_code == status_code
    body = resp.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == code
    assert body["error"]["message"]


async def test_duplicate_email_envelope(client):
    body = {"email": EMAIL, "password": PASSWORD}
    await client.post("/auth/register", json=body)
    dup = await client.post("/auth/register", json=body)
    _assert_envelope(dup, 409, "email_already_registered")


async def test_wrong_password_envelope(client):
    await client.post("/auth/register", json={"email": EMAIL, "password": PASSWORD})
    bad = await client.post("/auth/login", json={"email": EMAIL, "password": "nope"})
    _assert_envelope(bad, 401, "invalid_credentials")


async def test_missing_token_envelope(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401
    assert "error" in resp.json()


async def test_validation_error_envelope(client):
    # Bad email + missing password -> one detail entry per bad field.
    resp = await client.post("/auth/register", json={"email": "not-an-email"})
    _assert_envelope(resp, 422, "validation_error")
    fields = {d["field"] for d in resp.json()["error"]["details"]}
    assert fields == {"email", "password"}
    assert all(d["message"] for d in resp.json()["error"]["details"])


async def test_session_not_found_envelope(client):
    token = await _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.get(
        "/sessions/000000000000000000000000/messages", headers=headers
    )
    _assert_envelope(resp, 404, "session_not_found")
