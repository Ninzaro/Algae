from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from alphaforge.models.enums import (
    AssetClass,
    JournalEventType,
    OrderSide,
    OrderStatus,
    OrderType,
    SignalSide,
    Timeframe,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _uuid() -> str:
    return str(uuid4())


class Bar(BaseModel):
    """OHLCV bar for a single symbol and timestamp."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    timeframe: Timeframe = Timeframe.D1
    asset_class: AssetClass = AssetClass.EQUITY


class Quote(BaseModel):
    """Last print versus prior close from the market-data adapter."""

    symbol: str
    price: float
    prev_close: float
    change: float
    change_pct: float
    as_of: datetime
    source: str = "yfinance"


class Signal(BaseModel):
    """Pure strategy output. Never contains broker or risk side effects."""

    id: str = Field(default_factory=_uuid)
    strategy_id: str
    symbol: str
    side: SignalSide
    strength: float = Field(ge=-1.0, le=1.0)
    timestamp: datetime = Field(default_factory=_utcnow)
    reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class OrderIntent(BaseModel):
    """Proposed order produced by sizing. Must pass RiskManager before broker."""

    id: str = Field(default_factory=_uuid)
    strategy_id: str
    symbol: str
    side: OrderSide
    quantity: float = Field(gt=0.0)
    order_type: OrderType = OrderType.MARKET
    limit_price: float | None = None
    signal_id: str | None = None
    reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class Order(BaseModel):
    """Order lifecycle record after risk approval."""

    id: str = Field(default_factory=_uuid)
    intent_id: str
    strategy_id: str
    symbol: str
    side: OrderSide
    quantity: float
    filled_quantity: float = 0.0
    order_type: OrderType = OrderType.MARKET
    limit_price: float | None = None
    status: OrderStatus = OrderStatus.PENDING
    broker_order_id: str | None = None
    avg_fill_price: float | None = None
    submitted_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    reject_reason: str | None = None


class Fill(BaseModel):
    id: str = Field(default_factory=_uuid)
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    timestamp: datetime = Field(default_factory=_utcnow)
    fee: float = 0.0


class Position(BaseModel):
    symbol: str
    quantity: float
    avg_price: float
    market_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    market_value: float = 0.0
    side: str = "flat"
    updated_at: datetime = Field(default_factory=_utcnow)

    @model_validator(mode="after")
    def _derived(self) -> "Position":
        self.market_value = self.quantity * self.market_price
        if self.quantity > 0:
            self.side = "long"
        elif self.quantity < 0:
            self.side = "short"
        else:
            self.side = "flat"
        # Ensure market_value is never negative
        if self.market_value < 0:
            self.market_value = 0.0
        return self


class AccountSnapshot(BaseModel):
    cash: float
    equity: float
    buying_power: float
    peak_equity: float
    daily_start_equity: float
    drawdown_pct: float = 0.0
    daily_pnl_pct: float = 0.0
    updated_at: datetime = Field(default_factory=_utcnow)

    @model_validator(mode="after")
    def _derived(self) -> "AccountSnapshot":
        if self.peak_equity > 0:
            self.drawdown_pct = max(
                0.0, (self.peak_equity - self.equity) / self.peak_equity * 100.0
            )
        else:
            self.drawdown_pct = 0.0
        if self.daily_start_equity > 0:
            self.daily_pnl_pct = (
                (self.equity - self.daily_start_equity) / self.daily_start_equity * 100.0
            )
        else:
            self.daily_pnl_pct = 0.0
        return self


class PortfolioSnapshot(BaseModel):
    account: AccountSnapshot
    positions: list[Position] = Field(default_factory=list)
    open_orders: list[Order] = Field(default_factory=list)
    orders_today: int = 0

    def position_for(self, symbol: str) -> Position | None:
        for position in self.positions:
            if position.symbol == symbol:
                return position
        return None

    @property
    def gross_exposure(self) -> float:
        return sum(abs(p.market_value) for p in self.positions)

    @property
    def net_exposure(self) -> float:
        return sum(p.market_value for p in self.positions)

    @property
    def gross_exposure_pct(self) -> float:
        if self.account.equity <= 0:
            return 0.0
        return self.gross_exposure / self.account.equity * 100.0


class RiskDecision(BaseModel):
    approved: bool
    reason: str
    intent_id: str
    adjusted_intent: OrderIntent | None = None
    gates_fired: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=_utcnow)


class EquityPoint(BaseModel):
    timestamp: datetime
    equity: float
    drawdown_pct: float = 0.0


class JournalEntry(BaseModel):
    id: str = Field(default_factory=_uuid)
    event_type: JournalEventType
    timestamp: datetime = Field(default_factory=_utcnow)
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None


class StrategyMeta(BaseModel):
    id: str
    name: str
    description: str = ""
    enabled: bool = True
    symbols: list[str] = Field(default_factory=list)
    timeframe: Timeframe = Timeframe.D1
    params: dict[str, Any] = Field(default_factory=dict)


class StrategyContext(BaseModel):
    """Bars keyed by symbol. Strategies must treat this as read-only."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    as_of: datetime
    bars: dict[str, list[Bar]]
    positions: list[Position] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)

    def bars_for(self, symbol: str) -> list[Bar]:
        return self.bars.get(symbol, [])
