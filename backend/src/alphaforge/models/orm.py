from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BarRow(Base):
    __tablename__ = "bars"

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    timeframe: Mapped[str] = mapped_column(String(8), primary_key=True, default="1d")
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float, default=0.0)
    asset_class: Mapped[str] = mapped_column(String(16), default="equity")


class SignalRow(Base):
    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(8))
    strength: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    extra: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class OrderRow(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    intent_id: Mapped[str] = mapped_column(String(36), index=True)
    strategy_id: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(8))
    quantity: Mapped[float] = mapped_column(Float)
    filled_quantity: Mapped[float] = mapped_column(Float, default=0.0)
    order_type: Mapped[str] = mapped_column(String(16), default="market")
    limit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(24), index=True)
    broker_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    avg_fill_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class FillRow(Base):
    __tablename__ = "fills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(36), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(8))
    quantity: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    fee: Mapped[float] = mapped_column(Float, default=0.0)


class PositionRow(Base):
    __tablename__ = "positions"

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    quantity: Mapped[float] = mapped_column(Float)
    avg_price: Mapped[float] = mapped_column(Float)
    market_price: Mapped[float] = mapped_column(Float)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EquityRow(Base):
    __tablename__ = "equity"

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    cash: Mapped[float] = mapped_column(Float)
    equity: Mapped[float] = mapped_column(Float)
    peak_equity: Mapped[float] = mapped_column(Float)
    drawdown_pct: Mapped[float] = mapped_column(Float)


class JournalRow(Base):
    __tablename__ = "journal_entries"

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    correlation_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)


class AccountStateRow(Base):
    __tablename__ = "account_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cash: Mapped[float] = mapped_column(Float)
    peak_equity: Mapped[float] = mapped_column(Float)
    daily_start_equity: Mapped[float] = mapped_column(Float)
    daily_reset_on: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    orders_today: Mapped[int] = mapped_column(default=0)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    kill_switch: Mapped[bool] = mapped_column(Boolean, default=False)
    kill_reason: Mapped[str] = mapped_column(Text, default="")


class SignalHoldRow(Base):
    __tablename__ = "signal_holds"

    strategy_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    side: Mapped[str] = mapped_column(String(8))
    bar_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class StrategyRow(Base):
    __tablename__ = "strategies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    symbols: Mapped[list[str]] = mapped_column(JSON, default=list)
    timeframe: Mapped[str] = mapped_column(String(8), default="1d")
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
