from datetime import UTC, datetime, timedelta

from tests.conftest import make_bars

from alphaforge.models.api import BacktestRequest
from alphaforge.models.enums import Timeframe
from alphaforge.services.backtest.engine import BacktestEngine
from alphaforge.services.strategy.registry import StrategyRegistry
from alphaforge.strategies.sma_crossover import SmaCrossoverStrategy


def test_backtest_runs_without_error() -> None:
    registry = StrategyRegistry()
    registry.register(SmaCrossoverStrategy(symbols=["SPY"], fast=5, slow=15), enabled=True)
    engine = BacktestEngine(registry)
    closes = [100.0] * 20 + [100.0 + i for i in range(25)]
    bars = make_bars("SPY", closes)
    request = BacktestRequest(
        strategy_id="sma-crossover",
        symbols=["SPY"],
        start=datetime.now(UTC) - timedelta(days=80),
        end=datetime.now(UTC) + timedelta(days=1),
        timeframe=Timeframe.D1,
        starting_cash=100_000.0,
    )
    result = engine.run(request, {"SPY": bars})
    assert result.strategy_id == "sma-crossover"
    assert result.ending_equity > 0
    assert len(result.equity_curve) > 0
