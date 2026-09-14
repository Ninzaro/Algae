"""Quantitative performance analytics, risk-adjusted metrics, and Monte Carlo simulation."""

import random
from dataclasses import asdict, dataclass
from math import sqrt
from typing import Any

from alphaforge.models.domain import EquityPoint


@dataclass(frozen=True, slots=True)
class PerformanceMetrics:
    total_return_pct: float
    cagr_pct: float
    max_drawdown_pct: float
    max_drawdown_duration_bars: int
    sharpe: float
    sortino: float
    calmar: float
    trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    exposure_pct: float
    avg_win: float
    avg_loss: float
    expectancy: float
    monte_carlo: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def calculate_performance_metrics(
    curve: list[EquityPoint],
    starting_cash: float,
    *,
    trade_pnls: list[float] | None = None,
    bars_in_market: int = 0,
    total_bars: int = 0,
    periods_per_year: int = 252,
    num_monte_carlo_sims: int = 500,
) -> PerformanceMetrics:
    """Calculate institutional-grade tear-sheet statistics for an equity curve and trade list."""
    if not curve or starting_cash <= 0:
        return _empty_metrics(starting_cash)

    ending_equity = curve[-1].equity
    total_return_pct = ((ending_equity / starting_cash) - 1.0) * 100.0

    # Periodic returns
    daily_rets: list[float] = []
    for i in range(1, len(curve)):
        prev = curve[i - 1].equity
        if prev > 0:
            daily_rets.append((curve[i].equity - prev) / prev)

    n_bars = len(curve)
    years = max(n_bars / periods_per_year, 1.0 / periods_per_year)

    # CAGR %
    if ending_equity > 0:
        cagr_pct = (((ending_equity / starting_cash) ** (1.0 / years)) - 1.0) * 100.0
    else:
        cagr_pct = -100.0

    # Drawdown and max drawdown duration
    max_dd = 0.0
    max_dd_duration = 0
    current_dd_duration = 0
    peak = starting_cash

    for pt in curve:
        if pt.equity > peak:
            peak = pt.equity
            current_dd_duration = 0
        else:
            current_dd_duration += 1
            max_dd_duration = max(max_dd_duration, current_dd_duration)

        if peak > 0:
            dd = (peak - pt.equity) / peak * 100.0
            max_dd = max(max_dd, dd)

    # Sharpe Ratio
    sharpe = 0.0
    if len(daily_rets) >= 2:
        mean_ret = sum(daily_rets) / len(daily_rets)
        var = sum((r - mean_ret) ** 2 for r in daily_rets) / (len(daily_rets) - 1)
        std_ret = sqrt(max(var, 0.0))
        if std_ret > 1e-12:
            sharpe = (mean_ret / std_ret) * sqrt(periods_per_year)

    # Sortino Ratio (Downside deviation)
    sortino = 0.0
    if len(daily_rets) >= 2:
        downside_rets = [min(r, 0.0) for r in daily_rets]
        downside_var = sum(r**2 for r in downside_rets) / len(downside_rets)
        downside_std = sqrt(max(downside_var, 0.0))
        mean_ret = sum(daily_rets) / len(daily_rets)
        if downside_std > 1e-12:
            sortino = (mean_ret / downside_std) * sqrt(periods_per_year)
        elif mean_ret > 0:
            sortino = 100.0

    # Calmar Ratio (CAGR / Max DD)
    calmar = 0.0
    if max_dd > 0:
        calmar = cagr_pct / max_dd

    # Trade stats
    pnls = trade_pnls or []
    trade_count = len(pnls)
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    winning_count = len(wins)
    losing_count = len(losses)

    if trade_count > 0:
        win_rate = winning_count / trade_count
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (100.0 if gross_profit > 0 else 0.0)
        avg_win = (gross_profit / winning_count) if winning_count > 0 else 0.0
        avg_loss = (gross_loss / losing_count) if losing_count > 0 else 0.0
        expectancy = sum(pnls) / trade_count
    else:
        # Fallback to daily positive returns when trade PnLs not logged individually
        pos_days = sum(1 for r in daily_rets if r > 0)
        neg_days = sum(1 for r in daily_rets if r < 0)
        win_rate = (pos_days / len(daily_rets)) if daily_rets else 0.0
        gross_profit = sum(r for r in daily_rets if r > 0)
        gross_loss = abs(sum(r for r in daily_rets if r < 0))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (100.0 if gross_profit > 0 else 0.0)
        avg_win = (gross_profit / pos_days) if pos_days > 0 else 0.0
        avg_loss = (gross_loss / neg_days) if neg_days > 0 else 0.0
        expectancy = (sum(daily_rets) / len(daily_rets)) if daily_rets else 0.0
        winning_count = pos_days
        losing_count = neg_days

    # Market Exposure %
    effective_total = total_bars if total_bars > 0 else n_bars
    exposure_pct = (bars_in_market / effective_total * 100.0) if effective_total > 0 else 0.0

    # Monte Carlo simulation
    mc_source = pnls if len(pnls) >= 5 else daily_rets
    mc_results = run_monte_carlo(
        returns_or_pnls=mc_source,
        starting_cash=starting_cash,
        is_pnl=len(pnls) >= 5,
        num_simulations=num_monte_carlo_sims,
    )

    return PerformanceMetrics(
        total_return_pct=round(total_return_pct, 4),
        cagr_pct=round(cagr_pct, 4),
        max_drawdown_pct=round(max_dd, 4),
        max_drawdown_duration_bars=max_dd_duration,
        sharpe=round(sharpe, 4),
        sortino=round(sortino, 4),
        calmar=round(calmar, 4),
        trades=trade_count,
        winning_trades=winning_count,
        losing_trades=losing_count,
        win_rate=round(win_rate, 4),
        profit_factor=round(profit_factor, 4),
        exposure_pct=round(exposure_pct, 4),
        avg_win=round(avg_win, 4),
        avg_loss=round(avg_loss, 4),
        expectancy=round(expectancy, 4),
        monte_carlo=mc_results,
    )


