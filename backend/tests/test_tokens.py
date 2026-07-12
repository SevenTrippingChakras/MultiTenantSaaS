from app.core import security

USER_ID = "507f1f77bcf86cd799439011"


def test_access_token_decodes_as_access_only():
    token = security.create_access_token(USER_ID)
    assert security.decode_access_token(token) == USER_ID
    # An access token must not pass as a refresh token.
    assert security.decode_refresh_token(token) is None


def test_refresh_token_decodes_as_refresh_only():
    token = security.create_refresh_token(USER_ID, family_id="fam1", jti="jti1")
    payload = security.decode_refresh_token(token)
    assert payload is not None
    assert payload["sub"] == USER_ID
    assert payload["fid"] == "fam1"
    assert payload["jti"] == "jti1"
    # A refresh token must not pass as an access token.
    assert security.decode_access_token(token) is None


def test_garbage_token_rejected():
    assert security.decode_access_token("not-a-jwt") is None
    assert security.decode_refresh_token("not-a-jwt") is None
