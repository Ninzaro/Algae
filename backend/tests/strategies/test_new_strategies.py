"""Unit tests for institutional strategy templates."""

from datetime import UTC, datetime, timedelta

from alphaforge.models.domain import Bar, Position, StrategyContext
from alphaforge.models.enums import AssetClass, SignalSide, Timeframe
from alphaforge.strategies.statistical_arbitrage import PairsTradingStrategy
from alphaforge.strategies.trend_breakout import TrendBreakoutStrategy
from alphaforge.strategies.volatility_breakout import VolatilityBreakoutStrategy


def _make_bars(symbol: str, closes: list[float]) -> list[Bar]:
    base = datetime(2025, 1, 1, tzinfo=UTC)
    bars = []
    for i, c in enumerate(closes):
        bars.append(
            Bar(
                symbol=symbol,
                timestamp=base + timedelta(days=i),
                open=c * 0.99,
                high=c * 1.02,
                low=c * 0.98,
                close=c,
                volume=1000.0,
                timeframe=Timeframe.D1,
                asset_class=AssetClass.EQUITY,
            )
        )
    return bars


def test_trend_breakout_strategy() -> None:
    strat = TrendBreakoutStrategy(symbols=["SPY"], donchian_window=10, exit_window=5, atr_window=5)
    # 15 flat days, then strong breakout
    prices = [100.0] * 15 + [101.0, 103.0, 108.0]
    bars = _make_bars("SPY", prices)
    ctx = StrategyContext(as_of=bars[-1].timestamp, bars={"SPY": bars}, positions=[])

    signals = strat.generate_signals(ctx)
    assert len(signals) >= 1
    assert signals[0].side == SignalSide.BUY
    assert signals[0].symbol == "SPY"

    # Test with_params
    fitted = strat.with_params({"donchian_window": 15, "exit_window": 7})
    assert fitted.params["donchian_window"] == 15
    assert fitted.params["exit_window"] == 7


def test_volatility_breakout_strategy() -> None:
    strat = VolatilityBreakoutStrategy(
        symbols=["SPY"], bb_window=15, bb_std=1.5, squeeze_threshold=0.20, rsi_window=10
    )
    # Long tight consolidation (squeeze) followed by expansion
    prices = [100.0] * 42 + [103.0, 106.0, 110.0]
    bars = _make_bars("SPY", prices)
    ctx = StrategyContext(as_of=bars[-1].timestamp, bars={"SPY": bars}, positions=[])

    signals = strat.generate_signals(ctx)
    assert len(signals) >= 1
    assert signals[0].side == SignalSide.BUY

    fitted = strat.with_params({"bb_window": 20})
    assert fitted.params["bb_window"] == 20


def test_pairs_trading_strategy() -> None:
    strat = PairsTradingStrategy(
        symbols=["SPY", "QQQ"], lookback=15, entry_z=1.5, exit_z=0.5, stop_z=5.0
    )
    # SPY and QQQ move together with slight variation, then SPY diverges downward
    spy_prices = [100.0 + (i % 3) * 0.2 for i in range(25)] + [94.0]
    qqq_prices = [100.0 + (i % 3) * 0.2 for i in range(25)] + [100.0]

    bars_spy = _make_bars("SPY", spy_prices)
    bars_qqq = _make_bars("QQQ", qqq_prices)

    ctx = StrategyContext(
        as_of=bars_spy[-1].timestamp,
        bars={"SPY": bars_spy, "QQQ": bars_qqq},
        positions=[],
    )

    signals = strat.generate_signals(ctx)
    assert len(signals) >= 1
    # SPY is undervalued -> Signal to BUY SPY
    buy_signals = [s for s in signals if s.side == SignalSide.BUY]
    assert any(s.symbol == "SPY" for s in buy_signals)

    # Test exit when positions held and spread converges
    pos_spy = Position(
        symbol="SPY", quantity=10.0, avg_price=94.0, market_price=100.0, market_value=1000.0
    )
    spy_prices_conv = [100.0] * 25
    qqq_prices_conv = [100.0] * 25
    ctx_conv = StrategyContext(
        as_of=bars_spy[-1].timestamp,
        bars={"SPY": _make_bars("SPY", spy_prices_conv), "QQQ": _make_bars("QQQ", qqq_prices_conv)},
        positions=[pos_spy],
    )
    exit_signals = strat.generate_signals(ctx_conv)
    flat_signals = [s for s in exit_signals if s.side == SignalSide.FLAT]
    assert any(s.symbol == "SPY" for s in flat_signals)
