"""Unit tests for performance metrics and Monte Carlo simulation."""

from datetime import UTC, datetime, timedelta

import pytest

from alphaforge.models.domain import EquityPoint
from alphaforge.services.backtest.metrics import (
    calculate_performance_metrics,
    run_monte_carlo,
)


def test_calculate_metrics_growth_curve() -> None:
    base = datetime(2025, 1, 1, tzinfo=UTC)
    starting = 100_000.0
    curve = [
        EquityPoint(timestamp=base + timedelta(days=i), equity=starting * (1.0 + 0.001 * i), drawdown_pct=0.0)
        for i in range(100)
    ]
    metrics = calculate_performance_metrics(curve, starting)

    assert metrics.total_return_pct > 0
    assert metrics.cagr_pct > 0
    assert metrics.sharpe > 0
    assert metrics.sortino > 0
    assert metrics.max_drawdown_pct == 0.0
    assert metrics.win_rate == 1.0


def test_calculate_metrics_with_drawdown() -> None:
    base = datetime(2025, 1, 1, tzinfo=UTC)
    starting = 100_000.0
    equities = [100_000.0, 110_000.0, 105_000.0, 95_000.0, 102_000.0, 120_000.0]
    curve = [
        EquityPoint(timestamp=base + timedelta(days=i), equity=eq, drawdown_pct=0.0)
        for i, eq in enumerate(equities)
    ]
    trade_pnls = [10_000.0, -15_000.0, 7_000.0, 18_000.0]
    metrics = calculate_performance_metrics(curve, starting, trade_pnls=trade_pnls, bars_in_market=4, total_bars=6)

    assert metrics.max_drawdown_pct > 10.0
    assert metrics.trades == 4
    assert metrics.winning_trades == 3
    assert metrics.losing_trades == 1
    assert metrics.win_rate == 0.75
    assert metrics.profit_factor > 1.0
    assert metrics.exposure_pct == pytest.approx((4 / 6) * 100.0, rel=1e-3)
    assert "equity_p50" in metrics.monte_carlo


def test_monte_carlo_resampling() -> None:
    trade_pnls = [500.0, -200.0, 1200.0, -800.0, 450.0, 600.0, -150.0]
    mc = run_monte_carlo(trade_pnls, starting_cash=10_000.0, is_pnl=True, num_simulations=100)

    assert mc["simulations"] == 100
    assert mc["equity_p5"] <= mc["equity_p50"] <= mc["equity_p95"]
    assert 0.0 <= mc["max_dd_p5"] <= mc["max_dd_p95"] <= 100.0
    assert 0.0 <= mc["ruin_probability_pct"] <= 100.0
