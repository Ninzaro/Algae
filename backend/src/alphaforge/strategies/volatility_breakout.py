"""Volatility Breakout Strategy (Bollinger Squeeze + Momentum Expansion).

Detects periods of volatility compression (Bollinger Squeeze) followed by explosive directional
expansion with MACD and RSI momentum confirmation.
"""

from typing import Any

from alphaforge.models.domain import Signal, StrategyContext
from alphaforge.models.enums import SignalSide, Timeframe
from alphaforge.quant.indicators import bollinger_bands, macd, rsi
from alphaforge.strategies.base import Strategy


class VolatilityBreakoutStrategy(Strategy):
    """Bollinger Band Squeeze Breakout with Momentum Confirmation."""

    def __init__(
        self,
        *,
        strategy_id: str = "volatility-breakout",
        symbols: list[str] | None = None,
        bb_window: int = 20,
        bb_std: float = 2.0,
        squeeze_threshold: float = 0.08,
        rsi_window: int = 14,
        timeframe: Timeframe = Timeframe.D1,
    ) -> None:
        self.id = strategy_id
        self.name = "Volatility Squeeze Breakout"
        self.description = (
            f"Enter on Bollinger({bb_window}, {bb_std}) expansion from squeeze (<{squeeze_threshold:.2f}) with MACD/RSI momentum."
        )
        self.symbols = symbols or ["SPY"]
        self.timeframe = timeframe
        self.params: dict[str, Any] = {
            "bb_window": bb_window,
            "bb_std": bb_std,
            "squeeze_threshold": squeeze_threshold,
            "rsi_window": rsi_window,
        }

    def with_params(self, params: dict[str, Any]) -> "VolatilityBreakoutStrategy":
        merged = {**self.params, **params}
        return VolatilityBreakoutStrategy(
            strategy_id=self.id,
            symbols=list(self.symbols),
            bb_window=int(merged["bb_window"]),
            bb_std=float(merged["bb_std"]),
            squeeze_threshold=float(merged["squeeze_threshold"]),
            rsi_window=int(merged["rsi_window"]),
            timeframe=self.timeframe,
        )

    def generate_signals(self, context: StrategyContext) -> list[Signal]:
        bb_w = int(self.params["bb_window"])
        bb_std = float(self.params["bb_std"])
        sq_thresh = float(self.params["squeeze_threshold"])
        rsi_w = int(self.params["rsi_window"])

        signals: list[Signal] = []
        for symbol in self.symbols:
            bars = context.bars_for(symbol)
            min_bars = max(bb_w, rsi_w, 35) + 1
            if len(bars) < min_bars:
                continue

            closes = [b.close for b in bars]
            bb = bollinger_bands(closes, window=bb_w, num_std=bb_std)
            macd_res = macd(closes, fast=12, slow=26, signal_period=9)
            rsi_vals = rsi(closes, window=rsi_w)

            # Check recent bandwidth for squeeze in past 5 bars
            recent_bw = [b for b in bb.bandwidth[-6:-1] if b == b]
            had_squeeze = any(bw < sq_thresh for bw in recent_bw) if recent_bw else False

            curr_close = closes[-1]
            curr_upper = bb.upper[-1]
            curr_mid = bb.middle[-1]
            curr_hist = macd_res.histogram[-1]
            curr_rsi = rsi_vals[-1]

            if curr_upper != curr_upper or curr_mid != curr_mid:
                continue

            held_qty = next((p.quantity for p in context.positions if p.symbol == symbol), 0.0)

            # Breakout: close above upper band after squeeze with positive momentum
            if (curr_close >= curr_upper or had_squeeze) and curr_close > curr_mid:
                if curr_hist > 0 and curr_rsi >= 50.0 and held_qty <= 0:
                    strength = min(1.0, max(0.3, (curr_close - curr_mid) / (curr_upper - curr_mid if curr_upper != curr_mid else 1.0)))
                    signals.append(
                        Signal(
                            strategy_id=self.id,
                            symbol=symbol,
                            side=SignalSide.BUY,
                            strength=strength,
                            timestamp=context.as_of,
                            reason=f"Vol Breakout (Close={curr_close:.2f} > Mid={curr_mid:.2f}, RSI={curr_rsi:.1f})",
                            metadata={
                                "bandwidth": bb.bandwidth[-1],
                                "macd_hist": curr_hist,
                                "rsi": curr_rsi,
                            },
                        )
                    )

            # Exit: close crosses below middle band (20 SMA)
            elif curr_close < curr_mid and held_qty > 0:
                signals.append(
                    Signal(
                        strategy_id=self.id,
                        symbol=symbol,
                        side=SignalSide.FLAT,
                        strength=0.0,
                        timestamp=context.as_of,
                        reason=f"Exit below Middle Band SMA({bb_w})={curr_mid:.2f}",
                        metadata={"middle_band": curr_mid},
                    )
                )

        return signals
