from datetime import datetime
from itertools import product
from typing import Any

from alphaforge.models.api import WalkForwardFold, WalkForwardRequest, WalkForwardResult
from alphaforge.models.domain import Bar, EquityPoint
from alphaforge.services.backtest.engine import BacktestEngine, WindowResult, _sharpe
from alphaforge.services.journal.service import JournalService
from alphaforge.services.risk.manager import RiskLimits, RiskManager
from alphaforge.strategies.base import Strategy

_GRIDS: dict[str, list[dict[str, Any]]] = {
    "sma-crossover": [
        {"fast": fast, "slow": slow}
        for fast, slow in product((5, 10, 15), (20, 30, 50))
        if fast < slow
    ],
    "mean-reversion": [
        {"lookback": lookback, "entry_z": entry_z, "exit_z": exit_z}
        for lookback, entry_z, exit_z in product((10, 20, 30), (1.5, 2.0, 2.5), (0.25, 0.5))
    ],
    "trend-breakout": [
        {"donchian_window": donchian_w, "exit_window": exit_w, "atr_window": 14, "atr_mult": 2.5}
        for donchian_w, exit_w in product((20, 30, 40), (10, 15))
        if exit_w < donchian_w
    ],
    "volatility-breakout": [
        {"bb_window": bb_w, "bb_std": bb_std, "squeeze_threshold": sq_th, "rsi_window": 14}
        for bb_w, bb_std, sq_th in product((15, 20), (1.8, 2.0, 2.2), (0.06, 0.08, 0.10))
    ],
    "stat-arb-pairs": [
        {"lookback": lookback, "entry_z": entry_z, "exit_z": 0.5, "stop_z": 3.5}
        for lookback, entry_z in product((20, 30, 40), (1.8, 2.0, 2.5))
    ],
}


class WalkForwardEngine:
    """Rolling train/test evaluation with in-sample parameter search."""

    def __init__(self, backtest: BacktestEngine) -> None:
        self._backtest = backtest

    def run(
        self,
        request: WalkForwardRequest,
        strategy: Strategy,
        bars_by_symbol: dict[str, list[Bar]],
    ) -> WalkForwardResult:
        timestamps = _union_timestamps(bars_by_symbol)
        folds_idx = _fold_indices(
            len(timestamps),
            train=request.train_bars,
            test=request.test_bars,
            step=request.step_bars,
            anchored=request.anchored,
        )
        if not folds_idx:
            return WalkForwardResult(
                strategy_id=strategy.id,
                starting_cash=request.starting_cash,
                ending_equity=request.starting_cash,
                oos_return_pct=0.0,
                oos_max_drawdown_pct=0.0,
                oos_sharpe=0.0,
                folds=[],
                oos_equity_curve=[],
            )

        grid = request.param_grid or _GRIDS.get(strategy.id, [dict(strategy.params)])
        folds: list[WalkForwardFold] = []
        oos_curve: list[EquityPoint] = []
        cash = request.starting_cash

        for train_slice, test_slice in folds_idx:
            train_start, train_end = timestamps[train_slice[0]], timestamps[train_slice[-1]]
            test_start, test_end = timestamps[test_slice[0]], timestamps[test_slice[-1]]
            best_params, is_result = _best_params(
                self._backtest, strategy, bars_by_symbol, grid, train_start, train_end, cash
            )
            fitted = strategy.with_params(best_params)
            oos = self._backtest.run_window(
                fitted,
                bars_by_symbol,
                start=test_start,
                end=test_end,
                starting_cash=cash,
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
            folds.append(
                WalkForwardFold(
                    train_start=train_start,
                    train_end=train_end,
                    test_start=test_start,
                    test_end=test_end,
                    params=best_params,
                    is_return_pct=is_result.total_return_pct,
                    is_sharpe=is_result.sharpe,
                    oos_return_pct=oos.total_return_pct,
                    oos_sharpe=oos.sharpe,
                    oos_max_drawdown_pct=oos.max_drawdown_pct,
                    oos_trades=oos.trades,
                    oos_signals=oos.signals,
                )
            )
            oos_curve.extend(oos.equity_curve)
            cash = oos.ending_equity

        ending = oos_curve[-1].equity if oos_curve else request.starting_cash
        oos_return = (
            (ending / request.starting_cash - 1.0) * 100.0 if request.starting_cash else 0.0
        )
        max_dd = max((p.drawdown_pct for p in oos_curve), default=0.0)
        return WalkForwardResult(
            strategy_id=strategy.id,
            starting_cash=request.starting_cash,
            ending_equity=ending,
            oos_return_pct=oos_return,
            oos_max_drawdown_pct=max_dd,
            oos_sharpe=_sharpe(oos_curve),
            folds=folds,
            oos_equity_curve=oos_curve,
        )


def _best_params(
    engine: BacktestEngine,
    strategy: Strategy,
    bars_by_symbol: dict[str, list[Bar]],
    grid: list[dict[str, Any]],
    start: datetime,
    end: datetime,
    cash: float,
) -> tuple[dict[str, Any], WindowResult]:
    best: WindowResult | None = None
    best_params = dict(strategy.params)
    for params in grid:
        try:
            candidate = strategy.with_params(params)
        except (TypeError, ValueError):
            continue
        result = engine.run_window(
            candidate, bars_by_symbol, start=start, end=end, starting_cash=cash,
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
        if best is None or result.sharpe > best.sharpe:
            best = result
            best_params = dict(candidate.params)
    if best is None:
        fallback = engine.run_window(
            strategy, bars_by_symbol, start=start, end=end, starting_cash=cash,
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
        return dict(strategy.params), fallback
    return best_params, best


def _union_timestamps(bars_by_symbol: dict[str, list[Bar]]) -> list[datetime]:
    stamps = {b.timestamp for rows in bars_by_symbol.values() for b in rows}
    return sorted(stamps)


def _fold_indices(
    n: int,
    *,
    train: int,
    test: int,
    step: int,
    anchored: bool,
) -> list[tuple[range, range]]:
    if n < train + test or train < 5 or test < 1 or step < 1:
        return []
    folds: list[tuple[range, range]] = []
    start = 0
    while start + train + test <= n:
        train_from = 0 if anchored else start
        train_range = range(train_from, start + train)
        test_range = range(start + train, start + train + test)
        folds.append((train_range, test_range))
        start += step
    return folds
