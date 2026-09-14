from datetime import UTC, datetime, timedelta

import pytest

from alphaforge.adapters.paper import PaperBroker
from alphaforge.adapters.yfinance_data import SyntheticMarketData, make_synthetic_trend
from alphaforge.core.config import Settings
from alphaforge.models.domain import AccountSnapshot, Bar, OrderIntent, PortfolioSnapshot, Position
from alphaforge.models.enums import OrderSide, Timeframe
from alphaforge.services.journal.service import JournalService
from alphaforge.services.portfolio.service import PortfolioService
from alphaforge.services.risk.manager import RiskLimits, RiskManager


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env="test",
        trading_mode="paper",
        jwt_secret="test-secret-key-which-is-long-enough",
        master_key="test-master-key",
        api_key="test-api-key",
        operator_email="operator@example.com",
        operator_password="test-pass",
        max_daily_loss_pct=2.0,
        max_drawdown_pct=10.0,
        max_gross_exposure_pct=100.0,
        max_position_pct=20.0,
        max_orders_per_day=50,
        starting_cash=100_000.0,
    )


@pytest.fixture
def journal() -> JournalService:
    return JournalService()


@pytest.fixture
def limits() -> RiskLimits:
    return RiskLimits(
        max_daily_loss_pct=2.0,
        max_drawdown_pct=10.0,
        max_gross_exposure_pct=100.0,
        max_position_pct=20.0,
        max_orders_per_day=50,
    )


@pytest.fixture
def risk(limits: RiskLimits, journal: JournalService) -> RiskManager:
    return RiskManager(limits, journal)


@pytest.fixture
def portfolio() -> PortfolioService:
    return PortfolioService(100_000.0)


@pytest.fixture
def paper_broker() -> PaperBroker:
    return PaperBroker(100_000.0)


@pytest.fixture
def market_data() -> SyntheticMarketData:
    data = SyntheticMarketData()
    data.set_bars("SPY", make_synthetic_trend("SPY", n=80, drift=0.4))
    return data


def make_snapshot(
    *,
    cash: float = 100_000.0,
    equity: float | None = None,
    peak: float | None = None,
    daily_start: float | None = None,
    positions: list[Position] | None = None,
    orders_today: int = 0,
) -> PortfolioSnapshot:
    eq = equity if equity is not None else cash
    return PortfolioSnapshot(
        account=AccountSnapshot(
            cash=cash,
            equity=eq,
            buying_power=cash,
            peak_equity=peak if peak is not None else eq,
            daily_start_equity=daily_start if daily_start is not None else eq,
        ),
        positions=positions or [],
        open_orders=[],
        orders_today=orders_today,
    )


def make_intent(
    *,
    symbol: str = "SPY",
    quantity: float = 10,
    side: OrderSide = OrderSide.BUY,
    ref_price: float = 100.0,
) -> OrderIntent:
    return OrderIntent(
        strategy_id="test",
        symbol=symbol,
        side=side,
        quantity=quantity,
        metadata={"ref_price": ref_price},
    )


def make_bars(symbol: str, closes: list[float], timeframe: Timeframe = Timeframe.D1) -> list[Bar]:
    now = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    bars: list[Bar] = []
    for i, close in enumerate(closes):
        bars.append(
            Bar(
                symbol=symbol,
                timestamp=now - timedelta(days=len(closes) - i),
                open=close,
                high=close * 1.01,
                low=close * 0.99,
                close=close,
                volume=1_000,
                timeframe=timeframe,
            )
        )
    return bars
