import pytest
from tests.conftest import make_bars, make_intent

from alphaforge.core.exceptions import KillSwitchActiveError, RiskRejectedError
from alphaforge.models.enums import JournalEventType, OrderSide, OrderStatus
from alphaforge.services.execution.service import ExecutionService
from alphaforge.services.execution.sizing import annualized_vol, size_from_signal
from alphaforge.services.journal.service import JournalService
from alphaforge.services.portfolio.service import PortfolioService
from alphaforge.services.risk.manager import RiskManager


@pytest.fixture
def execution(
    paper_broker, risk: RiskManager, portfolio: PortfolioService, journal: JournalService
) -> ExecutionService:
    return ExecutionService(paper_broker, risk, portfolio, journal)


@pytest.mark.asyncio
async def test_signal_to_fill_path(
    execution: ExecutionService, portfolio: PortfolioService
) -> None:
    intent = make_intent(quantity=10, ref_price=100.0)
    order = await execution.submit_intent(intent, portfolio.snapshot())
    assert order.status == OrderStatus.FILLED
    snap = portfolio.snapshot()
    pos = snap.position_for("SPY")
    assert pos is not None
    assert pos.quantity == 10
    assert len(execution.fills) == 1


@pytest.mark.asyncio
async def test_risk_rejection_blocks_broker(
    execution: ExecutionService, risk: RiskManager, portfolio: PortfolioService
) -> None:
    risk.set_kill_switch(True, "halt")
    with pytest.raises((KillSwitchActiveError, RiskRejectedError)):
        await execution.submit_intent(make_intent(), portfolio.snapshot())
    assert execution.orders == []


@pytest.mark.asyncio
async def test_journal_records_submit_and_fill(
    execution: ExecutionService, portfolio: PortfolioService, journal: JournalService
) -> None:
    await execution.submit_intent(make_intent(quantity=5, ref_price=50.0), portfolio.snapshot())
    types = {e.event_type for e in journal.all_entries()}
    assert JournalEventType.RISK_DECISION in types
    assert JournalEventType.ORDER_SUBMITTED in types
    assert JournalEventType.ORDER_FILLED in types


def test_sizing_flat_without_position() -> None:
    from tests.conftest import make_snapshot

    from alphaforge.models.domain import Signal
    from alphaforge.models.enums import SignalSide

    signal = Signal(strategy_id="x", symbol="SPY", side=SignalSide.FLAT, strength=0.0)
    bars = make_bars("SPY", [100.0] * 30)
    assert (
        size_from_signal(
            signal, make_snapshot(), bars, target_vol=0.1, kelly_fraction=0.25, max_position_pct=20
        )
        is None
    )


def test_sizing_flatten_long() -> None:
    from tests.conftest import make_snapshot

    from alphaforge.models.domain import Position, Signal
    from alphaforge.models.enums import SignalSide

    signal = Signal(strategy_id="x", symbol="SPY", side=SignalSide.FLAT, strength=0.0)
    pos = Position(symbol="SPY", quantity=12, avg_price=100.0, market_price=110.0)
    bars = make_bars("SPY", [100.0] * 30)
    intent = size_from_signal(
        signal,
        make_snapshot(positions=[pos], cash=98_000, equity=99_320),
        bars,
        target_vol=0.1,
        kelly_fraction=0.25,
        max_position_pct=20,
        ref_price=110.0,
    )
    assert intent is not None
    assert intent.side == OrderSide.SELL
    assert intent.quantity == 12


def test_annualized_vol_zero_on_short_series() -> None:
    assert annualized_vol([1.0]) == 0.0
    assert annualized_vol([]) == 0.0
