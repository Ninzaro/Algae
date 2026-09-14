from datetime import datetime

from alphaforge.models.domain import Signal
from alphaforge.models.enums import SignalSide


class SignalHold:
    """Remember the last acted signal per strategy/symbol so the same bar cannot re-fire."""

    def __init__(self) -> None:
        self._last: dict[tuple[str, str], tuple[str, datetime]] = {}

    def allow(self, signal: Signal, bar_ts: datetime) -> bool:
        """Return True once for a given (strategy, symbol, side, bar)."""
        key = (signal.strategy_id, signal.symbol)
        previous = self._last.get(key)
        if previous is not None:
            prev_side, prev_bar = previous
            if prev_side == signal.side.value and prev_bar == bar_ts:
                return False
        self._last[key] = (signal.side.value, bar_ts)
        return True

    def snapshot(self) -> list[tuple[str, str, str, datetime]]:
        return [
            (strategy_id, symbol, side, bar_ts)
            for (strategy_id, symbol), (side, bar_ts) in self._last.items()
        ]

    def restore(self, rows: list[tuple[str, str, str, datetime]]) -> None:
        self._last = {
            (strategy_id, symbol): (side, bar_ts) for strategy_id, symbol, side, bar_ts in rows
        }

    def last_side(self, strategy_id: str, symbol: str) -> SignalSide | None:
        previous = self._last.get((strategy_id, symbol))
        if previous is None:
            return None
        return SignalSide(previous[0])
