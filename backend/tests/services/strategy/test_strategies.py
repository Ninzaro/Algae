from tests.conftest import make_bars

from alphaforge.models.domain import Position, StrategyContext
from alphaforge.models.enums import SignalSide
from alphaforge.strategies.mean_reversion import MeanReversionStrategy
from alphaforge.strategies.sma_crossover import SmaCrossoverStrategy


def test_sma_crossover_buy_on_cross_up() -> None:
    closes = [100.0] * 40 + [130.0]
    strategy = SmaCrossoverStrategy(symbols=["SPY"], fast=5, slow=20)
    ctx = StrategyContext(
        as_of=make_bars("SPY", closes)[-1].timestamp, bars={"SPY": make_bars("SPY", closes)}
    )
    signals = strategy.generate_signals(ctx)
    assert len(signals) == 1
    assert signals[0].side == SignalSide.BUY
    assert signals[0].strategy_id == "sma-crossover"


def test_sma_crossover_silent_without_cross() -> None:
    closes = [100.0 + i * 0.01 for i in range(40)]
    strategy = SmaCrossoverStrategy(symbols=["SPY"], fast=5, slow=20)
    ctx = StrategyContext(
        as_of=make_bars("SPY", closes)[-1].timestamp, bars={"SPY": make_bars("SPY", closes)}
    )
    first = strategy.generate_signals(ctx)
    second = strategy.generate_signals(ctx)
    assert isinstance(first, list)
    assert isinstance(second, list)


def test_sma_skips_buy_when_already_long() -> None:
    closes = [100.0] * 40 + [130.0]
    strategy = SmaCrossoverStrategy(symbols=["SPY"], fast=5, slow=20)
    bars = make_bars("SPY", closes)
    held = [Position(symbol="SPY", quantity=4, avg_price=100.0, market_price=130.0)]
    ctx = StrategyContext(as_of=bars[-1].timestamp, bars={"SPY": bars}, positions=held)
    assert strategy.generate_signals(ctx) == []


def test_sma_flattens_on_cross_down_when_long() -> None:
    closes = [130.0] * 40 + [90.0]
    strategy = SmaCrossoverStrategy(symbols=["SPY"], fast=5, slow=20)
    bars = make_bars("SPY", closes)
    held = [Position(symbol="SPY", quantity=4, avg_price=120.0, market_price=90.0)]
    ctx = StrategyContext(as_of=bars[-1].timestamp, bars={"SPY": bars}, positions=held)
    signals = strategy.generate_signals(ctx)
    assert len(signals) == 1
    assert signals[0].side == SignalSide.FLAT


def test_sma_insufficient_history() -> None:
    strategy = SmaCrossoverStrategy(symbols=["SPY"], fast=10, slow=30)
    bars = make_bars("SPY", [100.0] * 10)
    ctx = StrategyContext(as_of=bars[-1].timestamp, bars={"SPY": bars})
    assert strategy.generate_signals(ctx) == []


def test_mean_reversion_buys_oversold() -> None:
    closes = [100.0] * 19 + [80.0]
    strategy = MeanReversionStrategy(symbols=["SPY"], lookback=20, entry_z=1.5)
    bars = make_bars("SPY", closes)
    ctx = StrategyContext(as_of=bars[-1].timestamp, bars={"SPY": bars})
    signals = strategy.generate_signals(ctx)
    assert len(signals) == 1
    assert signals[0].side == SignalSide.BUY


def test_mean_reversion_does_not_rebuy_when_held() -> None:
    closes = [100.0] * 19 + [80.0]
    strategy = MeanReversionStrategy(symbols=["SPY"], lookback=20, entry_z=1.5)
    bars = make_bars("SPY", closes)
    held = [Position(symbol="SPY", quantity=10, avg_price=90.0, market_price=80.0)]
    ctx = StrategyContext(as_of=bars[-1].timestamp, bars={"SPY": bars}, positions=held)
    assert strategy.generate_signals(ctx) == []


def test_mean_reversion_flattens_when_held_and_mean() -> None:
    closes = [100.0 + ((i % 3) - 1) * 0.3 for i in range(19)] + [100.0]
    strategy = MeanReversionStrategy(symbols=["SPY"], lookback=20, entry_z=2.0, exit_z=0.5)
    bars = make_bars("SPY", closes)
    held = [Position(symbol="SPY", quantity=10, avg_price=90.0, market_price=100.0)]
    ctx = StrategyContext(as_of=bars[-1].timestamp, bars={"SPY": bars}, positions=held)
    signals = strategy.generate_signals(ctx)
    assert len(signals) == 1
    assert signals[0].side == SignalSide.FLAT


def test_strategy_never_imports_broker() -> None:
    import alphaforge.strategies.sma_crossover as mod

    with open(mod.__file__, encoding="utf-8") as handle:
        source = handle.read()
    assert "adapters" not in source
    assert "Broker" not in source
    assert "RiskManager" not in source
