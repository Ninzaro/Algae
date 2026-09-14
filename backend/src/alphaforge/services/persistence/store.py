from datetime import datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from alphaforge.core.db import create_engine_from_url, create_session_factory, init_db
from alphaforge.core.logging import get_logger
from alphaforge.models.domain import (
    Bar,
    EquityPoint,
    Fill,
    JournalEntry,
    Order,
    Position,
    Signal,
)
from alphaforge.models.enums import (
    JournalEventType,
    OrderSide,
    OrderStatus,
    OrderType,
    SignalSide,
)
from alphaforge.models.orm import (
    AccountStateRow,
    BarRow,
    EquityRow,
    FillRow,
    JournalRow,
    OrderRow,
    PositionRow,
    SignalHoldRow,
    SignalRow,
    StrategyRow,
)

log = get_logger(__name__)

_HYPERTABLES = (
    ("bars", "timestamp"),
    ("equity", "timestamp"),
    ("journal_entries", "timestamp"),
)


class PersistenceService:
    """Postgres/Timescale store. Optional — runtime stays in-memory if connect fails."""

    def __init__(self, database_url: str) -> None:
        self._url = database_url
        self._engine: AsyncEngine | None = None
        self._factory: async_sessionmaker[AsyncSession] | None = None
        self.enabled = False

    async def connect(self) -> bool:
        """Create tables (and hypertables when Timescale is present)."""
        try:
            self._engine = create_engine_from_url(self._url)
            self._factory = create_session_factory(self._engine)
            await init_db(self._engine)
            await self._ensure_hypertables()
            self.enabled = True
            log.info("persist.connected")
            return True
        except Exception:
            log.exception("persist.connect_failed")
            self.enabled = False
            if self._engine is not None:
                await self._engine.dispose()
            self._engine = None
            self._factory = None
            return False

    async def close(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._factory = None
        self.enabled = False

    async def _session(self) -> AsyncSession:
        if self._factory is None:
            raise RuntimeError("Persistence is not connected")
        return self._factory()

    async def _ensure_hypertables(self) -> None:
        if self._engine is None:
            return
        async with self._engine.begin() as conn:
            for table, column in _HYPERTABLES:
                try:
                    await conn.execute(
                        text("SELECT create_hypertable(:table, :column, if_not_exists => TRUE)"),
                        {"table": table, "column": column},
                    )
                except Exception:
                    log.info("persist.hypertable_skipped", table=table)

    async def load_book(self) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        async with await self._session() as session:
            state = await session.get(AccountStateRow, 1)
            if state is None:
                return None
            positions = [
                _position_from_row(row)
                for row in (await session.execute(select(PositionRow))).scalars()
            ]
            equity_rows = (
                await session.execute(select(EquityRow).order_by(EquityRow.timestamp.asc()))
            ).scalars()
            curve = [
                EquityPoint(
                    timestamp=row.timestamp,
                    equity=row.equity,
                    drawdown_pct=row.drawdown_pct,
                )
                for row in equity_rows
            ]
            order_rows = (await session.execute(select(OrderRow))).scalars()
            orders = [_order_from_row(row) for row in order_rows]
            fill_rows = (
                await session.execute(select(FillRow).order_by(FillRow.timestamp.asc()))
            ).scalars()
            fills = [_fill_from_row(row) for row in fill_rows]
            journal_rows = (
                await session.execute(select(JournalRow).order_by(JournalRow.timestamp.asc()))
            ).scalars()
            journal = [_journal_from_row(row) for row in journal_rows]
            signal_rows = (
                await session.execute(
                    select(SignalRow).order_by(SignalRow.timestamp.desc()).limit(100)
                )
            ).scalars()
            signals = [_signal_from_row(row) for row in signal_rows]
            strategy_rows = (await session.execute(select(StrategyRow))).scalars()
            enabled = {row.id: row.enabled for row in strategy_rows}
            hold_rows = (await session.execute(select(SignalHoldRow))).scalars()
            holds = [
                (row.strategy_id, row.symbol, row.side, row.bar_timestamp) for row in hold_rows
            ]
            return {
                "cash": state.cash,
                "peak_equity": state.peak_equity,
                "daily_start_equity": state.daily_start_equity,
                "daily_reset_on": state.daily_reset_on,
                "orders_today": state.orders_today,
                "realized_pnl": state.realized_pnl,
                "kill_switch": state.kill_switch,
                "kill_reason": state.kill_reason,
                "positions": [p for p in positions if p.quantity != 0],
                "equity_curve": curve,
                "orders": orders,
                "fills": fills,
                "journal": journal,
                "signals": signals,
                "strategy_enabled": enabled,
                "holds": holds,
            }

    async def save_bars(self, bars: list[Bar]) -> None:
        if not self.enabled or not bars:
            return
        async with await self._session() as session:
            for bar in bars:
                stmt = insert(BarRow).values(
                    symbol=bar.symbol,
                    timestamp=bar.timestamp,
                    timeframe=bar.timeframe.value,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                    asset_class=bar.asset_class.value,
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=["symbol", "timestamp", "timeframe"],
                    set_={
                        "open": stmt.excluded.open,
                        "high": stmt.excluded.high,
                        "low": stmt.excluded.low,
                        "close": stmt.excluded.close,
                        "volume": stmt.excluded.volume,
                    },
                )
                await session.execute(stmt)
            await session.commit()

    async def save_signals(self, signals: list[Signal]) -> None:
        if not self.enabled or not signals:
            return
        async with await self._session() as session:
            for signal in signals:
                session.add(
                    SignalRow(
                        id=signal.id,
                        strategy_id=signal.strategy_id,
                        symbol=signal.symbol,
                        side=signal.side.value,
                        strength=signal.strength,
                        timestamp=signal.timestamp,
                        reason=signal.reason,
                        extra=signal.metadata,
                    )
                )
            await session.commit()

    async def flush_runtime(
        self,
        *,
        cash: float,
        peak_equity: float,
        daily_start_equity: float,
        daily_reset_on: datetime,
        orders_today: int,
        realized_pnl: float,
        kill_switch: bool,
        kill_reason: str,
        positions: list[Position],
        equity_curve: list[EquityPoint],
        orders: list[Order],
        fills: list[Fill],
        journal: list[JournalEntry],
        strategies: list[tuple[str, str, str, bool, list[str], str, dict[str, Any]]],
    ) -> None:
        if not self.enabled:
            return
        async with await self._session() as session:
            state = await session.get(AccountStateRow, 1)
            if state is None:
                session.add(
                    AccountStateRow(
                        id=1,
                        cash=cash,
                        peak_equity=peak_equity,
                        daily_start_equity=daily_start_equity,
                        daily_reset_on=daily_reset_on,
                        orders_today=orders_today,
                        realized_pnl=realized_pnl,
                        kill_switch=kill_switch,
                        kill_reason=kill_reason,
                    )
                )
            else:
                state.cash = cash
                state.peak_equity = peak_equity
                state.daily_start_equity = daily_start_equity
                state.daily_reset_on = daily_reset_on
                state.orders_today = orders_today
                state.realized_pnl = realized_pnl
                state.kill_switch = kill_switch
                state.kill_reason = kill_reason

            existing_pos = {
                pos_row.symbol: pos_row
                for pos_row in (await session.execute(select(PositionRow))).scalars()
            }
            keep = {p.symbol for p in positions if p.quantity != 0}
            for symbol, pos_row in existing_pos.items():
                if symbol not in keep:
                    await session.delete(pos_row)
            for position in positions:
                if position.quantity == 0:
                    continue
                found = existing_pos.get(position.symbol)
                if found is None:
                    session.add(_position_to_row(position))
                else:
                    found.quantity = position.quantity
                    found.avg_price = position.avg_price
                    found.market_price = position.market_price
                    found.unrealized_pnl = position.unrealized_pnl
                    found.realized_pnl = position.realized_pnl
                    found.updated_at = position.updated_at

            known_orders = {
                order_row.id: order_row
                for order_row in (await session.execute(select(OrderRow))).scalars()
            }
            for order in orders:
                order_row = known_orders.get(order.id)
                if order_row is None:
                    session.add(_order_to_row(order))
                else:
                    order_row.status = order.status.value
                    order_row.filled_quantity = order.filled_quantity
                    order_row.avg_fill_price = order.avg_fill_price
                    order_row.broker_order_id = order.broker_order_id
                    order_row.updated_at = order.updated_at
                    order_row.reject_reason = order.reject_reason

            known_fills = {row.id for row in (await session.execute(select(FillRow))).scalars()}
            for fill in fills:
                if fill.id not in known_fills:
                    session.add(_fill_to_row(fill))

            known_journal = {
                row.id for row in (await session.execute(select(JournalRow))).scalars()
            }
            for entry in journal:
                if entry.id not in known_journal:
                    session.add(_journal_to_row(entry))

            known_eq = {
                (row.timestamp, row.id)
                for row in (await session.execute(select(EquityRow))).scalars()
            }
            for point in equity_curve:
                key = (point.timestamp, _equity_id(point))
                if key in known_eq:
                    continue
                session.add(
                    EquityRow(
                        timestamp=point.timestamp,
                        id=_equity_id(point),
                        cash=cash,
                        equity=point.equity,
                        peak_equity=peak_equity,
                        drawdown_pct=point.drawdown_pct,
                    )
                )
                known_eq.add(key)

            known_strat = {
                strat_row.id: strat_row
                for strat_row in (await session.execute(select(StrategyRow))).scalars()
            }
            for sid, name, description, enabled, symbols, timeframe, params in strategies:
                strat_row = known_strat.get(sid)
                if strat_row is None:
                    session.add(
                        StrategyRow(
                            id=sid,
                            name=name,
                            description=description,
                            enabled=enabled,
                            symbols=symbols,
                            timeframe=timeframe,
                            params=params,
                        )
                    )
                else:
                    strat_row.enabled = enabled
                    strat_row.symbols = symbols
                    strat_row.params = params

            await session.commit()

    async def save_holds(self, holds: list[tuple[str, str, str, datetime]]) -> None:
        if not self.enabled:
            return
        async with await self._session() as session:
            existing = {
                (row.strategy_id, row.symbol): row
                for row in (await session.execute(select(SignalHoldRow))).scalars()
            }
            keep = {(strategy_id, symbol) for strategy_id, symbol, _side, _ts in holds}
            for key, row in existing.items():
                if key not in keep:
                    await session.delete(row)
            for strategy_id, symbol, side, bar_ts in holds:
                hold_row = existing.get((strategy_id, symbol))
                if hold_row is None:
                    session.add(
                        SignalHoldRow(
                            strategy_id=strategy_id,
                            symbol=symbol,
                            side=side,
                            bar_timestamp=bar_ts,
                        )
                    )
                else:
                    hold_row.side = side
                    hold_row.bar_timestamp = bar_ts
            await session.commit()


def _equity_id(point: EquityPoint) -> str:
    return f"{int(point.timestamp.timestamp() * 1000)}"


def _position_to_row(position: Position) -> PositionRow:
    return PositionRow(
        symbol=position.symbol,
        quantity=position.quantity,
        avg_price=position.avg_price,
        market_price=position.market_price,
        unrealized_pnl=position.unrealized_pnl,
        realized_pnl=position.realized_pnl,
        updated_at=position.updated_at,
    )


def _position_from_row(row: PositionRow) -> Position:
    return Position(
        symbol=row.symbol,
        quantity=row.quantity,
        avg_price=row.avg_price,
        market_price=row.market_price,
        unrealized_pnl=row.unrealized_pnl,
        realized_pnl=row.realized_pnl,
        updated_at=row.updated_at,
    )


def _order_to_row(order: Order) -> OrderRow:
    return OrderRow(
        id=order.id,
        intent_id=order.intent_id,
        strategy_id=order.strategy_id,
        symbol=order.symbol,
        side=order.side.value,
        quantity=order.quantity,
        filled_quantity=order.filled_quantity,
        order_type=order.order_type.value,
        limit_price=order.limit_price,
        status=order.status.value,
        broker_order_id=order.broker_order_id,
        avg_fill_price=order.avg_fill_price,
        submitted_at=order.submitted_at,
        updated_at=order.updated_at,
        reject_reason=order.reject_reason,
    )


def _order_from_row(row: OrderRow) -> Order:
    return Order(
        id=row.id,
        intent_id=row.intent_id,
        strategy_id=row.strategy_id,
        symbol=row.symbol,
        side=OrderSide(row.side),
        quantity=row.quantity,
        filled_quantity=row.filled_quantity,
        order_type=OrderType(row.order_type),
        limit_price=row.limit_price,
        status=OrderStatus(row.status),
        broker_order_id=row.broker_order_id,
        avg_fill_price=row.avg_fill_price,
        submitted_at=row.submitted_at,
        updated_at=row.updated_at,
        reject_reason=row.reject_reason,
    )


def _fill_to_row(fill: Fill) -> FillRow:
    return FillRow(
        id=fill.id,
        order_id=fill.order_id,
        symbol=fill.symbol,
        side=fill.side.value,
        quantity=fill.quantity,
        price=fill.price,
        timestamp=fill.timestamp,
        fee=fill.fee,
    )


def _fill_from_row(row: FillRow) -> Fill:
    return Fill(
        id=row.id,
        order_id=row.order_id,
        symbol=row.symbol,
        side=OrderSide(row.side),
        quantity=row.quantity,
        price=row.price,
        timestamp=row.timestamp,
        fee=row.fee,
    )


def _journal_to_row(entry: JournalEntry) -> JournalRow:
    return JournalRow(
        id=entry.id,
        event_type=entry.event_type.value,
        timestamp=entry.timestamp,
        payload=entry.payload,
        correlation_id=entry.correlation_id,
    )


def _journal_from_row(row: JournalRow) -> JournalEntry:
    return JournalEntry(
        id=row.id,
        event_type=JournalEventType(row.event_type),
        timestamp=row.timestamp,
        payload=row.payload,
        correlation_id=row.correlation_id,
    )


def _signal_from_row(row: SignalRow) -> Signal:
    return Signal(
        id=row.id,
        strategy_id=row.strategy_id,
        symbol=row.symbol,
        side=SignalSide(row.side),
        strength=row.strength,
        timestamp=row.timestamp,
        reason=row.reason,
        metadata=row.extra or {},
    )
