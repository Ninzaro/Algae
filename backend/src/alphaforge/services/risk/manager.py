from dataclasses import dataclass

from alphaforge.core.exceptions import KillSwitchActiveError
from alphaforge.core.logging import get_logger
from alphaforge.models.domain import OrderIntent, PortfolioSnapshot, RiskDecision
from alphaforge.models.enums import JournalEventType
from alphaforge.services.journal.service import JournalService

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RiskLimits:
    """Hard numeric gates. Strategies cannot override these."""

    max_daily_loss_pct: float
    max_drawdown_pct: float
    max_gross_exposure_pct: float
    max_position_pct: float
    max_orders_per_day: int

    # Tolerances for floating-point comparisons
    _position_pct_tol: float = 1e-9
    _gross_exposure_pct_tol: float = 1e-9


class RiskManager:
    """Independent pre-trade gate. The only component that may approve an OrderIntent."""

    def __init__(self, limits: RiskLimits, journal: JournalService) -> None:
        self._limits = limits
        self._journal = journal
        self._kill_switch = False
        self._kill_reason = ""

    @property
    def kill_switch_active(self) -> bool:
        return self._kill_switch

    @property
    def kill_reason(self) -> str:
        return self._kill_reason

    @property
    def limits(self) -> RiskLimits:
        return self._limits

    def restore_kill_switch(self, active: bool, reason: str = "") -> None:
        """Hydrate kill-switch flags without writing a journal event."""
        self._kill_switch = active
        self._kill_reason = reason if active else ""

    def set_kill_switch(self, active: bool, reason: str = "") -> None:
        """Engage or release the kill switch and journal the change."""
        self._kill_switch = active
        self._kill_reason = reason if active else ""
        self._journal.append(
            JournalEventType.KILL_SWITCH,
            {"active": active, "reason": reason},
        )
        log.warning("risk.kill_switch", active=active, reason=reason)

    def evaluate(self, intent: OrderIntent, portfolio: PortfolioSnapshot) -> RiskDecision:
        """Synchronously approve or reject an order intent against all hard gates."""
        gates: list[str] = []

        if self._kill_switch:
            gates.append("kill_switch")
            return self._reject(intent, "Kill switch is active", gates)

        account = portfolio.account
        if account.daily_pnl_pct <= -self._limits.max_daily_loss_pct:
            gates.append("daily_loss")
        if account.drawdown_pct >= self._limits.max_drawdown_pct:
            gates.append("max_drawdown")
        if portfolio.orders_today >= self._limits.max_orders_per_day:
            gates.append("max_orders")

        if account.equity <= 0:
            gates.append("zero_equity")
            return self._reject(intent, "Account equity is non-positive", gates)

        existing = portfolio.position_for(intent.symbol)
        existing_qty = existing.quantity if existing else 0.0
        signed = intent.quantity if intent.side.value == "buy" else -intent.quantity
        new_qty = existing_qty + signed
        new_notional = abs(new_qty) * self._mark_price(intent, portfolio)
        new_position_pct = new_notional / account.equity * 100.0

        if new_position_pct > self._limits.max_position_pct + self._limits._position_pct_tol:
            gates.append("max_position")

        current_gross = portfolio.gross_exposure
        old_leg = abs(existing.market_value) if existing else 0.0
        new_gross = current_gross - old_leg + new_notional
        new_gross_pct = new_gross / account.equity * 100.0
        if new_gross_pct > self._limits.max_gross_exposure_pct + self._limits._gross_exposure_pct_tol:
            gates.append("max_gross_exposure")

        if gates:
            reason = "Rejected by gates: " + ", ".join(gates)
            return self._reject(intent, reason, gates)

        decision = RiskDecision(
            approved=True,
            reason="All gates passed",
            intent_id=intent.id,
            adjusted_intent=intent,
            gates_fired=[],
        )
        self._record(decision, intent)
        return decision

    def assert_not_killed(self) -> None:
        if self._kill_switch:
            raise KillSwitchActiveError(self._kill_reason or "Kill switch is active")

    def _mark_price(self, intent: OrderIntent, portfolio: PortfolioSnapshot) -> float:
        if intent.limit_price is not None and intent.limit_price > 0:
            return intent.limit_price
        existing = portfolio.position_for(intent.symbol)
        if existing and existing.market_price > 0:
            return existing.market_price
        raw = intent.metadata.get("ref_price")
        if isinstance(raw, int | float) and raw > 0:
            return float(raw)
        return 1.0

    def _reject(self, intent: OrderIntent, reason: str, gates: list[str]) -> RiskDecision:
        decision = RiskDecision(
            approved=False,
            reason=reason,
            intent_id=intent.id,
            adjusted_intent=None,
            gates_fired=gates,
        )
        self._record(decision, intent)
        log.info(
            "risk.rejected",
            intent_id=intent.id,
            symbol=intent.symbol,
            reason=reason,
            gates=gates,
        )
        return decision

    def _record(self, decision: RiskDecision, intent: OrderIntent) -> None:
        self._journal.append(
            JournalEventType.RISK_DECISION,
            {
                "approved": decision.approved,
                "reason": decision.reason,
                "gates_fired": decision.gates_fired,
                "intent": intent.model_dump(mode="json"),
            },
            correlation_id=intent.id,
        )
