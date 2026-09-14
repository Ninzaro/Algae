import json

from alphaforge.adapters.paper import PaperBroker
from alphaforge.adapters.yfinance_data import SyntheticMarketData, make_synthetic_trend
from alphaforge.core.config import Settings
from alphaforge.services.runtime import TradingRuntime
from alphaforge.services.strategy.registry import StrategyRegistry
from alphaforge.strategies.sma_crossover import SmaCrossoverStrategy


def test_dashboard_payload_is_json(settings: Settings) -> None:
    data = SyntheticMarketData()
    data.set_bars("SPY", make_synthetic_trend("SPY", n=40, drift=0.3))
    registry = StrategyRegistry()
    registry.register(SmaCrossoverStrategy(symbols=["SPY"], fast=5, slow=15), enabled=True)
    runtime = TradingRuntime(settings, PaperBroker(100_000.0), data, registry)
    payload = runtime.dashboard_payload()
    encoded = json.dumps(payload)
    assert "equity" in encoded
    assert payload["mode"] == "paper"
