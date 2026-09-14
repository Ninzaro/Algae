from datetime import UTC, datetime, timedelta

from tests.conftest import make_bars

from alphaforge.models.api import WalkForwardRequest
from alphaforge.models.enums import Timeframe
from alphaforge.services.backtest.engine import BacktestEngine
from alphaforge.services.backtest.walkforward import WalkForwardEngine, _fold_indices
from alphaforge.services.strategy.registry import StrategyRegistry
from alphaforge.strategies.sma_crossover import SmaCrossoverStrategy


def test_fold_indices_rolling() -> None:
    folds = _fold_indices(100, train=40, test=10, step=10, anchored=False)
    assert len(folds) == 6
    assert list(folds[0][0]) == list(range(0, 40))
    assert list(folds[0][1]) == list(range(40, 50))
    assert list(folds[1][0]) == list(range(10, 50))


def test_fold_indices_anchored() -> None:
    folds = _fold_indices(80, train=30, test=10, step=10, anchored=True)
    assert next(iter(folds[0][0])) == 0
    assert next(iter(folds[1][0])) == 0
    assert folds[1][0][-1] > folds[0][0][-1]


def test_walkforward_produces_oos_curve() -> None:
    registry = StrategyRegistry()
    strategy = SmaCrossoverStrategy(symbols=["SPY"], fast=5, slow=15)
    registry.register(strategy, enabled=True)
    engine = WalkForwardEngine(BacktestEngine(registry))
    closes = [100.0 + ((i % 17) - 8) * 1.5 for i in range(120)]
    bars = make_bars("SPY", closes)
    request = WalkForwardRequest(
        strategy_id="sma-crossover",
        symbols=["SPY"],
        start=datetime.now(UTC) - timedelta(days=200),
        end=datetime.now(UTC) + timedelta(days=1),
        timeframe=Timeframe.D1,
        train_bars=40,
        test_bars=15,
        step_bars=15,
    )
    result = engine.run(request, strategy, {"SPY": bars})
    assert result.strategy_id == "sma-crossover"
    assert len(result.folds) >= 2
    assert result.folds[0].params["fast"] < result.folds[0].params["slow"]
    assert len(result.oos_equity_curve) > 0
    assert result.ending_equity > 0
