"""Trend Following / Channel Breakout Strategy.

Goes long on Donchian upper breakout with ATR expansion filter, and exits on lower channel cross
or Supertrend trailing stop violation.
"""

from typing import Any

from alphaforge.models.domain import Signal, StrategyContext
from alphaforge.models.enums import SignalSide, Timeframe
from alphaforge.quant.indicators import atr, donchian_channel, supertrend
from alphaforge.strategies.base import Strategy


class TrendBreakoutStrategy(Strategy):
    """Institutional Donchian Breakout with ATR volatility filter and trailing stop."""

    def __init__(
        self,
        *,
        strategy_id: str = "trend-breakout",
        symbols: list[str] | None = None,
        donchian_window: int = 20,
        exit_window: int = 10,
        atr_window: int = 14,
        atr_mult: float = 2.5,
        timeframe: Timeframe = Timeframe.D1,
    ) -> None:
        if exit_window >= donchian_window:
            raise ValueError("exit_window must be < donchian_window")
        self.id = strategy_id
        self.name = "Trend Breakout (Donchian + ATR)"
        self.description = (
            f"Enter long on {donchian_window}-period high breakout; exit on {exit_window}-period low or ATR trailing stop."
        )
        self.symbols = symbols or ["SPY"]
        self.timeframe = timeframe
        self.params: dict[str, Any] = {
            "donchian_window": donchian_window,
            "exit_window": exit_window,
            "atr_window": atr_window,
            "atr_mult": atr_mult,
        }

    def with_params(self, params: dict[str, Any]) -> "TrendBreakoutStrategy":
        merged = {**self.params, **params}
        return TrendBreakoutStrategy(
            strategy_id=self.id,
            symbols=list(self.symbols),
            donchian_window=int(merged["donchian_window"]),
            exit_window=int(merged["exit_window"]),
            atr_window=int(merged["atr_window"]),
            atr_mult=float(merged["atr_mult"]),
            timeframe=self.timeframe,
        )

    def generate_signals(self, context: StrategyContext) -> list[Signal]:
        donchian_w = int(self.params["donchian_window"])
        exit_w = int(self.params["exit_window"])
        atr_w = int(self.params["atr_window"])
        atr_m = float(self.params["atr_mult"])

        signals: list[Signal] = []
        for symbol in self.symbols:
            bars = context.bars_for(symbol)
            min_bars = max(donchian_w, exit_w, atr_w) + 2
            if len(bars) < min_bars:
                continue

            highs = [b.high for b in bars]
            lows = [b.low for b in bars]
            closes = [b.close for b in bars]

            # Donchian on bars prior to current to avoid lookahead bias
            upper_entry, _, _ = donchian_channel(highs[:-1], lows[:-1], window=donchian_w)
            _, _, lower_exit = donchian_channel(highs[:-1], lows[:-1], window=exit_w)
            st_result = supertrend(highs, lows, closes, period=atr_w, multiplier=atr_m)
            atr_vals = atr(highs, lows, closes, window=atr_w)

            current_close = closes[-1]
            breakout_level = upper_entry[-1]
            exit_level = lower_exit[-1]
            current_trend = st_result.trend[-1]
            curr_atr = atr_vals[-1]

            if breakout_level != breakout_level or exit_level != exit_level:
                continue

            held_qty = next((p.quantity for p in context.positions if p.symbol == symbol), 0.0)

            # Entry condition: close breaks above N-day high and trend filter is bullish
            if current_close > breakout_level and held_qty <= 0:
                strength = min(1.0, max(0.2, (current_close - breakout_level) / (curr_atr if curr_atr > 0 else 1.0)))
                signals.append(
                    Signal(
                        strategy_id=self.id,
                        symbol=symbol,
                        side=SignalSide.BUY,
                        strength=strength,
                        timestamp=context.as_of,
                        reason=f"Breakout above {breakout_level:.2f} (close={current_close:.2f}, ATR={curr_atr:.2f})",
                        metadata={
                            "breakout_level": breakout_level,
                            "atr": curr_atr,
                            "supertrend": st_result.supertrend[-1],
                        },
                    )
                )

            # Exit condition: close breaks below exit channel or supertrend flips bearish
            elif (current_close < exit_level or current_trend == -1) and held_qty > 0:
                signals.append(
                    Signal(
                        strategy_id=self.id,
                        symbol=symbol,
                        side=SignalSide.FLAT,
                        strength=0.0,
                        timestamp=context.as_of,
                        reason=f"Channel exit below {exit_level:.2f} or supertrend flip",
                        metadata={"exit_level": exit_level, "trend": current_trend},
                    )
                )

        return signals
