from alphaforge.adapters.base import Broker
from alphaforge.core.exceptions import KillSwitchActiveError, RiskRejectedError
from alphaforge.core.logging import get_logger
from alphaforge.models.domain import Fill, Order, OrderIntent, PortfolioSnapshot
from alphaforge.models.enums import JournalEventType, OrderStatus
from alphaforge.services.journal.service import JournalService
from alphaforge.services.portfolio.service import PortfolioService
from alphaforge.services.risk.manager import RiskManager

log = get_logger(__name__)


class ExecutionService:
    """Order lifecycle: risk gate → broker submit → portfolio fill → journal."""

    def __init__(
        self,
        broker: Broker,
        risk: RiskManager,
        portfolio: PortfolioService,
        journal: JournalService,
    ) -> None:
        self._broker = broker
        self._risk = risk
        self._portfolio = portfolio
        self._journal = journal
        self._orders: dict[str, Order] = {}
        self._fills: list[Fill] = []

    @property
    def orders(self) -> list[Order]:
        return [o.model_copy() for o in self._orders.values()]

    @property
    def fills(self) -> list[Fill]:
        return [f.model_copy() for f in self._fills]

    def restore(self, orders: list[Order], fills: list[Fill]) -> None:
        """Hydrate order and fill history from durable storage."""
        self._orders = {order.id: order for order in orders}
        self._fills = list(fills)

    async def submit_intent(self, intent: OrderIntent, portfolio: PortfolioSnapshot) -> Order:
        """Evaluate risk, then submit. Raises if rejected or kill switch is on."""
        self._risk.assert_not_killed()
        decision = self._risk.evaluate(intent, portfolio)
        if not decision.approved or decision.adjusted_intent is None:
            raise RiskRejectedError(decision.reason)

        # Check for duplicate order intent to prevent resubmission
        if any(o.intent_id == decision.adjusted_intent.id for o in self._orders.values()):
            raise RiskRejectedError(f"Order already submitted: {decision.adjusted_intent.id}")

        approved = decision.adjusted_intent
        order = Order(
            intent_id=approved.id,
            strategy_id=approved.strategy_id,
            symbol=approved.symbol,
            side=approved.side,
            quantity=approved.quantity,
            order_type=approved.order_type,
            limit_price=approved.limit_price,
            status=OrderStatus.SUBMITTED,
        )
        self._orders[order.id] = order
        self._portfolio.register_open_order(order)
        self._journal.append(
            JournalEventType.ORDER_SUBMITTED,
            order.model_dump(mode="json"),
            correlation_id=intent.id,
        )

        ref_price = approved.metadata.get("ref_price")
        price = float(ref_price) if isinstance(ref_price, int | float) else None
        try:
            updated, fill = await self._broker.submit_order(order, ref_price=price)
        except Exception:
            failed = order.model_copy(
                update={"status": OrderStatus.REJECTED, "reject_reason": "broker_error"}
            )
            self._orders[order.id] = failed
            self._portfolio.update_order(failed)
            self._journal.append(
                JournalEventType.ORDER_REJECTED,
                {"order_id": order.id, "reason": "broker_error"},
                correlation_id=intent.id,
            )
            raise

        self._orders[updated.id] = updated
        self._portfolio.update_order(updated)
        if fill is not None:
            self._fills.append(fill)
            self._portfolio.apply_fill(fill)
            self._journal.append(
                JournalEventType.ORDER_FILLED,
                fill.model_dump(mode="json"),
                correlation_id=intent.id,
            )
        log.info(
            "execution.submitted",
            order_id=updated.id,
            symbol=updated.symbol,
            status=updated.status.value,
        )
        return updated

    async def cancel_open_orders(self) -> list[Order]:
        cancelled = await self._broker.cancel_all()
        for order in cancelled:
            self._orders[order.id] = order
            self._portfolio.update_order(order)
            self._journal.append(
                JournalEventType.ORDER_CANCELLED,
                order.model_dump(mode="json"),
                correlation_id=order.id,
            )
        snapshot = self._portfolio.snapshot()
        for open_order in snapshot.open_orders:
            updated = open_order.model_copy(update={"status": OrderStatus.CANCELLED})
            self._orders[updated.id] = updated
            self._portfolio.update_order(updated)
        return cancelled

    async def engage_kill_switch(self, reason: str, *, flatten: bool) -> int:
        """Activate the kill switch, cancel opens, optionally flatten longs."""
        self._risk.set_kill_switch(True, reason)
        await self.cancel_open_orders()
        cancelled = 0
        if flatten:
            snapshot = self._portfolio.snapshot()
            for position in snapshot.positions:
                if abs(position.quantity) < 1e-12:
                    continue
                from alphaforge.models.enums import OrderSide

                side = OrderSide.SELL if position.quantity > 0 else OrderSide.BUY
                intent = OrderIntent(
                    strategy_id="kill-switch",
                    symbol=position.symbol,
                    side=side,
                    quantity=abs(position.quantity),
                    reason="kill-switch flatten",
                    metadata={"ref_price": position.market_price},
                )
                try:
                    self._risk.set_kill_switch(False, "temporary flatten window")
                    await self.submit_intent(intent, self._portfolio.snapshot())
                    cancelled += 1
                except (RiskRejectedError, KillSwitchActiveError):
                    log.error("execution.flatten_failed", symbol=position.symbol)
                finally:
                    self._risk.set_kill_switch(True, reason)
        return cancelled
