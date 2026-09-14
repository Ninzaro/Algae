from enum import StrEnum


class TradingMode(StrEnum):
    BACKTEST = "backtest"
    PAPER = "paper"
    LIVE = "live"


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class SignalSide(StrEnum):
    BUY = "buy"
    SELL = "sell"
    FLAT = "flat"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(StrEnum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class AssetClass(StrEnum):
    EQUITY = "equity"
    ETF = "etf"
    CRYPTO = "crypto"


class Timeframe(StrEnum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    D1 = "1d"


class JournalEventType(StrEnum):
    SIGNAL = "signal"
    RISK_DECISION = "risk_decision"
    ORDER_SUBMITTED = "order_submitted"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_REJECTED = "order_rejected"
    KILL_SWITCH = "kill_switch"
    REBALANCE = "rebalance"
    SYSTEM = "system"
