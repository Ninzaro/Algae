from datetime import UTC, datetime
from uuid import uuid4

from alphaforge.core.exceptions import BrokerError, NotFoundError
from alphaforge.models.domain import AccountSnapshot, Fill, Order, Position
from alphaforge.models.enums import OrderStatus


class PaperBroker:
    """Local simulated broker. Immediate market fills at the supplied reference price."""

    name = "paper"

    def __init__(self, starting_cash: float = 100_000.0) -> None:
        self._cash = starting_cash
        self._orders: dict[str, Order] = {}

    async def submit_order(
        self, order: Order, *, ref_price: float | None = None
    ) -> tuple[Order, Fill | None]:
        price = ref_price if ref_price and ref_price > 0 else order.limit_price
        if price is None or price <= 0:
            raise BrokerError(f"Paper broker needs a reference price for {order.symbol}")
        now = datetime.now(UTC)
        filled = order.model_copy(
            update={
                "status": OrderStatus.FILLED,
                "filled_quantity": order.quantity,
                "avg_fill_price": price,
                "broker_order_id": f"paper-{uuid4()}",
                "updated_at": now,
            }
        )
        fill = Fill(
            order_id=filled.id,
            symbol=filled.symbol,
            side=filled.side,
            quantity=filled.quantity,
            price=price,
            timestamp=now,
            fee=0.0,
        )
        self._orders[filled.id] = filled
        return filled, fill

    async def cancel_order(self, order_id: str) -> Order:
        order = self._orders.get(order_id)
        if order is None:
            raise NotFoundError(f"Unknown order: {order_id}")
        if order.status == OrderStatus.FILLED:
            raise BrokerError("Cannot cancel a filled order")
        cancelled = order.model_copy(
            update={"status": OrderStatus.CANCELLED, "updated_at": datetime.now(UTC)}
        )
        self._orders[order_id] = cancelled
        return cancelled

    async def cancel_all(self) -> list[Order]:
        cancelled: list[Order] = []
        for order_id, order in list(self._orders.items()):
            if order.status in {
                OrderStatus.PENDING,
                OrderStatus.SUBMITTED,
                OrderStatus.PARTIALLY_FILLED,
            }:
                updated = await self.cancel_order(order_id)
                cancelled.append(updated)
        return cancelled

    async def get_positions(self) -> list[Position]:
        return []

    async def get_account(self) -> AccountSnapshot:
        return AccountSnapshot(
            cash=self._cash,
            equity=self._cash,
            buying_power=self._cash,
            peak_equity=self._cash,
            daily_start_equity=self._cash,
        )
