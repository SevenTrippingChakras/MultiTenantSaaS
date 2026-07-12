EMAIL = "carol@example.com"
PASSWORD = "password123"


async def _register(client):
    await client.post("/auth/register", json={"email": EMAIL, "password": PASSWORD})


async def _login(client):
    return await client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})


def _csrf_headers(client) -> dict:
    return {"x-csrf-token": client.cookies["csrf_token"]}


async def test_logout_revokes_the_session(client):
    await _register(client)
    login = await _login(client)
    refresh_cookie = login.cookies["refresh_token"]

    out = await client.post("/auth/logout", headers=_csrf_headers(client))
    assert out.status_code == 204

    # The refresh token is revoked server-side (replay it explicitly, with CSRF).
    resp = await client.post(
        "/auth/refresh",
        headers={
            "Cookie": f"refresh_token={refresh_cookie}; csrf_token=tok",
            "x-csrf-token": "tok",
        },
    )
    assert resp.status_code == 401


async def test_logout_without_csrf_forbidden(client):
    await _register(client)
    await _login(client)
    resp = await client.post("/auth/logout")  # no CSRF header
    assert resp.status_code == 403


async def test_logout_all_revokes_every_session(client):
    await _register(client)
    first = await _login(client)
    first_refresh = first.cookies["refresh_token"]
    first_access = first.json()["access_token"]
    second = await _login(client)
    second_refresh = second.cookies["refresh_token"]

    # logout-all is bearer-authed, so no CSRF header is required.
    out = await client.post(
        "/auth/logout-all",
        headers={"Authorization": f"Bearer {first_access}"},
    )
    assert out.status_code == 204

    for refresh_cookie in (first_refresh, second_refresh):
        resp = await client.post(
            "/auth/refresh",
            headers={
                "Cookie": f"refresh_token={refresh_cookie}; csrf_token=tok",
                "x-csrf-token": "tok",
            },
        )
        assert resp.status_code == 401


async def test_logout_all_requires_auth(client):
    resp = await client.post("/auth/logout-all")
    assert resp.status_code == 401
