"""Statistical Arbitrage / Pairs Trading Strategy.

Tracks the cointegrated spread or price ratio between two correlated assets, generating
mean-reversion signals when the spread Z-score exceeds entry thresholds and reverting at equilibrium.
"""

from math import log, sqrt
from typing import Any

from alphaforge.models.domain import Signal, StrategyContext
from alphaforge.models.enums import SignalSide, Timeframe
from alphaforge.strategies.base import Strategy


class PairsTradingStrategy(Strategy):
    """Statistical Arbitrage / Cointegrated Pairs Mean Reversion."""

    def __init__(
        self,
        *,
        strategy_id: str = "stat-arb-pairs",
        symbols: list[str] | None = None,
        lookback: int = 30,
        entry_z: float = 2.0,
        exit_z: float = 0.5,
        stop_z: float = 3.5,
        timeframe: Timeframe = Timeframe.D1,
    ) -> None:
        pair_symbols = symbols or ["SPY", "QQQ"]
        if len(pair_symbols) < 2:
            raise ValueError("Pairs trading requires at least 2 symbols")

        self.id = strategy_id
        self.name = f"Pairs Arbitrage ({pair_symbols[0]} / {pair_symbols[1]})"
        self.description = (
            f"Trade spread between {pair_symbols[0]} and {pair_symbols[1]} at |Z| > {entry_z:.1f}, exit at |Z| < {exit_z:.1f}."
        )
        self.symbols = pair_symbols[:2]
        self.timeframe = timeframe
        self.params: dict[str, Any] = {
            "lookback": lookback,
            "entry_z": entry_z,
            "exit_z": exit_z,
            "stop_z": stop_z,
        }

    def with_params(self, params: dict[str, Any]) -> "PairsTradingStrategy":
        merged = {**self.params, **params}
        return PairsTradingStrategy(
            strategy_id=self.id,
            symbols=list(self.symbols),
            lookback=int(merged["lookback"]),
            entry_z=float(merged["entry_z"]),
            exit_z=float(merged["exit_z"]),
            stop_z=float(merged["stop_z"]),
            timeframe=self.timeframe,
        )

    def generate_signals(self, context: StrategyContext) -> list[Signal]:
        sym_a, sym_b = self.symbols[0], self.symbols[1]
        bars_a = context.bars_for(sym_a)
        bars_b = context.bars_for(sym_b)

        lookback = int(self.params["lookback"])
        entry_z = float(self.params["entry_z"])
        exit_z = float(self.params["exit_z"])
        stop_z = float(self.params["stop_z"])

        min_bars = lookback + 2
        if len(bars_a) < min_bars or len(bars_b) < min_bars:
            return []

        # Align timestamps
        ts_a = {b.timestamp: b.close for b in bars_a}
        ts_b = {b.timestamp: b.close for b in bars_b}
        common_ts = sorted(set(ts_a.keys()) & set(ts_b.keys()))

        if len(common_ts) < min_bars:
            return []

        # Compute log price spread
        spreads: list[float] = []
        for ts in common_ts:
            p_a = ts_a[ts]
            p_b = ts_b[ts]
            if p_a <= 0 or p_b <= 0:
                continue
            spreads.append(log(p_a) - log(p_b))

        if len(spreads) < lookback:
            return []

        window_spreads = spreads[-lookback:]
        mean_spread = sum(window_spreads) / lookback
        var = sum((s - mean_spread) ** 2 for s in window_spreads) / (lookback - 1)
        std_spread = sqrt(max(var, 0.0))

        held_a = next((p.quantity for p in context.positions if p.symbol == sym_a), 0.0)
        held_b = next((p.quantity for p in context.positions if p.symbol == sym_b), 0.0)

        if std_spread < 1e-9:
            early_signals: list[Signal] = []
            if held_a > 0:
                early_signals.append(
                    Signal(
                        strategy_id=self.id,
                        symbol=sym_a,
                        side=SignalSide.FLAT,
                        strength=0.0,
                        timestamp=context.as_of,
                        reason="Pairs Mean Reversion (Zero Variance Equilibrium)",
                    )
                )
            if held_b > 0:
                early_signals.append(
                    Signal(
                        strategy_id=self.id,
                        symbol=sym_b,
                        side=SignalSide.FLAT,
                        strength=0.0,
                        timestamp=context.as_of,
                        reason="Pairs Mean Reversion (Zero Variance Equilibrium)",
                    )
                )
            return early_signals

        current_spread = spreads[-1]
        current_z = (current_spread - mean_spread) / std_spread

        signals: list[Signal] = []

        # Condition 1: Spread too low (Asset A is cheap vs Asset B) -> BUY A, FLAT B
        if current_z <= -entry_z and current_z > -stop_z:
            if held_a <= 0:
                strength = min(1.0, max(0.3, abs(current_z) / entry_z))
                signals.append(
                    Signal(
                        strategy_id=self.id,
                        symbol=sym_a,
                        side=SignalSide.BUY,
                        strength=strength,
                        timestamp=context.as_of,
                        reason=f"Pairs Long {sym_a} (Z={current_z:.2f} <= -{entry_z:.1f})",
                        metadata={"z_score": current_z, "spread": current_spread},
                    )
                )
            if held_b > 0:
                signals.append(
                    Signal(
                        strategy_id=self.id,
                        symbol=sym_b,
                        side=SignalSide.FLAT,
                        strength=0.0,
                        timestamp=context.as_of,
                        reason=f"Pairs Rotate from {sym_b} to {sym_a}",
                    )
                )

        # Condition 2: Spread too high (Asset B is cheap vs Asset A) -> BUY B, FLAT A
        elif current_z >= entry_z and current_z < stop_z:
            if held_b <= 0:
                strength = min(1.0, max(0.3, abs(current_z) / entry_z))
                signals.append(
                    Signal(
                        strategy_id=self.id,
                        symbol=sym_b,
                        side=SignalSide.BUY,
                        strength=strength,
                        timestamp=context.as_of,
                        reason=f"Pairs Long {sym_b} (Z={current_z:.2f} >= {entry_z:.1f})",
                        metadata={"z_score": current_z, "spread": current_spread},
                    )
                )
            if held_a > 0:
                signals.append(
                    Signal(
                        strategy_id=self.id,
                        symbol=sym_a,
                        side=SignalSide.FLAT,
                        strength=0.0,
                        timestamp=context.as_of,
                        reason=f"Pairs Rotate from {sym_a} to {sym_b}",
                    )
                )

        # Condition 3: Reversion to mean (|Z| < exit_z) or stop loss (|Z| >= stop_z) -> Exit both
        elif abs(current_z) <= exit_z or abs(current_z) >= stop_z:
            reason = f"Pairs Mean Reversion (Z={current_z:.2f})" if abs(current_z) <= exit_z else f"Pairs Stop Loss (Z={current_z:.2f})"
            if held_a > 0:
                signals.append(
                    Signal(
                        strategy_id=self.id,
                        symbol=sym_a,
                        side=SignalSide.FLAT,
                        strength=0.0,
                        timestamp=context.as_of,
                        reason=reason,
                        metadata={"z_score": current_z},
                    )
                )
            if held_b > 0:
                signals.append(
                    Signal(
                        strategy_id=self.id,
                        symbol=sym_b,
                        side=SignalSide.FLAT,
                        strength=0.0,
                        timestamp=context.as_of,
                        reason=reason,
                        metadata={"z_score": current_z},
                    )
                )

        return signals
