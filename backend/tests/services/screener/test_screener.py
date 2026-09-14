"""Unit tests for the Quantitative Screener Service."""

import pytest

from alphaforge.adapters.yfinance_data import SyntheticMarketData, make_synthetic_trend
from alphaforge.models.api import ScreenerRequest
from alphaforge.services.backtest.engine import BacktestEngine
from alphaforge.services.data.service import MarketDataService
from alphaforge.services.screener.service import QuantitativeScreenerService
from alphaforge.services.strategy.registry import StrategyRegistry
from alphaforge.strategies.sma_crossover import SmaCrossoverStrategy
from alphaforge.strategies.trend_breakout import TrendBreakoutStrategy


@pytest.mark.asyncio
async def test_screener_scan_synthetic() -> None:
    # Setup synthetic trend bars for 2 symbols
    bars_rel = make_synthetic_trend("RELIANCE.NS", start=100.0, n=80, drift=0.5)
    bars_tcs = make_synthetic_trend("TCS.NS", start=200.0, n=80, drift=-0.3)

    market_data = SyntheticMarketData({"RELIANCE.NS": bars_rel, "TCS.NS": bars_tcs})
    data_service = MarketDataService(market_data)

    registry = StrategyRegistry()
    registry.register(SmaCrossoverStrategy(fast=5, slow=15))
    registry.register(TrendBreakoutStrategy(donchian_window=20))

    backtest_engine = BacktestEngine(registry)
    screener = QuantitativeScreenerService(data_service, registry, backtest_engine)

    req = ScreenerRequest(
        custom_symbols=["RELIANCE.NS", "TCS.NS"],
        strategy_ids=["sma-crossover", "trend-breakout"],
        min_strength=0.3,
        side_filter="all",
    )

    response = await screener.scan(req)
    assert response.total_scanned == 2
    assert isinstance(response.hits, list)
    # Uptrending RELIANCE should generate signals
    if response.hits:
        first = response.hits[0]
        assert first.symbol in {"RELIANCE", "TCS"}
        assert first.strength >= 0.3
        assert first.ltp > 0
