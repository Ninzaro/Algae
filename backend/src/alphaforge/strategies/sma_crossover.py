from typing import Any

from alphaforge.models.domain import Signal, StrategyContext
from alphaforge.models.enums import SignalSide, Timeframe
from alphaforge.strategies.base import Strategy


class SmaCrossoverStrategy(Strategy):
    """Long when fast SMA crosses above slow SMA; flatten on the opposite cross."""

    def __init__(
        self,
        *,
        strategy_id: str = "sma-crossover",
        symbols: list[str] | None = None,
        fast: int = 10,
        slow: int = 30,
        timeframe: Timeframe = Timeframe.D1,
    ) -> None:
        if fast >= slow:
            raise ValueError("fast window must be < slow window")
        self.id = strategy_id
        self.name = "SMA Crossover"
        self.description = f"Buy when SMA({fast}) crosses above SMA({slow}); flatten on cross down."
        self.symbols = symbols or ["SPY"]
        self.timeframe = timeframe
        self.params: dict[str, Any] = {"fast": fast, "slow": slow}

    def with_params(self, params: dict[str, Any]) -> "SmaCrossoverStrategy":
        merged = {**self.params, **params}
        return SmaCrossoverStrategy(
            strategy_id=self.id,
            symbols=list(self.symbols),
            fast=int(merged["fast"]),
            slow=int(merged["slow"]),
            timeframe=self.timeframe,
        )

    def generate_signals(self, context: StrategyContext) -> list[Signal]:
        fast = int(self.params["fast"])
        slow = int(self.params["slow"])
        signals: list[Signal] = []
        for symbol in self.symbols:
            bars = context.bars_for(symbol)
            if len(bars) < slow + 1:
                continue
            closes = [b.close for b in bars]
            prev_fast = _sma(closes[-(fast + 1) : -1], fast)
            prev_slow = _sma(closes[-(slow + 1) : -1], slow)
            last_fast = _sma(closes[-fast:], fast)
            last_slow = _sma(closes[-slow:], slow)
            if prev_fast is None or prev_slow is None or last_fast is None or last_slow is None:
                continue
            crossed_up = prev_fast <= prev_slow and last_fast > last_slow
            crossed_down = prev_fast >= prev_slow and last_fast < last_slow
            if not crossed_up and not crossed_down:
                continue
            held_qty = next((p.quantity for p in context.positions if p.symbol == symbol), 0.0)
            if crossed_up and held_qty > 0:
                continue
            if crossed_down and held_qty <= 0:
                continue
            side = SignalSide.BUY if crossed_up else SignalSide.FLAT
            strength = min(1.0, abs(last_fast - last_slow) / last_slow) if last_slow else 0.5
            if side == SignalSide.FLAT:
                strength = 0.0
            bar_ts = bars[-1].timestamp
            signals.append(
                Signal(
                    strategy_id=self.id,
                    symbol=symbol,
                    side=side,
                    strength=strength,
                    timestamp=context.as_of,
                    reason=f"SMA{fast}={last_fast:.4f} SMA{slow}={last_slow:.4f}",
                    metadata={"fast": last_fast, "slow": last_slow, "bar_ts": bar_ts.isoformat()},
                )
            )
        return signals


def _sma(values: list[float], window: int) -> float | None:
    if len(values) < window or window <= 0:
        return None
    return sum(values[-window:]) / window
