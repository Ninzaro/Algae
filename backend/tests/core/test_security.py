import pytest

from alphaforge.core.config import Settings
from alphaforge.core.exceptions import AuthenticationError
from alphaforge.core.security import (
    create_token,
    decode_token,
    decrypt_secret,
    encrypt_secret,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("s3cret")
    assert verify_password("s3cret", hashed)
    assert not verify_password("wrong", hashed)


def test_encrypt_roundtrip(settings: Settings) -> None:
    token = encrypt_secret("alpaca-secret", settings)
    assert token != "alpaca-secret"
    assert decrypt_secret(token, settings) == "alpaca-secret"


def test_jwt_roundtrip(settings: Settings) -> None:
    token = create_token("op@test.local", settings, "access")
    payload = decode_token(token, settings)
    assert payload["sub"] == "op@test.local"
    assert payload["type"] == "access"


def test_bad_jwt_raises(settings: Settings) -> None:
    with pytest.raises(AuthenticationError):
        decode_token("not-a-token", settings)
