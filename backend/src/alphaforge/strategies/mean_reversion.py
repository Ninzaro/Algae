from math import sqrt
from typing import Any

from alphaforge.models.domain import Signal, StrategyContext
from alphaforge.models.enums import SignalSide, Timeframe
from alphaforge.strategies.base import Strategy


class MeanReversionStrategy(Strategy):
    """Fade z-score extremes versus a rolling mean; flatten when z-score mean-reverts."""

    def __init__(
        self,
        *,
        strategy_id: str = "mean-reversion",
        symbols: list[str] | None = None,
        lookback: int = 20,
        entry_z: float = 2.0,
        exit_z: float = 0.5,
        timeframe: Timeframe = Timeframe.D1,
    ) -> None:
        self.id = strategy_id
        self.name = "Mean Reversion"
        self.description = f"Buy when z < -{entry_z}; flatten when |z| < {exit_z}."
        self.symbols = symbols or ["SPY"]
        self.timeframe = timeframe
        self.params: dict[str, Any] = {
            "lookback": lookback,
            "entry_z": entry_z,
            "exit_z": exit_z,
        }

    def with_params(self, params: dict[str, Any]) -> "MeanReversionStrategy":
        merged = {**self.params, **params}
        return MeanReversionStrategy(
            strategy_id=self.id,
            symbols=list(self.symbols),
            lookback=int(merged["lookback"]),
            entry_z=float(merged["entry_z"]),
            exit_z=float(merged["exit_z"]),
            timeframe=self.timeframe,
        )

    def generate_signals(self, context: StrategyContext) -> list[Signal]:
        lookback = int(self.params["lookback"])
        entry_z = float(self.params["entry_z"])
        exit_z = float(self.params["exit_z"])
        held = {p.symbol for p in context.positions if p.quantity > 0}
        signals: list[Signal] = []
        for symbol in self.symbols:
            bars = context.bars_for(symbol)
            if len(bars) < lookback:
                continue
            closes = [b.close for b in bars[-lookback:]]
            mean = sum(closes) / lookback
            var = sum((c - mean) ** 2 for c in closes) / lookback
            std = sqrt(var)
            if std <= 0:
                continue
            z = (closes[-1] - mean) / std
            side: SignalSide | None = None
            if z <= -entry_z and symbol not in held:
                side = SignalSide.BUY
            elif symbol in held and (abs(z) <= exit_z or z >= entry_z):
                side = SignalSide.FLAT
            if side is None:
                continue
            strength = max(-1.0, min(1.0, -z / max(entry_z, 1e-9)))
            if side == SignalSide.FLAT:
                strength = 0.0
            signals.append(
                Signal(
                    strategy_id=self.id,
                    symbol=symbol,
                    side=side,
                    strength=strength,
                    timestamp=context.as_of,
                    reason=f"z={z:.2f} mean={mean:.4f}",
                    metadata={
                        "z": z,
                        "mean": mean,
                        "std": std,
                        "bar_ts": bars[-1].timestamp.isoformat(),
                    },
                )
            )
        return signals
