"""Grid-search parameter optimization service for the strategy lab.

Generates parameter combinations, runs a backtest for each,
and returns the ranked results.
"""

from dataclasses import dataclass
from datetime import datetime
from itertools import product
from typing import Any

from alphaforge.core.logging import get_logger
from alphaforge.models.api import GridResultPoint, GridSearchResponse, ParamRange, StrategyLabInfo
from alphaforge.models.domain import Bar
from alphaforge.services.backtest.engine import BacktestEngine
from alphaforge.services.backtest.metrics import PerformanceMetrics
from alphaforge.services.journal.service import JournalService
from alphaforge.services.risk.manager import RiskLimits, RiskManager
from alphaforge.strategies.base import Strategy

log = get_logger(__name__)

_PARAM_DEFAULTS: dict[str, list[dict[str, Any]]] = {
    "sma-crossover": [
        {"name": "fast", "min": 5, "max": 50, "step": 5, "default": 10},
        {"name": "slow", "min": 15, "max": 200, "step": 10, "default": 30},
    ],
    "mean-reversion": [
        {"name": "lookback", "min": 5, "max": 60, "step": 5, "default": 20},
        {"name": "entry_z", "min": 1.0, "max": 3.0, "step": 0.5, "default": 2.0},
        {"name": "exit_z", "min": 0.0, "max": 1.5, "step": 0.5, "default": 0.5},
    ],
    "trend-breakout": [
        {"name": "donchian_window", "min": 10, "max": 60, "step": 5, "default": 20},
        {"name": "exit_window", "min": 5, "max": 30, "step": 5, "default": 10},
        {"name": "atr_mult", "min": 1.5, "max": 4.0, "step": 0.5, "default": 2.5},
    ],
    "volatility-breakout": [
        {"name": "bb_window", "min": 10, "max": 50, "step": 5, "default": 20},
        {"name": "bb_std", "min": 1.0, "max": 3.0, "step": 0.5, "default": 2.0},
        {"name": "squeeze_factor", "min": 0.3, "max": 1.0, "step": 0.1, "default": 0.5},
    ],
    "stat-arb-pairs": [
        {"name": "lookback", "min": 10, "max": 60, "step": 5, "default": 30},
        {"name": "entry_z", "min": 1.0, "max": 3.0, "step": 0.5, "default": 2.0},
    ],
}


def _generate_combinations(ranges: list[ParamRange]) -> list[dict[str, float]]:
    """Generate all parameter combinations from a list of ranges."""
    values: list[list[float]] = []
    for r in ranges:
        vals: list[float] = []
        current = r.min
        while current <= r.max:
            vals.append(round(current, 4))
            current += r.step
        values.append(vals)
    names = [r.name for r in ranges]
    combos: list[dict[str, float]] = []
    for combo in product(*values):
        combos.append({name: val for name, val in zip(names, combo)})
    return combos


def _build_grid(strategy_id: str) -> list[ParamRange]:
    """Build a list of parameter ranges for a given strategy id."""
    raw = _PARAM_DEFAULTS.get(strategy_id, [])
    return [ParamRange(**r) for r in raw]


def get_lab_info(strategy_id: str, name: str, description: str) -> StrategyLabInfo:
    """Get parameter grid info for the strategy lab UI."""
    grid = _build_grid(strategy_id)
    return StrategyLabInfo(
        id=strategy_id,
        name=name,
        description=description,
        param_grid=grid,
    )


async def run_grid_search(
    strategy: Strategy,
    strategy_id: str,
    bars: dict[str, list[Bar]],
    start: datetime,
    end: datetime,
    starting_cash: float,
    backtest_engine: BacktestEngine,
    max_combinations: int = 100,
) -> GridSearchResponse:
    """Run a grid search over parameter combinations.

    For each combination, clones the strategy with those params
    and runs a backtest. Returns all results sorted by Sharpe.
    """
    param_ranges = _build_grid(strategy_id)
    combinations = _generate_combinations(param_ranges)

    if len(combinations) > max_combinations:
        log.warning(
            "grid_search.truncated",
            requested=len(combinations),
            capped=max_combinations,
        )
        combinations = combinations[:max_combinations]

    results: list[GridResultPoint] = []

    for combo in combinations:
        try:
            variant = strategy.with_params(combo)
            outcome = backtest_engine.run_window(
                variant,
                bars,
                start=start,
                end=end,
                starting_cash=starting_cash,
                risk=RiskManager(
                    limits=RiskLimits(
                        max_daily_loss_pct=5.0,
                        max_drawdown_pct=10.0,
                        max_gross_exposure_pct=20.0,
                        max_position_pct=10.0,
                        max_orders_per_day=10,
                    ),
                    journal=JournalService(),
                ),
            )
            results.append(
                GridResultPoint(
                    params=dict(combo),
                    sharpe=round(outcome.sharpe, 4),
                    total_return_pct=round(outcome.total_return_pct, 2),
                    max_drawdown_pct=round(outcome.max_drawdown_pct, 2),
                    trades=outcome.trades,
                    win_rate=round(outcome.metrics.win_rate, 4) if outcome.metrics else 0.0,
                    profit_factor=round(outcome.metrics.profit_factor, 2) if outcome.metrics and outcome.metrics.profit_factor else 0.0,
                )
            )
        except Exception:
            log.warning("grid_search.combo_failed", params=combo, exc_info=True)

    results.sort(key=lambda r: r.sharpe, reverse=True)

    best = results[0] if results else GridResultPoint(
        params={}, sharpe=0, total_return_pct=0, max_drawdown_pct=0, trades=0, win_rate=0, profit_factor=0,
    )

    return GridSearchResponse(
        strategy_id=strategy_id,
        combinations_tested=len(results),
        best_params=dict(best.params),
        best_result=best,
        results=results[:50],
    )
