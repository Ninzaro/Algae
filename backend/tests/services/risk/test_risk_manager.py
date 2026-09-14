import pytest
from hypothesis import given
from hypothesis import settings as hy_settings
from hypothesis import strategies as st
from tests.conftest import make_intent, make_snapshot

from alphaforge.core.exceptions import KillSwitchActiveError
from alphaforge.models.domain import Position
from alphaforge.models.enums import JournalEventType, OrderSide
from alphaforge.services.journal.service import JournalService
from alphaforge.services.risk.manager import RiskLimits, RiskManager


def test_approves_small_order(risk: RiskManager) -> None:
    decision = risk.evaluate(make_intent(quantity=10, ref_price=100.0), make_snapshot())
    assert decision.approved
    assert decision.adjusted_intent is not None
    assert decision.gates_fired == []


def test_rejects_when_kill_switch_active(risk: RiskManager) -> None:
    risk.set_kill_switch(True, "manual")
    decision = risk.evaluate(make_intent(), make_snapshot())
    assert not decision.approved
    assert "kill_switch" in decision.gates_fired


def test_assert_not_killed_raises(risk: RiskManager) -> None:
    risk.set_kill_switch(True, "halt")
    with pytest.raises(KillSwitchActiveError):
        risk.assert_not_killed()


def test_rejects_daily_loss(risk: RiskManager) -> None:
    snap = make_snapshot(cash=97_000.0, equity=97_000.0, daily_start=100_000.0, peak=100_000.0)
    decision = risk.evaluate(make_intent(), snap)
    assert not decision.approved
    assert "daily_loss" in decision.gates_fired


def test_rejects_max_drawdown(risk: RiskManager) -> None:
    snap = make_snapshot(cash=89_000.0, equity=89_000.0, peak=100_000.0, daily_start=89_000.0)
    decision = risk.evaluate(make_intent(), snap)
    assert not decision.approved
    assert "max_drawdown" in decision.gates_fired


def test_rejects_max_orders(risk: RiskManager) -> None:
    snap = make_snapshot(orders_today=50)
    decision = risk.evaluate(make_intent(), snap)
    assert not decision.approved
    assert "max_orders" in decision.gates_fired


def test_rejects_max_position(risk: RiskManager) -> None:
    intent = make_intent(quantity=300, ref_price=100.0)
    decision = risk.evaluate(intent, make_snapshot())
    assert not decision.approved
    assert "max_position" in decision.gates_fired


def test_rejects_gross_exposure(risk: RiskManager) -> None:
    existing = Position(symbol="QQQ", quantity=850, avg_price=100.0, market_price=100.0)
    snap = make_snapshot(
        cash=15_000.0,
        equity=100_000.0,
        positions=[existing],
    )
    intent = make_intent(symbol="SPY", quantity=180, ref_price=100.0)
    decision = risk.evaluate(intent, snap)
    assert not decision.approved
    assert "max_gross_exposure" in decision.gates_fired


def test_rejects_zero_equity(risk: RiskManager) -> None:
    snap = make_snapshot(cash=0.0, equity=0.0)
    decision = risk.evaluate(make_intent(), snap)
    assert not decision.approved
    assert "zero_equity" in decision.gates_fired


def test_allows_reducing_existing_position(risk: RiskManager) -> None:
    existing = Position(symbol="SPY", quantity=50, avg_price=100.0, market_price=100.0)
    snap = make_snapshot(cash=95_000.0, equity=100_000.0, positions=[existing])
    intent = make_intent(quantity=20, side=OrderSide.SELL, ref_price=100.0)
    decision = risk.evaluate(intent, snap)
    assert decision.approved


def test_journals_every_decision(risk: RiskManager, journal: JournalService) -> None:
    risk.evaluate(make_intent(), make_snapshot())
    entries = journal.list_entries(event_type=JournalEventType.RISK_DECISION)
    assert len(entries) == 1
    assert entries[0].payload["approved"] is True


def test_release_kill_switch_allows_orders(risk: RiskManager) -> None:
    risk.set_kill_switch(True, "halt")
    risk.set_kill_switch(False)
    decision = risk.evaluate(make_intent(), make_snapshot())
    assert decision.approved


@hy_settings(max_examples=80)
@given(
    qty=st.floats(min_value=0.01, max_value=10_000, allow_nan=False, allow_infinity=False),
    price=st.floats(min_value=1.0, max_value=1_000, allow_nan=False, allow_infinity=False),
    equity=st.floats(min_value=1_000.0, max_value=1_000_000, allow_nan=False, allow_infinity=False),
    max_pos=st.floats(min_value=1.0, max_value=50.0, allow_nan=False, allow_infinity=False),
)
def test_position_gate_is_never_exceeded(
    qty: float, price: float, equity: float, max_pos: float
) -> None:
    journal = JournalService()
    manager = RiskManager(
        RiskLimits(
            max_daily_loss_pct=100.0,
            max_drawdown_pct=100.0,
            max_gross_exposure_pct=10_000.0,
            max_position_pct=max_pos,
            max_orders_per_day=10_000,
        ),
        journal,
    )
    intent = make_intent(quantity=qty, ref_price=price)
    snap = make_snapshot(cash=equity, equity=equity)
    decision = manager.evaluate(intent, snap)
    notional_pct = qty * price / equity * 100.0
    if notional_pct > max_pos + 1e-6:
        assert not decision.approved
        assert "max_position" in decision.gates_fired
    else:
        assert decision.approved


@hy_settings(max_examples=40)
@given(daily_pnl=st.floats(min_value=-50.0, max_value=10.0, allow_nan=False, allow_infinity=False))
def test_daily_loss_gate_boundary(daily_pnl: float) -> None:
    limit = 2.0
    journal = JournalService()
    manager = RiskManager(
        RiskLimits(
            max_daily_loss_pct=limit,
            max_drawdown_pct=100.0,
            max_gross_exposure_pct=10_000.0,
            max_position_pct=100.0,
            max_orders_per_day=10_000,
        ),
        journal,
    )
    start = 100_000.0
    equity = start * (1.0 + daily_pnl / 100.0)
    snap = make_snapshot(cash=equity, equity=equity, daily_start=start, peak=max(start, equity))
    decision = manager.evaluate(make_intent(quantity=1, ref_price=10.0), snap)
    if daily_pnl <= -limit:
        assert not decision.approved
        assert "daily_loss" in decision.gates_fired
    else:
        assert "daily_loss" not in decision.gates_fired