def run_monte_carlo(
    returns_or_pnls: list[float],
    starting_cash: float,
    *,
    is_pnl: bool = False,
    num_simulations: int = 500,
    horizon: int | None = None,
    seed: int = 42,
) -> dict[str, Any]:
    """Bootstrap resampling Monte Carlo simulation across trades or periodic returns."""
    if not returns_or_pnls or starting_cash <= 0:
        return {
            "simulations": 0,
            "equity_p5": starting_cash,
            "equity_p25": starting_cash,
            "equity_p50": starting_cash,
            "equity_p75": starting_cash,
            "equity_p95": starting_cash,
            "max_dd_p5": 0.0,
            "max_dd_p50": 0.0,
            "max_dd_p95": 0.0,
            "ruin_probability_pct": 0.0,
        }

    rng = random.Random(seed)
    n = horizon or len(returns_or_pnls)
    final_equities: list[float] = []
    max_dds: list[float] = []
    ruined_count = 0
    ruin_threshold = starting_cash * 0.50  # 50% capital loss considered ruin threshold

    for _ in range(num_simulations):
        current_equity = starting_cash
        peak_equity = starting_cash
        sim_max_dd = 0.0
        hit_ruin = False

        for _ in range(n):
            sample = rng.choice(returns_or_pnls)
            if is_pnl:
                current_equity += sample
            else:
                current_equity *= 1.0 + sample

            if current_equity <= 0:
                current_equity = 0.0
                hit_ruin = True
                sim_max_dd = 100.0
                break

            if current_equity > peak_equity:
                peak_equity = current_equity

            dd = (peak_equity - current_equity) / peak_equity * 100.0
            if dd > sim_max_dd:
                sim_max_dd = dd

            if current_equity <= ruin_threshold:
                hit_ruin = True

        if hit_ruin:
            ruined_count += 1

        final_equities.append(current_equity)
        max_dds.append(sim_max_dd)

    final_equities.sort()
    max_dds.sort()

    def _percentile(arr: list[float], pct: float) -> float:
        idx = int(pct * (len(arr) - 1))
        return round(arr[idx], 2)

    return {
        "simulations": num_simulations,
        "equity_p5": _percentile(final_equities, 0.05),
        "equity_p25": _percentile(final_equities, 0.25),
        "equity_p50": _percentile(final_equities, 0.50),
        "equity_p75": _percentile(final_equities, 0.75),
        "equity_p95": _percentile(final_equities, 0.95),
        "max_dd_p5": _percentile(max_dds, 0.05),
        "max_dd_p50": _percentile(max_dds, 0.50),
        "max_dd_p95": _percentile(max_dds, 0.95),
        "ruin_probability_pct": round((ruined_count / num_simulations) * 100.0, 2),
    }


def _empty_metrics(starting_cash: float) -> PerformanceMetrics:
    return PerformanceMetrics(
        total_return_pct=0.0,
        cagr_pct=0.0,
        max_drawdown_pct=0.0,
        max_drawdown_duration_bars=0,
        sharpe=0.0,
        sortino=0.0,
        calmar=0.0,
        trades=0,
        winning_trades=0,
        losing_trades=0,
        win_rate=0.0,
        profit_factor=0.0,
        exposure_pct=0.0,
        avg_win=0.0,
        avg_loss=0.0,
        expectancy=0.0,
        monte_carlo={
            "simulations": 0,
            "equity_p5": starting_cash,
            "equity_p50": starting_cash,
            "equity_p95": starting_cash,
            "max_dd_p50": 0.0,
            "ruin_probability_pct": 0.0,
        },
    )
