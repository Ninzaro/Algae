from datetime import UTC, date, datetime
from typing import TypedDict

from alphaforge.core.logging import get_logger
from alphaforge.models.domain import (
    AccountSnapshot,
    EquityPoint,
    Fill,
    Order,
    PortfolioSnapshot,
    Position,
)
from alphaforge.models.enums import OrderSide, OrderStatus

log = get_logger(__name__)


class BookState(TypedDict):
    cash: float
    peak_equity: float
    daily_start_equity: float
    daily_reset_on: date
    orders_today: int
    realized_pnl: float
    positions: list[Position]
    equity_curve: list[EquityPoint]
    open_orders: list[Order]


class PortfolioService:
    """In-process book: cash, positions, marks, and realized PnL."""

    def __init__(self, starting_cash: float) -> None:
        now = datetime.now(UTC)
        self._cash = starting_cash
        self._realized_pnl = 0.0
        self._positions: dict[str, Position] = {}
        self._open_orders: dict[str, Order] = {}
        self._orders_today = 0
        self._orders_day: date = now.date()
        self._peak_equity = starting_cash
        self._daily_start_equity = starting_cash
        self._daily_reset_on = now.date()
        self._equity_curve: list[EquityPoint] = [
            EquityPoint(timestamp=now, equity=starting_cash, drawdown_pct=0.0)
        ]

    def snapshot(self) -> PortfolioSnapshot:
        self._roll_day()
        account = self._account()
        return PortfolioSnapshot(
            account=account,
            positions=[p.model_copy() for p in self._positions.values() if p.quantity != 0],
            open_orders=[o.model_copy() for o in self._open_orders.values()],
            orders_today=self._orders_today,
        )

    def mark(self, prices: dict[str, float]) -> None:
        """Update market prices and unrealized PnL, then snapshot equity."""
        for symbol, price in prices.items():
            position = self._positions.get(symbol)
            if position is None:
                continue
            unrealized = (price - position.avg_price) * position.quantity
            self._positions[symbol] = Position.model_validate(
                {
                    **position.model_dump(),
                    "market_price": price,
                    "unrealized_pnl": unrealized,
                    "updated_at": datetime.now(UTC),
                }
            )
        account = self._account()
        self._peak_equity = max(self._peak_equity, account.equity)
        self._equity_curve.append(
            EquityPoint(
                timestamp=datetime.now(UTC),
                equity=account.equity,
                drawdown_pct=account.drawdown_pct,
            )
        )

    def apply_fill(self, fill: Fill, *, silent: bool = False) -> None:
        """Apply a fill to cash and the position book."""
        signed_qty = fill.quantity if fill.side == OrderSide.BUY else -fill.quantity
        cash_delta = -signed_qty * fill.price - fill.fee
        self._cash += cash_delta

        existing = self._positions.get(fill.symbol)
        if existing is None or existing.quantity == 0:
            self._positions[fill.symbol] = Position(
                symbol=fill.symbol,
                quantity=signed_qty,
                avg_price=fill.price,
                market_price=fill.price,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
            )
            return

        old_qty = existing.quantity
        new_qty = old_qty + signed_qty
        realized = 0.0
        avg_price = existing.avg_price

        closing = old_qty != 0 and (old_qty > 0) != (signed_qty > 0)
        if closing:
            closed = min(abs(old_qty), abs(signed_qty))
            direction = 1.0 if old_qty > 0 else -1.0
            realized = (fill.price - existing.avg_price) * closed * direction
            self._realized_pnl += realized
            if abs(new_qty) < 1e-12:
                new_qty = 0.0
                avg_price = 0.0
            elif (old_qty > 0) != (new_qty > 0):
                avg_price = fill.price
        elif new_qty != 0:
            avg_price = (existing.avg_price * abs(old_qty) + fill.price * abs(signed_qty)) / abs(
                new_qty
            )

        self._positions[fill.symbol] = Position.model_validate(
            {
                **existing.model_dump(),
                "quantity": new_qty,
                "avg_price": avg_price,
                "market_price": fill.price,
                "unrealized_pnl": (fill.price - avg_price) * new_qty if new_qty else 0.0,
                "realized_pnl": existing.realized_pnl + realized,
                "updated_at": fill.timestamp,
            }
        )
        if not silent:
            log.info(
                "portfolio.fill",
                symbol=fill.symbol,
                qty=fill.quantity,
                price=fill.price,
                cash=self._cash,
            )

    def register_open_order(self, order: Order) -> None:
        self._roll_day()
        self._open_orders[order.id] = order
        if order.status in {OrderStatus.SUBMITTED, OrderStatus.PENDING}:
            self._orders_today += 1

    def update_order(self, order: Order) -> None:
        if order.status in {
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
        }:
            self._open_orders.pop(order.id, None)
        else:
            self._open_orders[order.id] = order

    def equity_curve(self, limit: int = 500) -> list[EquityPoint]:
        return self._equity_curve[-limit:]

    def restore(
        self,
        *,
        cash: float,
        peak_equity: float,
        daily_start_equity: float,
        daily_reset_on: date,
        orders_today: int,
        realized_pnl: float,
        positions: list[Position],
        equity_curve: list[EquityPoint],
        open_orders: list[Order],
    ) -> None:
        """Hydrate the book from durable storage."""
        self._cash = cash
        self._peak_equity = peak_equity
        self._daily_start_equity = daily_start_equity
        self._daily_reset_on = daily_reset_on
        self._orders_today = orders_today
        self._orders_day = daily_reset_on
        self._realized_pnl = realized_pnl
        self._positions = {p.symbol: p for p in positions if p.quantity != 0}
        self._open_orders = {o.id: o for o in open_orders}
        self._equity_curve = list(equity_curve) or [
            EquityPoint(timestamp=datetime.now(UTC), equity=cash, drawdown_pct=0.0)
        ]

    def export_state(self) -> BookState:
        """Return the fields needed to persist the book."""
        snap = self.snapshot()
        return {
            "cash": self._cash,
            "peak_equity": self._peak_equity,
            "daily_start_equity": self._daily_start_equity,
            "daily_reset_on": self._daily_reset_on,
            "orders_today": self._orders_today,
            "realized_pnl": self._realized_pnl,
            "positions": snap.positions,
            "equity_curve": list(self._equity_curve),
            "open_orders": snap.open_orders,
        }

    def _account(self) -> AccountSnapshot:
        self._roll_day()
        long_value = sum(p.market_value for p in self._positions.values())
        equity = self._cash + long_value
        self._peak_equity = max(self._peak_equity, equity)
        return AccountSnapshot(
            cash=self._cash,
            equity=equity,
            buying_power=self._cash,
            peak_equity=self._peak_equity,
            daily_start_equity=self._daily_start_equity,
        )

    def _roll_day(self) -> None:
        today = datetime.now(UTC).date()
        if today != self._daily_reset_on:
            self._daily_start_equity = self._account_equity_raw()
            self._daily_reset_on = today
            self._orders_today = 0
            self._orders_day = today

    def _account_equity_raw(self) -> float:
        return self._cash + sum(p.market_value for p in self._positions.values())
