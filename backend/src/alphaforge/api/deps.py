from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from alphaforge.core.config import Settings
from alphaforge.core.exceptions import AuthenticationError
from alphaforge.core.security import decode_token
from alphaforge.services.runtime import TradingRuntime

_bearer = HTTPBearer(auto_error=False)
_runtime: TradingRuntime | None = None
_settings: Settings | None = None


def bind_runtime(runtime: TradingRuntime, settings: Settings) -> None:
    global _runtime, _settings
    _runtime = runtime
    _settings = settings


def get_runtime() -> TradingRuntime:
    if _runtime is None:
        raise RuntimeError("TradingRuntime is not bound")
    return _runtime


def get_settings_dep() -> Settings:
    if _settings is None:
        raise RuntimeError("Settings are not bound")
    return _settings


def get_current_subject(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings_dep)],
    x_api_key: Annotated[str | None, Header()] = None,
) -> str:
    """Authenticate via JWT bearer or scoped internal API key."""
    expected_key = settings.api_key.get_secret_value()
    if x_api_key and x_api_key == expected_key:
        return "service"
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_token(creds.credentials, settings)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message) from exc
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token required"
        )
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject"
        )
    return subject


RuntimeDep = Annotated[TradingRuntime, Depends(get_runtime)]
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
SubjectDep = Annotated[str, Depends(get_current_subject)]
