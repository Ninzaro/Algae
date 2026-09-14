from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ENV = Path(__file__).resolve().parents[4] / ".env"


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(_REPO_ENV if _REPO_ENV.is_file() else ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "AlphaForge"
    app_env: Literal["development", "test", "production"] = "development"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    trading_mode: Literal["backtest", "paper", "live"] = "paper"
    broker_adapter: Literal["paper", "angelone", "alpaca"] = "paper"
    data_adapter: Literal["yfinance", "angelone"] = "yfinance"
    strategy_symbols: str = "RELIANCE.NS,INFY.NS,HDFCBANK.NS"
    log_level: str = "INFO"

    jwt_secret: SecretStr = SecretStr("change-me-to-a-long-random-string")
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 7
    master_key: SecretStr = SecretStr("change-me-fernet-compatible-or-raw-secret")
    api_key: SecretStr = SecretStr("change-me-internal-service-key")

    database_url: str = "postgresql+asyncpg://alphaforge:alphaforge@localhost:5432/alphaforge"
    redis_url: str = "redis://localhost:6379/0"

    operator_email: str = "operator@localhost"
    operator_password: SecretStr = SecretStr("change-me")

    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_paper: bool = True
    alpaca_base_url: str = "https://paper-api.alpaca.markets"

    angel_api_key: str = ""
    angel_client_code: str = ""
    angel_password: SecretStr = SecretStr("")
    angel_totp_secret: SecretStr = SecretStr("")
    angel_product: str = "DELIVERY"

    polygon_api_key: str = ""

    max_daily_loss_pct: float = Field(default=2.0, ge=0.0)
    max_drawdown_pct: float = Field(default=10.0, ge=0.0)
    max_gross_exposure_pct: float = Field(default=100.0, ge=0.0)
    max_position_pct: float = Field(default=20.0, ge=0.0)
    max_orders_per_day: int = Field(default=50, ge=0)
    kill_switch_enabled: bool = False

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    discord_webhook_url: str = ""

    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    cors_origin_regex: str | None = Field(
        default=r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)(:\d+)?$"
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> list[str]:
        if isinstance(value, str):
            val = value.strip()
            if not val:
                return []
            if val.startswith("[") and val.endswith("]"):
                import json

                try:
                    return json.loads(val)
                except Exception:
                    pass
            return [origin.strip() for origin in val.split(",") if origin.strip()]
        if isinstance(value, (list, tuple, set)):
            return list(value)
        return value

    starting_cash: float = 100_000.0
    target_volatility: float = 0.10
    kelly_fraction: float = 0.25

    @property
    def is_live(self) -> bool:
        return self.trading_mode == "live"

    @property
    def is_paper(self) -> bool:
        return self.trading_mode == "paper"

    def symbol_list(self) -> list[str]:
        return [item.strip().upper() for item in self.strategy_symbols.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()


def reset_settings() -> None:
    """Clear the settings cache (tests only)."""
    get_settings.cache_clear()
