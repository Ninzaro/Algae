from datetime import UTC, datetime

from alphaforge.core.exceptions import DataError
from alphaforge.core.logging import get_logger
from alphaforge.models.domain import Bar
from alphaforge.models.enums import Timeframe

log = get_logger(__name__)

_YF_INTERVAL = {
    Timeframe.M1: "1m",
    Timeframe.M5: "5m",
    Timeframe.M15: "15m",
    Timeframe.H1: "1h",
    Timeframe.D1: "1d",
}

_YF_PERIOD = {
    Timeframe.M1: "7d",
    Timeframe.M5: "60d",
    Timeframe.M15: "60d",
    Timeframe.H1: "730d",
    Timeframe.D1: "5y",
}


class YFinanceMarketData:
    """yfinance-backed market data adapter (research / paper fallback)."""

    name = "yfinance"

    async def get_bars(
        self,
        symbol: str,
        *,
        timeframe: Timeframe,
        lookback: int,
    ) -> list[Bar]:
        try:
            import asyncio

            import yfinance as yf
        except ImportError as exc:
            raise DataError("yfinance is not installed") from exc

        interval = _YF_INTERVAL[timeframe]
        period = _YF_PERIOD[timeframe]

        def _download() -> list[Bar]:
            frame = yf.download(
                symbol,
                period=period,
                interval=interval,
                auto_adjust=True,
                progress=False,
            )
            if frame is None or frame.empty:
                raise DataError(f"No data returned for {symbol}")
            if hasattr(frame.columns, "droplevel") and getattr(frame.columns, "nlevels", 1) > 1:
                frame.columns = frame.columns.droplevel(1)
            bars: list[Bar] = []
            for ts, row in frame.tail(lookback).iterrows():
                timestamp = ts.to_pydatetime()
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=UTC)
                bars.append(
                    Bar(
                        symbol=symbol,
                        timestamp=timestamp,
                        open=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                        volume=float(row.get("Volume", 0.0) or 0.0),
                        timeframe=timeframe,
                    )
                )
            return bars

        try:
            return await asyncio.to_thread(_download)
        except DataError:
            raise
        except Exception as exc:
            raise DataError(f"Failed to fetch {symbol}: {exc}") from exc

    async def latest_price(self, symbol: str) -> float:
        bars = await self.get_bars(symbol, timeframe=Timeframe.D1, lookback=1)
        if not bars:
            raise DataError(f"No latest price for {symbol}")
        return bars[-1].close


class SyntheticMarketData:
    """Deterministic in-memory bars for tests and offline paper loops."""

    name = "synthetic"

    def __init__(self, series: dict[str, list[Bar]] | None = None) -> None:
        self._series = series or {}

    def set_bars(self, symbol: str, bars: list[Bar]) -> None:
        self._series[symbol] = list(bars)

    async def get_bars(
        self,
        symbol: str,
        *,
        timeframe: Timeframe,
        lookback: int,
    ) -> list[Bar]:
        bars = [b for b in self._series.get(symbol, []) if b.timeframe == timeframe]
        if not bars:
            bars = list(self._series.get(symbol, []))
        return bars[-lookback:]

    async def latest_price(self, symbol: str) -> float:
        bars = self._series.get(symbol, [])
        if not bars:
            raise DataError(f"No synthetic bars for {symbol}")
        return bars[-1].close


def make_synthetic_trend(
    symbol: str,
    *,
    start: float = 100.0,
    n: int = 80,
    drift: float = 0.4,
    timeframe: Timeframe = Timeframe.D1,
) -> list[Bar]:
    """Build a simple trending series for tests and the demo loop."""
    from datetime import timedelta

    bars: list[Bar] = []
    price = start
    now = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    for i in range(n):
        price = max(1.0, price + drift)
        high = price * 1.01
        low = price * 0.99
        open_px = price - drift * 0.5
        bars.append(
            Bar(
                symbol=symbol,
                timestamp=now - timedelta(days=n - i),
                open=open_px,
                high=high,
                low=low,
                close=price,
                volume=1_000_000,
                timeframe=timeframe,
            )
        )
    return bars
