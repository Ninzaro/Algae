from alphaforge.core.exceptions import ConfigurationError
from alphaforge.core.logging import get_logger
from alphaforge.models.domain import AccountSnapshot, Fill, Order, Position
from alphaforge.models.enums import OrderSide, OrderStatus, OrderType

log = get_logger(__name__)


class AlpacaBroker:
    """Alpaca adapter. Imported optionally so the paper path works without alpaca-py."""

    name = "alpaca"

    def __init__(
        self, api_key: str, secret_key: str, *, paper: bool = True, base_url: str = ""
    ) -> None:
        if not api_key or not secret_key:
            raise ConfigurationError("Alpaca credentials are required for the Alpaca broker")
        try:
            from alpaca.trading.client import TradingClient
        except ImportError as exc:
            raise ConfigurationError("alpaca-py is not installed") from exc
        self._client = TradingClient(
            api_key, secret_key, paper=paper, url_override=base_url or None
        )

    async def submit_order(
        self, order: Order, *, ref_price: float | None = None
    ) -> tuple[Order, Fill | None]:
        from alpaca.trading.enums import OrderSide as AlpacaSide
        from alpaca.trading.enums import TimeInForce
        from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest

        side = AlpacaSide.BUY if order.side == OrderSide.BUY else AlpacaSide.SELL
        if order.order_type == OrderType.LIMIT and order.limit_price is not None:
            request = LimitOrderRequest(
                symbol=order.symbol,
                qty=order.quantity,
                side=side,
                time_in_force=TimeInForce.DAY,
                limit_price=order.limit_price,
            )
        else:
            request = MarketOrderRequest(
                symbol=order.symbol,
                qty=order.quantity,
                side=side,
                time_in_force=TimeInForce.DAY,
            )
        submitted = self._client.submit_order(request)
        broker_id = str(submitted.id)
        status = _map_status(str(submitted.status))
        updated = order.model_copy(update={"broker_order_id": broker_id, "status": status})
        log.info("alpaca.submitted", order_id=order.id, broker_id=broker_id, status=status)
        return updated, None

    async def cancel_order(self, order_id: str) -> Order:
        self._client.cancel_order_by_id(order_id)
        return Order(
            id=order_id,
            intent_id=order_id,
            strategy_id="",
            symbol="",
            side=OrderSide.BUY,
            quantity=0.0,
            status=OrderStatus.CANCELLED,
        )

    async def cancel_all(self) -> list[Order]:
        self._client.cancel_orders()
        return []

    async def get_positions(self) -> list[Position]:
        raw = self._client.get_all_positions()
        positions: list[Position] = []
        for item in raw:
            qty = float(item.qty)
            avg = float(item.avg_entry_price)
            mark = float(item.current_price or avg)
            positions.append(
                Position(
                    symbol=str(item.symbol),
                    quantity=qty,
                    avg_price=avg,
                    market_price=mark,
                    unrealized_pnl=float(item.unrealized_pl or 0.0),
                )
            )
        return positions

    async def get_account(self) -> AccountSnapshot:
        account = self._client.get_account()
        equity = float(account.equity)
        cash = float(account.cash)
        return AccountSnapshot(
            cash=cash,
            equity=equity,
            buying_power=float(account.buying_power),
            peak_equity=equity,
            daily_start_equity=float(account.last_equity or equity),
        )


def _map_status(raw: str) -> OrderStatus:
    mapping = {
        "new": OrderStatus.SUBMITTED,
        "accepted": OrderStatus.SUBMITTED,
        "partially_filled": OrderStatus.PARTIALLY_FILLED,
        "filled": OrderStatus.FILLED,
        "canceled": OrderStatus.CANCELLED,
        "cancelled": OrderStatus.CANCELLED,
        "rejected": OrderStatus.REJECTED,
        "expired": OrderStatus.CANCELLED,
    }
    return mapping.get(raw.lower(), OrderStatus.SUBMITTED)
