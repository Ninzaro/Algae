from datetime import UTC, date, datetime

from alphaforge.models.domain import EquityPoint, Fill, Order
from alphaforge.models.enums import JournalEventType, OrderSide, OrderStatus
from alphaforge.services.execution.service import ExecutionService
from alphaforge.services.journal.service import JournalService
from alphaforge.services.portfolio.service import PortfolioService
from alphaforge.services.risk.manager import RiskManager
from alphaforge.services.strategy.registry import StrategyRegistry
from alphaforge.strategies.sma_crossover import SmaCrossoverStrategy


def test_portfolio_restore_roundtrip() -> None:
    book = PortfolioService(100_000.0)
    book.apply_fill(Fill(order_id="1", symbol="QQQ", side=OrderSide.BUY, quantity=3, price=700.0))
    book.mark({"QQQ": 723.7})
    state = book.export_state()

    restored = PortfolioService(50_000.0)
    restored.restore(
        cash=float(state["cash"]),
        peak_equity=float(state["peak_equity"]),
        daily_start_equity=float(state["daily_start_equity"]),
        daily_reset_on=date.today(),
        orders_today=int(state["orders_today"]),
        realized_pnl=float(state["realized_pnl"]),
        positions=state["positions"],
        equity_curve=state["equity_curve"],
        open_orders=[],
    )
    snap = restored.snapshot()
    pos = snap.position_for("QQQ")
    assert pos is not None
    assert pos.quantity == 3
    assert abs(snap.account.cash - 97_900.0) < 1e-6


def test_journal_and_flags_restore(journal: JournalService, risk: RiskManager) -> None:
    entry = journal.append(JournalEventType.SIGNAL, {"symbol": "QQQ"})
    other = JournalService()
    other.load(journal.all_entries())
    assert len(other) == 1
    assert other.all_entries()[0].id == entry.id

    risk.restore_kill_switch(True, "halt")
    assert risk.kill_switch_active
    assert risk.kill_reason == "halt"


def test_execution_and_strategy_restore(
    paper_broker, risk: RiskManager, portfolio: PortfolioService, journal: JournalService
) -> None:
    execution = ExecutionService(paper_broker, risk, portfolio, journal)
    order = Order(
        intent_id="i",
        strategy_id="sma-crossover",
        symbol="QQQ",
        side=OrderSide.BUY,
        quantity=3,
        status=OrderStatus.FILLED,
        filled_quantity=3,
        avg_fill_price=700.0,
        submitted_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    fill = Fill(order_id=order.id, symbol="QQQ", side=OrderSide.BUY, quantity=3, price=700.0)
    execution.restore([order], [fill])
    assert execution.orders[0].symbol == "QQQ"
    assert execution.fills[0].quantity == 3

    registry = StrategyRegistry()
    registry.register(SmaCrossoverStrategy(symbols=["QQQ"]), enabled=True)
    registry.apply_enabled({"sma-crossover": False})
    assert not registry.is_enabled("sma-crossover")


def test_export_includes_equity_curve() -> None:
    book = PortfolioService(100_000.0)
    book.mark({})
    curve = book.export_state()["equity_curve"]
    assert isinstance(curve, list)
    assert all(isinstance(p, EquityPoint) for p in curve)
