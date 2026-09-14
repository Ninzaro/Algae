from fastapi import APIRouter, HTTPException, status

from alphaforge.api.deps import SettingsDep
from alphaforge.core.exceptions import AuthenticationError
from alphaforge.core.security import create_token, decode_token, verify_password
from alphaforge.models.api import LoginRequest, RefreshRequest, TokenResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, settings: SettingsDep) -> TokenResponse:
    if body.email.lower() != settings.operator_email.lower():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    expected = settings.operator_password.get_secret_value()
    if body.password != expected and not _looks_hashed_and_matches(body.password, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(
        access_token=create_token(body.email.lower(), settings, "access"),
        refresh_token=create_token(body.email.lower(), settings, "refresh"),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, settings: SettingsDep) -> TokenResponse:
    try:
        payload = decode_token(body.refresh_token, settings)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message) from exc
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token required"
        )
    subject = str(payload.get("sub", ""))
    return TokenResponse(
        access_token=create_token(subject, settings, "access"),
        refresh_token=create_token(subject, settings, "refresh"),
    )


def _looks_hashed_and_matches(password: str, stored: str) -> bool:
    if not stored.startswith("$argon2"):
        return False
    return verify_password(password, stored)
