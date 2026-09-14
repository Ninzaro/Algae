from datetime import UTC, datetime, timedelta

from alphaforge.models.domain import Signal
from alphaforge.models.enums import SignalSide
from alphaforge.services.strategy.hold import SignalHold


def test_hold_blocks_same_bar_and_side() -> None:
    hold = SignalHold()
    bar = datetime(2026, 8, 13, tzinfo=UTC)
    signal = Signal(strategy_id="sma-crossover", symbol="QQQ", side=SignalSide.BUY, strength=0.4)
    assert hold.allow(signal, bar)
    assert not hold.allow(signal, bar)


def test_hold_allows_new_bar_or_opposite_side() -> None:
    hold = SignalHold()
    bar = datetime(2026, 8, 13, tzinfo=UTC)
    buy = Signal(strategy_id="sma-crossover", symbol="QQQ", side=SignalSide.BUY, strength=0.4)
    flat = Signal(strategy_id="sma-crossover", symbol="QQQ", side=SignalSide.FLAT, strength=0.0)
    assert hold.allow(buy, bar)
    assert hold.allow(flat, bar)
    assert hold.allow(buy, bar + timedelta(days=1))


def test_hold_restore_roundtrip() -> None:
    hold = SignalHold()
    bar = datetime(2026, 8, 13, tzinfo=UTC)
    signal = Signal(strategy_id="sma-crossover", symbol="SPY", side=SignalSide.BUY, strength=0.2)
    hold.allow(signal, bar)
    other = SignalHold()
    other.restore(hold.snapshot())
    assert not other.allow(signal, bar)
    assert other.last_side("sma-crossover", "SPY") == SignalSide.BUY
