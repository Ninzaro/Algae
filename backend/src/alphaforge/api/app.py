from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from alphaforge import __version__
from alphaforge.adapters.angelone import AngelOneBroker, AngelOneClient, AngelOneMarketData
from alphaforge.adapters.base import Broker, MarketData
from alphaforge.adapters.paper import PaperBroker
from alphaforge.adapters.yfinance_data import (
    SyntheticMarketData,
    YFinanceMarketData,
    make_synthetic_trend,
)
from alphaforge.api.deps import bind_runtime
from alphaforge.api.routers import (
    auth,
    backtest,
    journal,
    market,
    orders,
    portfolio,
    risk,
    screener,
    strategies,
)
from alphaforge.api.ws import hub
from alphaforge.api.ws import router as ws_router
from alphaforge.core.config import Settings, get_settings
from alphaforge.core.exceptions import AlphaForgeError
from alphaforge.core.logging import configure_logging, get_logger
from alphaforge.models.api import HealthResponse
from alphaforge.services.persistence.store import PersistenceService
from alphaforge.services.runtime import TradingRuntime
from alphaforge.services.strategy.registry import StrategyRegistry
from alphaforge.strategies.mean_reversion import MeanReversionStrategy
from alphaforge.strategies.sma_crossover import SmaCrossoverStrategy
from alphaforge.strategies.statistical_arbitrage import PairsTradingStrategy
from alphaforge.strategies.trend_breakout import TrendBreakoutStrategy
from alphaforge.strategies.volatility_breakout import VolatilityBreakoutStrategy

log = get_logger(__name__)


def _build_registry(settings: Settings) -> StrategyRegistry:
    symbols = ["SPY", "QQQ"] if settings.app_env == "test" else settings.symbol_list()
    if not symbols:
        symbols = ["RELIANCE.NS"]
    registry = StrategyRegistry()
    registry.register(
        SmaCrossoverStrategy(symbols=symbols[:3], fast=10, slow=30),
        enabled=True,
    )
    registry.register(
        MeanReversionStrategy(symbols=symbols[:1], lookback=20, entry_z=2.0),
        enabled=False,
    )
    registry.register(
        TrendBreakoutStrategy(symbols=symbols[:3], donchian_window=20, exit_window=10),
        enabled=False,
    )
    registry.register(
        VolatilityBreakoutStrategy(symbols=symbols[:3], bb_window=20, bb_std=2.0),
        enabled=False,
    )
    pair_symbols = symbols[:2] if len(symbols) >= 2 else ["SPY", "QQQ"]
    registry.register(
        PairsTradingStrategy(symbols=pair_symbols, lookback=30, entry_z=2.0),
        enabled=False,
    )
    return registry


def _build_angel_client(settings: Settings) -> AngelOneClient:
    return AngelOneClient(
        settings.angel_api_key,
        settings.angel_client_code,
        settings.angel_password.get_secret_value(),
        settings.angel_totp_secret.get_secret_value(),
    )


def _build_data_adapter(settings: Settings, angel: AngelOneClient | None) -> MarketData:
    if settings.app_env == "test":
        data = SyntheticMarketData()
        data.set_bars("SPY", make_synthetic_trend("SPY", n=80, drift=0.5))
        data.set_bars("QQQ", make_synthetic_trend("QQQ", start=80.0, n=80, drift=0.35))
        return data
    if settings.data_adapter == "angelone":
        if angel is None:
            raise RuntimeError("Angel One client is required for DATA_ADAPTER=angelone")
        return AngelOneMarketData(angel)
    return YFinanceMarketData()


def _build_broker(settings: Settings, angel: AngelOneClient | None) -> Broker:
    if settings.broker_adapter == "angelone":
        if not settings.is_live:
            log.warning("broker.angelone_forced_paper", reason="TRADING_MODE is not live")
            return PaperBroker(settings.starting_cash)
        if angel is None:
            raise RuntimeError("Angel One client is required for BROKER_ADAPTER=angelone")
        return AngelOneBroker(angel, product=settings.angel_product)
    if settings.is_live and settings.alpaca_api_key:
        from alphaforge.adapters.alpaca import AlpacaBroker

        return AlpacaBroker(
            settings.alpaca_api_key,
            settings.alpaca_secret_key,
            paper=settings.alpaca_paper,
            base_url=settings.alpaca_base_url,
        )
    return PaperBroker(settings.starting_cash)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        angel = None
        needs_angel = settings.data_adapter == "angelone" or (
            settings.broker_adapter == "angelone" and settings.is_live
        )
        if needs_angel and settings.app_env != "test":
            angel = _build_angel_client(settings)
        runtime = TradingRuntime(
            settings,
            broker=_build_broker(settings, angel),
            market_data=_build_data_adapter(settings, angel),
            registry=_build_registry(settings),
        )
        runtime.subscribe(hub.broadcast)
        if settings.app_env != "test":
            store = PersistenceService(settings.database_url)
            if await store.connect():
                await runtime.attach_persistence(store)
            else:
                log.warning("persist.disabled", reason="database unavailable")
        bind_runtime(runtime, settings)
        app.state.runtime = runtime
        if settings.app_env != "test":
            try:
                await runtime.warmup_market_data()
                await runtime.publish("hello")
            except Exception:
                log.exception("data.warmup_failed")
        scheduler = None
        if settings.app_env != "test" and settings.trading_mode != "backtest":
            from apscheduler.schedulers.asyncio import AsyncIOScheduler

            scheduler = AsyncIOScheduler()
            scheduler.add_job(runtime.run_cycle, "interval", minutes=5, id="trading_cycle")
            scheduler.start()
        log.info(
            "app.started",
            mode=settings.trading_mode,
            env=settings.app_env,
            version=__version__,
        )
        yield
        if scheduler is not None:
            scheduler.shutdown(wait=False)
        if runtime.persistence is not None:
            await runtime.persist()
            await runtime.persistence.close()
        if angel is not None:
            await angel.aclose()
        log.info("app.stopped")

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AlphaForgeError)
    async def handle_domain_error(_request: Request, exc: AlphaForgeError) -> JSONResponse:
        status = 400
        if exc.code in {"unauthenticated"}:
            status = 401
        elif exc.code in {"forbidden"}:
            status = 403
        elif exc.code in {"not_found"}:
            status = 404
        elif exc.code in {"risk_rejected", "kill_switch_active"}:
            status = 409
        return JSONResponse(status_code=status, content={"code": exc.code, "message": exc.message})

    @app.get("/", tags=["system"])
    async def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "docs": "/docs",
            "dashboard": "http://localhost:3000",
        }

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    async def health() -> HealthResponse:
        runtime: TradingRuntime | None = getattr(app.state, "runtime", None)
        return HealthResponse(
            status="ok",
            mode=settings.trading_mode,
            kill_switch=bool(runtime.risk.kill_switch_active) if runtime else False,
            persistence=runtime.persistence_backend if runtime else "memory",
            broker=runtime.broker_name if runtime else settings.broker_adapter,
            data=runtime.data.adapter_name if runtime else settings.data_adapter,
        )

    app.include_router(auth.router)
    app.include_router(portfolio.router)
    app.include_router(risk.router)
    app.include_router(strategies.router)
    app.include_router(journal.router)
    app.include_router(orders.router)
    app.include_router(backtest.router)
    app.include_router(market.router)
    app.include_router(screener.router)
    app.include_router(ws_router)
    return app
