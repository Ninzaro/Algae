from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from alphaforge.models.domain import (
    AccountSnapshot,
    EquityPoint,
    Fill,
    JournalEntry,
    Order,
    PortfolioSnapshot,
    Position,
    Quote,
    RiskDecision,
    Signal,
)
from alphaforge.models.enums import SignalSide, Timeframe


class LoginRequest(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class KillSwitchRequest(BaseModel):
    active: bool
    flatten: bool = True
    reason: str = ""


class KillSwitchResponse(BaseModel):
    active: bool
    reason: str
    cancelled_orders: int = 0


class StrategyToggleRequest(BaseModel):
    enabled: bool


class StrategyView(BaseModel):
    id: str
    name: str
    description: str
    enabled: bool
    symbols: list[str]
    timeframe: Timeframe
    params: dict[str, Any]


class BacktestRequest(BaseModel):
    strategy_id: str
    symbols: list[str]
    start: datetime
    end: datetime
    timeframe: Timeframe = Timeframe.D1
    starting_cash: float = Field(default=100_000.0, gt=0)
    params: dict[str, Any] = Field(default_factory=dict)


class WalkForwardRequest(BaseModel):
    strategy_id: str
    symbols: list[str]
    start: datetime
    end: datetime
    timeframe: Timeframe = Timeframe.D1
    starting_cash: float = Field(default=100_000.0, gt=0)
    train_bars: int = Field(default=252, ge=20)
    test_bars: int = Field(default=63, ge=5)
    step_bars: int = Field(default=63, ge=5)
    anchored: bool = False
    param_grid: list[dict[str, Any]] | None = None


class WalkForwardFold(BaseModel):
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    params: dict[str, Any]
    is_return_pct: float
    is_sharpe: float
    oos_return_pct: float
    oos_sharpe: float
    oos_max_drawdown_pct: float
    oos_trades: int
    oos_signals: int


class WalkForwardResult(BaseModel):
    strategy_id: str
    starting_cash: float
    ending_equity: float
    oos_return_pct: float
    oos_max_drawdown_pct: float
    oos_sharpe: float
    folds: list[WalkForwardFold]
    oos_equity_curve: list[EquityPoint]


class BacktestResult(BaseModel):
    strategy_id: str
    starting_cash: float
    ending_equity: float
    total_return_pct: float
    cagr_pct: float = 0.0
    max_drawdown_pct: float
    max_drawdown_duration_bars: int = 0
    sharpe: float
    sortino: float = 0.0
    calmar: float = 0.0
    trades: int
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float
    profit_factor: float = 0.0
    exposure_pct: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    expectancy: float = 0.0
    monte_carlo: dict[str, Any] = Field(default_factory=dict)
    equity_curve: list[EquityPoint]
    signals: int


class DashboardSnapshot(BaseModel):
    mode: str
    persistence: str = "memory"
    kill_switch: bool
    account: AccountSnapshot
    positions: list[Position]
    open_orders: list[Order]
    recent_signals: list[Signal]
    recent_fills: list[Fill]
    recent_decisions: list[RiskDecision]
    equity_curve: list[EquityPoint]
    quotes: list[Quote] = Field(default_factory=list)
    data_source: str = "yfinance"


class JournalPage(BaseModel):
    items: list[JournalEntry]
    next_cursor: str | None = None


class ErrorBody(BaseModel):
    code: str
    message: str


class HealthResponse(BaseModel):
    status: str
    mode: str
    kill_switch: bool
    persistence: str = "memory"
    broker: str = "paper"
    data: str = "yfinance"


class MarketBarsRequest(BaseModel):
    symbol: str
    timeframe: Timeframe = Timeframe.D1
    lookback: int = Field(default=120, ge=5, le=2000)


class PortfolioResponse(BaseModel):
    snapshot: PortfolioSnapshot


class ScripInfo(BaseModel):
    symbol: str
    name: str
    exchange: str
    sector: str = ""
    backend_symbol: str


class BasketInfo(BaseModel):
    id: str
    name: str
    description: str
    count: int
    symbols: list[str]


class ScreenerHit(BaseModel):
    symbol: str
    name: str
    exchange: str
    strategy_id: str
    strategy_name: str
    side: SignalSide
    strength: float
    reason: str
    ltp: float
    change_pct: float
    rsi: float | None = None
    atr: float | None = None
    dist_sma50_pct: float | None = None
    hist_win_rate_pct: float | None = None
    hist_sharpe: float | None = None
    hist_max_dd_pct: float | None = None
    timestamp: datetime


class ScreenerRequest(BaseModel):
    strategy_ids: list[str] = Field(default_factory=list)
    basket_id: str = "nifty50"
    custom_symbols: list[str] = Field(default_factory=list)
    timeframe: Timeframe = Timeframe.D1
    min_strength: float = Field(default=0.5, ge=0.0, le=1.0)
    side_filter: str = "all"  # "all", "buy", "sell"
    limit: int = Field(default=20, ge=1, le=100)


class ScreenerResponse(BaseModel):
    total_scanned: int
    hits_count: int
    hits: list[ScreenerHit]


class StrategyAllocation(BaseModel):
    strategy_id: str
    weight: float = Field(ge=0.0, le=1.0)
    params: dict[str, Any] = Field(default_factory=dict)


class StrategyReturnProfile(BaseModel):
    strategy_id: str
    name: str
    weight: float
    total_return_pct: float
    sharpe: float
    max_drawdown_pct: float
    annualized_volatility: float
    equity_curve: list[EquityPoint]


class PortfolioBlendRequest(BaseModel):
    allocations: list[StrategyAllocation]
    symbols: list[str]
    start: datetime
    end: datetime
    starting_cash: float = 100_000.0
    timeframe: Timeframe = Timeframe.D1
    method: str = "custom"  # "custom", "equal_weight", "risk_parity", "max_sharpe"


class PortfolioBlendResponse(BaseModel):
    method: str
    starting_cash: float
    ending_equity: float
    total_return_pct: float
    cagr_pct: float
    sharpe: float
    sortino: float
    max_drawdown_pct: float
    annualized_volatility: float
    diversification_ratio: float
    drawdown_reduction_pct: float
    blended_equity_curve: list[EquityPoint]
    strategy_profiles: list[StrategyReturnProfile]
    correlation_matrix: dict[str, dict[str, float]]



