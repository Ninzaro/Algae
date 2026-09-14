"""Multi-Strategy Portfolio Allocator & Risk Parity Blend Optimizer."""

import math
from typing import TYPE_CHECKING

from alphaforge.core.logging import get_logger
from alphaforge.core.symbols import normalize_symbol
from alphaforge.models.api import (
    PortfolioBlendRequest,
    PortfolioBlendResponse,
    StrategyReturnProfile,
)
from alphaforge.models.domain import Bar, EquityPoint
from alphaforge.services.backtest.metrics import calculate_performance_metrics
from alphaforge.services.journal.service import JournalService
from alphaforge.services.risk.manager import RiskLimits, RiskManager

if TYPE_CHECKING:
    from alphaforge.services.backtest.engine import BacktestEngine
    from alphaforge.services.data.service import MarketDataService
    from alphaforge.services.strategy.registry import StrategyRegistry

log = get_logger(__name__)


class PortfolioBlendService:
    """Combines multiple quantitative strategies into a single diversified portfolio."""

    def __init__(
        self,
        data_service: "MarketDataService",
        registry: "StrategyRegistry",
        backtest_engine: "BacktestEngine",
    ) -> None:
        self._data = data_service
        self._registry = registry
        self._backtest = backtest_engine

    async def blend(self, req: PortfolioBlendRequest) -> PortfolioBlendResponse:
        # Normalize target symbols
        norm_symbols = [normalize_symbol(s) for s in req.symbols if s.strip()]
        if not norm_symbols:
            norm_symbols = ["SPY"]

        # Fetch historical bars for all symbols
        bars_by_symbol: dict[str, list[Bar]] = {}
        for sym in norm_symbols:
            try:
                rows = await self._data.get_bars(sym, timeframe=req.timeframe, lookback=2000)
                if rows:
                    bars_by_symbol[sym] = rows
            except Exception as exc:
                log.warning("blend.fetch_failed", symbol=sym, error=str(exc))

        if not bars_by_symbol:
            raise ValueError(f"No historical price bars available for symbols: {req.symbols}")

        # Run independent backtest for each strategy in the allocation list
        profiles: list[StrategyReturnProfile] = []
        strategy_return_series: dict[str, list[float]] = {}
        strategy_curves: dict[str, list[EquityPoint]] = {}

        for alloc in req.allocations:
            strat = self._registry.get(alloc.strategy_id)
            if alloc.params:
                strat = strat.with_params(alloc.params)

            window = self._backtest.run_window(
                strat,
                bars_by_symbol,
                start=req.start,
                end=req.end,
                starting_cash=req.starting_cash,
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

            curve = window.equity_curve
            strategy_curves[alloc.strategy_id] = curve

            # Calculate daily percentage returns
            rets: list[float] = []
            for i in range(1, len(curve)):
                prev_eq = curve[i - 1].equity
                if prev_eq > 0:
                    rets.append((curve[i].equity - prev_eq) / prev_eq)
                else:
                    rets.append(0.0)

            strategy_return_series[alloc.strategy_id] = rets

            # Volatility
            vol = _calculate_std(rets) * math.sqrt(252)

            profiles.append(
                StrategyReturnProfile(
                    strategy_id=alloc.strategy_id,
                    name=strat.name,
                    weight=alloc.weight,
                    total_return_pct=window.total_return_pct,
                    sharpe=window.sharpe,
                    max_drawdown_pct=window.max_drawdown_pct,
                    annualized_volatility=round(vol * 100.0, 2),
                    equity_curve=curve,
                )
            )

        if not profiles:
            raise ValueError("No valid strategies provided for portfolio allocation.")

        # Compute Pearson correlation matrix between strategy returns
        strat_ids = [p.strategy_id for p in profiles]
        correlation_matrix: dict[str, dict[str, float]] = {sid: {} for sid in strat_ids}

        for sid1 in strat_ids:
            for sid2 in strat_ids:
                if sid1 == sid2:
                    correlation_matrix[sid1][sid2] = 1.0
                else:
                    r1 = strategy_return_series.get(sid1, [])
                    r2 = strategy_return_series.get(sid2, [])
                    correlation_matrix[sid1][sid2] = round(_pearson_corr(r1, r2), 3)

        # Optimize or calculate strategy weights
        n = len(profiles)
        weights: dict[str, float] = {}

        if req.method == "equal_weight":
            w = 1.0 / n if n > 0 else 0.0
            weights = {p.strategy_id: w for p in profiles}

        elif req.method == "risk_parity":
            # Weight inversely proportional to volatility
            inv_vols = []
            for p in profiles:
                vol = p.annualized_volatility / 100.0
                inv_vols.append(1.0 / max(0.01, vol))
            total_inv = sum(inv_vols)
            for i, p in enumerate(profiles):
                weights[p.strategy_id] = round(inv_vols[i] / total_inv, 4) if total_inv > 0 else (1.0 / n)

        elif req.method == "max_sharpe":
            # Heuristic / Analytical Max Sharpe allocation
            sharpe_scores = [max(0.05, p.sharpe) for p in profiles]
            total_score = sum(sharpe_scores)
            for i, p in enumerate(profiles):
                weights[p.strategy_id] = round(sharpe_scores[i] / total_score, 4) if total_score > 0 else (1.0 / n)

        else:
            # Custom user weights normalized
            total_user_w = sum(p.weight for p in profiles)
            if total_user_w > 0:
                weights = {p.strategy_id: round(p.weight / total_user_w, 4) for p in profiles}
            else:
                weights = {p.strategy_id: 1.0 / n for p in profiles}

        # Update profiles with computed weights
        for p in profiles:
            p.weight = weights.get(p.strategy_id, 0.0)

        # Synthesize combined blended portfolio equity curve
        # Find common timestamp index across all strategy curves
        timestamps = [pt.timestamp for pt in profiles[0].equity_curve]
        blended_curve: list[EquityPoint] = []
        current_equity = req.starting_cash
        peak_equity = req.starting_cash

        # Initial point
        if timestamps:
            blended_curve.append(
                EquityPoint(
                    timestamp=timestamps[0],
                    equity=req.starting_cash,
                    drawdown_pct=0.0,
                )
            )

        blended_returns: list[float] = []

        min_len = min((len(strategy_return_series[sid]) for sid in strat_ids), default=0)

        for t_idx in range(min_len):
            # Daily blended return = sum(w_i * r_i)
            day_ret = sum(weights.get(sid, 0.0) * strategy_return_series[sid][t_idx] for sid in strat_ids)
            blended_returns.append(day_ret)
            current_equity = current_equity * (1.0 + day_ret)
            peak_equity = max(peak_equity, current_equity)
            dd_pct = ((peak_equity - current_equity) / peak_equity * 100.0) if peak_equity > 0 else 0.0

            ts = timestamps[t_idx + 1] if t_idx + 1 < len(timestamps) else timestamps[-1]
            blended_curve.append(
                EquityPoint(
                    timestamp=ts,
                    equity=round(current_equity, 2),
                    drawdown_pct=round(dd_pct, 2),
                )
            )

        # Calculate blended metrics
        m = calculate_performance_metrics(blended_curve, req.starting_cash)

        # Calculate Diversification Ratio and Drawdown Reduction
        weighted_vol = sum(weights.get(p.strategy_id, 0.0) * (p.annualized_volatility / 100.0) for p in profiles)
        blended_vol = _calculate_std(blended_returns) * math.sqrt(252)
        div_ratio = (weighted_vol / blended_vol) if blended_vol > 0 else 1.0

        avg_single_dd = sum(weights.get(p.strategy_id, 0.0) * p.max_drawdown_pct for p in profiles)
        dd_reduction = max(0.0, avg_single_dd - m.max_drawdown_pct)

        return PortfolioBlendResponse(
            method=req.method,
            starting_cash=req.starting_cash,
            ending_equity=round(current_equity, 2),
            total_return_pct=round(m.total_return_pct, 2),
            cagr_pct=round(m.cagr_pct, 2),
            sharpe=round(m.sharpe, 2),
            sortino=round(m.sortino, 2),
            max_drawdown_pct=round(m.max_drawdown_pct, 2),
            annualized_volatility=round(blended_vol * 100.0, 2),
            diversification_ratio=round(div_ratio, 2),
            drawdown_reduction_pct=round(dd_reduction, 2),
            blended_equity_curve=blended_curve,
            strategy_profiles=profiles,
            correlation_matrix=correlation_matrix,
        )


def _calculate_std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(var)


def _pearson_corr(x: list[float], y: list[float]) -> float:
    n = min(len(x), len(y))
    if n < 3:
        return 0.0
    x_sub = x[:n]
    y_sub = y[:n]
    mean_x = sum(x_sub) / n
    mean_y = sum(y_sub) / n

    cov = sum((x_sub[i] - mean_x) * (y_sub[i] - mean_y) for i in range(n))
    std_x = math.sqrt(sum((val - mean_x) ** 2 for val in x_sub))
    std_y = math.sqrt(sum((val - mean_y) ** 2 for val in y_sub))

    if std_x * std_y == 0:
        return 0.0
    return max(-1.0, min(1.0, cov / (std_x * std_y)))
