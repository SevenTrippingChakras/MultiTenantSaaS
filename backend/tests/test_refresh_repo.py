import uuid

from app.repositories import refresh_repo


async def test_set_and_get_active_jti(client):
    user, fam = _ids()
    await refresh_repo.set_active_jti(user, fam, "jti1")
    assert await refresh_repo.get_active_jti(fam) == "jti1"
    await refresh_repo.revoke_family(user, fam)


async def test_rotation_overwrites_active_jti(client):
    user, fam = _ids()
    await refresh_repo.set_active_jti(user, fam, "jti1")
    await refresh_repo.set_active_jti(user, fam, "jti2")
    assert await refresh_repo.get_active_jti(fam) == "jti2"
    await refresh_repo.revoke_family(user, fam)


async def test_revoke_family_clears_it(client):
    user, fam = _ids()
    await refresh_repo.set_active_jti(user, fam, "jti1")
    await refresh_repo.revoke_family(user, fam)
    assert await refresh_repo.get_active_jti(fam) is None


async def test_revoke_all_clears_every_family(client):
    user = f"user-{uuid.uuid4()}"
    fam1, fam2 = f"fam-{uuid.uuid4()}", f"fam-{uuid.uuid4()}"
    await refresh_repo.set_active_jti(user, fam1, "a")
    await refresh_repo.set_active_jti(user, fam2, "b")
    await refresh_repo.revoke_all(user)
    assert await refresh_repo.get_active_jti(fam1) is None
    assert await refresh_repo.get_active_jti(fam2) is None


def _ids() -> tuple[str, str]:
    return f"user-{uuid.uuid4()}", f"fam-{uuid.uuid4()}"
