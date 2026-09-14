from typing import Any

import httpx

from alphaforge.core.config import Settings
from alphaforge.core.logging import get_logger

log = get_logger(__name__)


class AlertService:
    """Fire-and-forget Telegram / Discord webhooks for risk events."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def send(self, message: str) -> None:
        await self._telegram(message)
        await self._discord(message)

    async def _telegram(self, message: str) -> None:
        token = self._settings.telegram_bot_token
        chat = self._settings.telegram_chat_id
        if not token or not chat:
            return
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(url, json={"chat_id": chat, "text": message})
        except Exception:
            log.exception("alerts.telegram_failed")

    async def _discord(self, message: str) -> None:
        hook = self._settings.discord_webhook_url
        if not hook:
            return
        payload: dict[str, Any] = {"content": message}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(hook, json=payload)
        except Exception:
            log.exception("alerts.discord_failed")
