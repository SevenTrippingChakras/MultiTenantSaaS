EMAIL = "bob@example.com"
PASSWORD = "password123"


async def _register_and_login(client):
    await client.post("/auth/register", json={"email": EMAIL, "password": PASSWORD})
    return await client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})


def _csrf_headers(client) -> dict:
    """The header the client must echo back (double-submit CSRF)."""
    return {"x-csrf-token": client.cookies["csrf_token"]}


async def test_login_sets_httponly_refresh_and_csrf_cookies(client):
    resp = await _register_and_login(client)
    assert "refresh_token" in resp.cookies
    assert "csrf_token" in resp.cookies
    # The token is not in the JSON body anymore.
    assert "refresh_token" not in resp.json()
    cookies = resp.headers.get_list("set-cookie")
    refresh_c = next(c for c in cookies if c.startswith("refresh_token=")).lower()
    assert "httponly" in refresh_c and "samesite=strict" in refresh_c


async def test_refresh_returns_a_working_new_pair(client):
    await _register_and_login(client)
    resp = await client.post("/auth/refresh", headers=_csrf_headers(client))
    assert resp.status_code == 200
    new_access = resp.json()["access_token"]
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me.status_code == 200


async def test_refresh_without_csrf_header_forbidden(client):
    await _register_and_login(client)
    resp = await client.post("/auth/refresh")  # cookie sent, but no CSRF header
    assert resp.status_code == 403


async def test_refresh_csrf_mismatch_forbidden(client):
    await _register_and_login(client)
    resp = await client.post("/auth/refresh", headers={"x-csrf-token": "wrong-value"})
    assert resp.status_code == 403


async def test_reuse_of_rotated_token_revokes_family(client):
    login = await _register_and_login(client)
    old_refresh = login.cookies["refresh_token"]

    # First refresh rotates old -> new (client cookie now holds the new one).
    first = await client.post("/auth/refresh", headers=_csrf_headers(client))
    assert first.status_code == 200

    # Replaying the OLD token is reuse -> 401 and revokes the whole family.
    replay = await client.post(
        "/auth/refresh",
        headers={
            "Cookie": f"refresh_token={old_refresh}; csrf_token=tok",
            "x-csrf-token": "tok",
        },
    )
    assert replay.status_code == 401

    # The (previously valid) NEW token is now dead too.
    after = await client.post("/auth/refresh", headers=_csrf_headers(client))
    assert after.status_code == 401


async def test_missing_refresh_cookie_rejected(client):
    # Valid CSRF but no refresh cookie -> 401 (not a CSRF failure).
    resp = await client.post(
        "/auth/refresh",
        headers={"Cookie": "csrf_token=tok", "x-csrf-token": "tok"},
    )
    assert resp.status_code == 401


async def test_garbage_refresh_token_rejected(client):
    resp = await client.post(
        "/auth/refresh",
        headers={
            "Cookie": "refresh_token=not-a-jwt; csrf_token=tok",
            "x-csrf-token": "tok",
        },
    )
    assert resp.status_code == 401


async def test_access_token_rejected_as_refresh(client):
    login = await _register_and_login(client)
    access = login.json()["access_token"]
    resp = await client.post(
        "/auth/refresh",
        headers={
            "Cookie": f"refresh_token={access}; csrf_token=tok",
            "x-csrf-token": "tok",
        },
    )
    assert resp.status_code == 401
