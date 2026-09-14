from typing import Protocol

from alphaforge.models.domain import AccountSnapshot, Bar, Fill, Order, Position
from alphaforge.models.enums import Timeframe


class Broker(Protocol):
    """Broker adapter contract. Strategies must never import this."""

    name: str

    async def submit_order(
        self, order: Order, *, ref_price: float | None = None
    ) -> tuple[Order, Fill | None]:
        """Submit an approved order. May return an immediate fill (paper/market)."""

    async def cancel_order(self, order_id: str) -> Order:
        """Cancel an open order."""

    async def cancel_all(self) -> list[Order]:
        """Cancel every open order."""

    async def get_positions(self) -> list[Position]:
        """Return broker-reported positions."""

    async def get_account(self) -> AccountSnapshot:
        """Return broker-reported account snapshot."""


class MarketData(Protocol):
    """Historical and latest-bar market data contract."""

    name: str

    async def get_bars(
        self,
        symbol: str,
        *,
        timeframe: Timeframe,
        lookback: int,
    ) -> list[Bar]:
        """Return oldest-first OHLCV bars."""

    async def latest_price(self, symbol: str) -> float:
        """Return the most recent trade/close price."""
