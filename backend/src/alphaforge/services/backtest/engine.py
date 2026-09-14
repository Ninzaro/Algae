from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from alphaforge.models.api import BacktestRequest, BacktestResult
from alphaforge.models.domain import (
    Bar,
    EquityPoint,
    Fill,
    PortfolioSnapshot,
    Signal,
    StrategyContext,
)
from alphaforge.services.backtest.metrics import (
    PerformanceMetrics,
    calculate_performance_metrics,
)
from alphaforge.services.execution.sizing import size_from_signal
from alphaforge.services.journal.service import JournalService
from alphaforge.services.portfolio.service import PortfolioService
from alphaforge.services.risk.manager import RiskLimits, RiskManager
from alphaforge.services.strategy.registry import StrategyRegistry
from alphaforge.strategies.base import Strategy


@dataclass(slots=True)
class WindowResult:
    starting_cash: float
    ending_equity: float
    total_return_pct: float
    max_drawdown_pct: float
    sharpe: float
    trades: int
    signals: int
    equity_curve: list[EquityPoint] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    metrics: PerformanceMetrics | None = None


class BacktestEngine:
    """Walk a strategy over historical bars using the same signal → size path as paper/live."""

    def __init__(self, registry: StrategyRegistry) -> None:
        self._registry = registry

    def run(self, request: BacktestRequest, bars_by_symbol: dict[str, list[Bar]]) -> BacktestResult:
        strategy = self._registry.get(request.strategy_id)
        if request.params:
            strategy = strategy.with_params(request.params)
        window = self.run_window(
            strategy,
            bars_by_symbol,
            start=request.start,
            end=request.end,
            starting_cash=request.starting_cash,
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

        m = window.metrics or calculate_performance_metrics(window.equity_curve, window.starting_cash)

        return BacktestResult(
            strategy_id=request.strategy_id,
            starting_cash=window.starting_cash,
            ending_equity=window.ending_equity,
            total_return_pct=m.total_return_pct,
            cagr_pct=m.cagr_pct,
            max_drawdown_pct=m.max_drawdown_pct,
            max_drawdown_duration_bars=m.max_drawdown_duration_bars,
            sharpe=m.sharpe,
            sortino=m.sortino,
            calmar=m.calmar,
            trades=m.trades if m.trades > 0 else window.trades,
            winning_trades=m.winning_trades,
            losing_trades=m.losing_trades,
            win_rate=m.win_rate,
            profit_factor=m.profit_factor,
            exposure_pct=m.exposure_pct,
            avg_win=m.avg_win,
            avg_loss=m.avg_loss,
            expectancy=m.expectancy,
            monte_carlo=m.monte_carlo,
            equity_curve=window.equity_curve,
            signals=window.signals,
        )

    def run_window(
        self,
        strategy: Strategy,
        bars_by_symbol: dict[str, list[Bar]],
        *,
        start: datetime,
        end: datetime,
        starting_cash: float,
        risk: RiskManager,
    ) -> WindowResult:
        """Score and trade only inside [start, end], using earlier bars as indicator warmup."""
        start_aware = _aware(start)
        end_aware = _aware(end)
        trade_ts = sorted(
            {
                b.timestamp
                for rows in bars_by_symbol.values()
                for b in rows
                if start_aware <= b.timestamp <= end_aware
            }
        )
        if not trade_ts:
            return WindowResult(
                starting_cash=starting_cash,
                ending_equity=starting_cash,
                total_return_pct=0.0,
                max_drawdown_pct=0.0,
                sharpe=0.0,
                trades=0,
                signals=0,
                params=dict(strategy.params),
            )

        portfolio = PortfolioService(starting_cash)
        signal_count = 0
        trades = 0
        curve: list[EquityPoint] = []
        max_dd = 0.0
        trade_pnls: list[float] = []
        bars_in_market = 0

        for ts in trade_ts:
            window: dict[str, list[Bar]] = {}
            marks: dict[str, float] = {}
            for symbol, rows in bars_by_symbol.items():
                subset = [b for b in rows if b.timestamp <= ts]
                if subset:
                    window[symbol] = subset
                    marks[symbol] = subset[-1].close
            portfolio.mark(marks)
            snap = portfolio.snapshot()

            if snap.positions and any(abs(p.quantity) > 0 for p in snap.positions):
                bars_in_market += 1

            context = StrategyContext(as_of=ts, bars=window, positions=snap.positions)
            signals = strategy.generate_signals(context)
            signal_count += len(signals)
            for signal in signals:
                if self._apply_signal(signal, portfolio, window, risk):
                    trades += 1
            snap = portfolio.snapshot()
            max_dd = max(max_dd, snap.account.drawdown_pct)
            curve.append(
                EquityPoint(
                    timestamp=ts,
                    equity=snap.account.equity,
                    drawdown_pct=snap.account.drawdown_pct,
                )
            )

        ending = curve[-1].equity if curve else starting_cash
        total_return = (ending / starting_cash - 1.0) * 100.0 if starting_cash else 0.0

        metrics = calculate_performance_metrics(
            curve,
            starting_cash,
            trade_pnls=trade_pnls,
            bars_in_market=bars_in_market,
            total_bars=len(trade_ts),
        )

        return WindowResult(
            starting_cash=starting_cash,
            ending_equity=ending,
            total_return_pct=total_return,
            max_drawdown_pct=max_dd,
            sharpe=metrics.sharpe,
            trades=trades,
            signals=signal_count,
            equity_curve=curve,
            params=dict(strategy.params),
            metrics=metrics,
        )

    def _apply_signal(
        self,
        signal: Signal,
        portfolio: PortfolioService,
        window: dict[str, list[Bar]],
        risk: RiskManager,
    ) -> bool:
        snap: PortfolioSnapshot = portfolio.snapshot()
        bars = window.get(signal.symbol, [])
        if not bars:
            clean_sym = signal.symbol.split(".")[0].upper()
            for k, v in window.items():
                if k.split(".")[0].upper() == clean_sym:
                    bars = v
                    break
        if not bars:
            return False
        intent = size_from_signal(
            signal,
            snap,
            bars,
            target_vol=0.10,
            kelly_fraction=0.25,
            max_position_pct=20.0,
            ref_price=bars[-1].close,
        )
        if intent is None:
            return False
        # Evaluate risk gate before applying fill
        portfolio_snap = portfolio.snapshot()
        decision = risk.evaluate(intent, portfolio_snap)
        if not decision.approved:
            return False
        fill = Fill(
            order_id=intent.id,
            symbol=intent.symbol,
            side=intent.side,
            quantity=intent.quantity,
            price=bars[-1].close,
            timestamp=signal.timestamp,
        )
        portfolio.apply_fill(fill, silent=True)
        return True


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _sharpe(curve: list[EquityPoint], periods_per_year: int = 252) -> float:
    m = calculate_performance_metrics(curve, curve[0].equity if curve else 100_000.0, periods_per_year=periods_per_year)
    return m.sharpe


def _positive_day_rate(curve: list[EquityPoint]) -> float:
    if len(curve) < 2:
        return 0.0
    wins = sum(1 for i in range(1, len(curve)) if curve[i].equity > curve[i - 1].equity)
    return wins / (len(curve) - 1)
