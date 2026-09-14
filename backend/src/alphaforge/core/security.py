from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from jose import JWTError, jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from alphaforge.core.config import Settings
from alphaforge.core.exceptions import AuthenticationError

_password_hash = PasswordHash((Argon2Hasher(),))
_FERNET_SALT = b"alphaforge.v1.master"


def hash_password(password: str) -> str:
    """Hash a password with Argon2."""
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against an Argon2 hash."""
    return _password_hash.verify(password, password_hash)


def _fernet_from_master(master_key: str) -> Fernet:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_FERNET_SALT,
        iterations=480_000,
    )
    key = kdf.derive(master_key.encode("utf-8"))
    import base64

    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_secret(plaintext: str, settings: Settings) -> str:
    """Encrypt a secret at rest using a key derived from MASTER_KEY."""
    fernet = _fernet_from_master(settings.master_key.get_secret_value())
    return fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str, settings: Settings) -> str:
    """Decrypt a secret previously encrypted with encrypt_secret."""
    fernet = _fernet_from_master(settings.master_key.get_secret_value())
    try:
        return fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise AuthenticationError("Unable to decrypt secret") from exc


def create_token(
    subject: str,
    settings: Settings,
    token_type: Literal["access", "refresh"] = "access",
    extra: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT access or refresh token."""
    now = datetime.now(UTC)
    if token_type == "access":
        ttl = timedelta(minutes=settings.jwt_access_ttl_minutes)
    else:
        ttl = timedelta(days=settings.jwt_refresh_ttl_days)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
        "jti": str(uuid4()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm="HS256")


def decode_token(token: str, settings: Settings) -> dict[str, Any]:
    """Decode and validate a JWT. Raises AuthenticationError on failure."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=["HS256"],
        )
    except JWTError as exc:
        raise AuthenticationError("Invalid or expired token") from exc
    return payload
