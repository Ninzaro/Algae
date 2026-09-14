"""Unit tests for PortfolioBlendService and Multi-Strategy Allocation."""

from datetime import UTC, datetime, timedelta

import pytest

from alphaforge.adapters.yfinance_data import SyntheticMarketData, make_synthetic_trend
from alphaforge.models.api import PortfolioBlendRequest, StrategyAllocation
from alphaforge.services.backtest.engine import BacktestEngine
from alphaforge.services.data.service import MarketDataService
from alphaforge.services.portfolio.allocator import PortfolioBlendService
from alphaforge.services.strategy.registry import StrategyRegistry
from alphaforge.strategies.sma_crossover import SmaCrossoverStrategy
from alphaforge.strategies.trend_breakout import TrendBreakoutStrategy


@pytest.mark.asyncio
async def test_portfolio_blend_risk_parity() -> None:
    # Setup 100 bars of synthetic data
    bars_rel = make_synthetic_trend("RELIANCE.NS", start=100.0, n=120, drift=0.4)
    bars_tcs = make_synthetic_trend("TCS.NS", start=200.0, n=120, drift=0.2)

    market_data = SyntheticMarketData({"RELIANCE.NS": bars_rel, "TCS.NS": bars_tcs})
    data_service = MarketDataService(market_data)

    registry = StrategyRegistry()
    registry.register(SmaCrossoverStrategy(fast=5, slow=15))
    registry.register(TrendBreakoutStrategy(donchian_window=20))

    backtest_engine = BacktestEngine(registry)
    allocator = PortfolioBlendService(data_service, registry, backtest_engine)

    now = datetime.now(UTC)
    req = PortfolioBlendRequest(
        allocations=[
            StrategyAllocation(strategy_id="sma-crossover", weight=0.5),
            StrategyAllocation(strategy_id="trend-breakout", weight=0.5),
        ],
        symbols=["RELIANCE.NS", "TCS.NS"],
        start=now - timedelta(days=90),
        end=now,
        starting_cash=100_000.0,
        method="risk_parity",
    )

    resp = await allocator.blend(req)

    assert resp.method == "risk_parity"
    assert resp.starting_cash == 100_000.0
    assert len(resp.strategy_profiles) == 2
    assert len(resp.blended_equity_curve) > 0
    assert "sma-crossover" in resp.correlation_matrix
    assert "trend-breakout" in resp.correlation_matrix
    assert resp.correlation_matrix["sma-crossover"]["sma-crossover"] == 1.0
    assert resp.diversification_ratio >= 0.0


@pytest.mark.asyncio
async def test_portfolio_blend_equal_weight() -> None:
    bars = make_synthetic_trend("SPY", start=100.0, n=100, drift=0.3)
    market_data = SyntheticMarketData({"SPY": bars})
    data_service = MarketDataService(market_data)

    registry = StrategyRegistry()
    registry.register(SmaCrossoverStrategy(fast=5, slow=15))

    backtest_engine = BacktestEngine(registry)
    allocator = PortfolioBlendService(data_service, registry, backtest_engine)

    now = datetime.now(UTC)
    req = PortfolioBlendRequest(
        allocations=[
            StrategyAllocation(strategy_id="sma-crossover", weight=1.0),
        ],
        symbols=["SPY"],
        start=now - timedelta(days=60),
        end=now,
        starting_cash=50_000.0,
        method="equal_weight",
    )

    resp = await allocator.blend(req)
    assert resp.method == "equal_weight"
    assert resp.starting_cash == 50_000.0
    assert len(resp.strategy_profiles) == 1
    assert resp.strategy_profiles[0].weight == 1.0
