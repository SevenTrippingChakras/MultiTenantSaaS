EMAIL = "alice@example.com"
PASSWORD = "password123"


async def test_register_login_me_flow(client):
    """The happy path: a new user can register, log in, and read /me."""
    register = await client.post(
        "/auth/register", json={"email": EMAIL, "password": PASSWORD}
    )
    assert register.status_code == 201
    user = register.json()
    assert user["email"] == EMAIL
    assert "id" in user and "password" not in user and "password_hash" not in user

    login = await client.post(
        "/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    assert token

    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == EMAIL
    assert me.json()["id"] == user["id"]


async def test_register_duplicate_email_conflicts(client):
    """Registering the same email twice returns 409."""
    body = {"email": EMAIL, "password": PASSWORD}
    assert (await client.post("/auth/register", json=body)).status_code == 201
    dup = await client.post("/auth/register", json=body)
    assert dup.status_code == 409


async def test_login_wrong_password_unauthorized(client):
    """A wrong password returns 401, not a token."""
    await client.post("/auth/register", json={"email": EMAIL, "password": PASSWORD})
    bad = await client.post(
        "/auth/login", json={"email": EMAIL, "password": "wrong-password"}
    )
    assert bad.status_code == 401


async def test_me_without_token_rejected(client):
    """/me requires a bearer token."""
    resp = await client.get("/auth/me")
    assert resp.status_code == 401
