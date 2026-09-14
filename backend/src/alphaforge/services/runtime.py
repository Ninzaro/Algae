from datetime import UTC, datetime
from typing import Any

from alphaforge.adapters.base import Broker, MarketData
from alphaforge.core.config import Settings
from alphaforge.core.logging import get_logger
from alphaforge.models.domain import Bar, Quote, Signal, StrategyContext
from alphaforge.models.enums import JournalEventType
from alphaforge.services.backtest.engine import BacktestEngine
from alphaforge.services.backtest.walkforward import WalkForwardEngine
from alphaforge.services.data.service import MarketDataService
from alphaforge.services.events import Event, EventBus
from alphaforge.services.execution.service import ExecutionService
from alphaforge.services.execution.sizing import size_from_signal
from alphaforge.services.journal.service import JournalService
from alphaforge.services.persistence.store import PersistenceService
from alphaforge.services.portfolio.allocator import PortfolioBlendService
from alphaforge.services.portfolio.service import PortfolioService
from alphaforge.services.risk.manager import RiskLimits, RiskManager
from alphaforge.services.screener.service import QuantitativeScreenerService
from alphaforge.services.strategy.hold import SignalHold
from alphaforge.services.strategy.registry import StrategyRegistry

log = get_logger(__name__)


class TradingRuntime:
    """Composition root: wires journal, risk, portfolio, execution, data, strategies, and event bus."""

    def __init__(
        self,
        settings: Settings,
        broker: Broker,
        market_data: MarketData,
        registry: StrategyRegistry,
    ) -> None:
        self.settings = settings
        self.journal = JournalService()
        self.risk = RiskManager(
            RiskLimits(
                max_daily_loss_pct=settings.max_daily_loss_pct,
                max_drawdown_pct=settings.max_drawdown_pct,
                max_gross_exposure_pct=settings.max_gross_exposure_pct,
                max_position_pct=settings.max_position_pct,
                max_orders_per_day=settings.max_orders_per_day,
            ),
            self.journal,
        )
        if settings.kill_switch_enabled:
            self.risk.set_kill_switch(True, "enabled via configuration")
        self.portfolio = PortfolioService(settings.starting_cash)
        self.broker_name = getattr(broker, "name", "paper")
        self.execution = ExecutionService(broker, self.risk, self.portfolio, self.journal)
        self.data = MarketDataService(market_data)
        self.registry = registry
        self.backtest = BacktestEngine(registry)
        self.walkforward = WalkForwardEngine(self.backtest)
        self.screener = QuantitativeScreenerService(self.data, self.registry, self.backtest)
        self.allocator = PortfolioBlendService(self.data, self.registry, self.backtest)
        self.recent_signals: list[Signal] = []
        self.hold = SignalHold()
        self._subscribers: list[Any] = []
        self.persistence: PersistenceService | None = None
        self.persistence_backend = "memory"
        self.event_bus = EventBus()
        self._event_loop_running = False
        self._data_task: Any = None
        self._register_event_handlers()

    def _register_event_handlers(self) -> None:
        """Register each enabled strategy as an event subscriber for its symbols."""
        for meta in self.registry.list_meta():
            if not meta.enabled:
                continue
            symbols = list(meta.symbols)
            self.event_bus.subscribe(
                topics=["bars_updated"],
                symbols=symbols,
                handler=self._make_strategy_handler(meta.id),
                subscriber_id=f"strategy:{meta.id}",
            )

    def _make_strategy_handler(self, strategy_id: str):
        """Create a closure that evaluates a single strategy on a bars_updated event."""

        async def handler(event: Event) -> None:
            if self.risk.kill_switch_active:
                return
            strategies = [s for s in self.registry.get_all() if s.id == strategy_id]
            if not strategies:
                return
            strat = strategies[0]
            symbol = event.data.get("symbol", event.symbol)
            bars_raw = event.data.get("bars", [])
            bars: list[Bar] = [Bar(**b) if isinstance(b, dict) else b for b in bars_raw]

            if not bars:
                return

            prices: dict[str, float] = {}
            snapshot = self.portfolio.snapshot()
            all_bars: dict[str, list[Bar]] = {}
            for sym in strat.symbols:
                cached = self.data.cached_bars(sym)
                all_bars[sym] = cached
                if cached:
                    prices[sym] = cached[-1].close
            if symbol in all_bars:
                bars_list = all_bars[symbol]
            else:
                bars_list = bars
            all_bars[symbol] = bars_list
            if bars_list:
                prices[symbol] = bars_list[-1].close

            self.portfolio.mark(prices)

            context = StrategyContext(
                as_of=datetime.now(UTC),
                bars=all_bars,
                positions=snapshot.positions,
            )
            signals = strat.generate_signals(context)

            valid: list[Signal] = []
            for sig in signals:
                series = all_bars.get(sig.symbol, [])
                bar_ts = series[-1].timestamp if series else sig.timestamp
                if not self.hold.allow(sig, bar_ts):
                    continue
                valid.append(sig)

            if not valid:
                return

            for sig in valid:
                self.journal.append(
                    JournalEventType.SIGNAL,
                    sig.model_dump(mode="json"),
                    correlation_id=sig.id,
                )

            self.recent_signals = (valid + self.recent_signals)[:100]

            for sig in valid:
                intent = size_from_signal(
                    sig,
                    self.portfolio.snapshot(),
                    all_bars.get(sig.symbol, []),
                    target_vol=self.settings.target_volatility,
                    kelly_fraction=self.settings.kelly_fraction,
                    max_position_pct=self.settings.max_position_pct,
                )
                if intent is None:
                    continue
                try:
                    await self.execution.submit_intent(intent, self.portfolio.snapshot())
                except Exception as exc:
                    log.warning(
                        "runtime.intent_skipped",
                        symbol=sig.symbol,
                        reason=str(exc),
                    )

            await self.persist(
                bars=[b for rows in all_bars.values() for b in rows],
                signals=valid,
            )
            await self.publish("cycle")

        return handler

    def refresh_event_subscriptions(self) -> None:
        """Re-register event handlers after strategy enable/disable changes."""
        subscribed_ids = {
            sid
            for sid in self.event_bus._subscriptions
            if sid.startswith("strategy:")
        }
        for sid in subscribed_ids:
            self.event_bus.unsubscribe(sid)
        self._register_event_handlers()
        log.info("runtime.event_subs_refreshed", count=self.event_bus.subscriber_count())

    async def start_event_driven_loop(self, interval_seconds: int = 300) -> None:
        """Start a background loop that fetches data and fires events per symbol."""
        if self._event_loop_running:
            return
        self._event_loop_running = True
        import asyncio

        async def _loop() -> None:
            while self._event_loop_running:
                try:
                    metas = [m for m in self.registry.list_meta() if m.enabled]
                    symbols = sorted({s for m in metas for s in m.symbols})
                    for symbol in symbols:
                        try:
                            rows = await self.data.get_bars(symbol, lookback=120)
                            if rows:
                                await self.event_bus.fire(
                                    Event(
                                        topic="bars_updated",
                                        symbol=symbol,
                                        data={
                                            "symbol": symbol,
                                            "bars": [r.model_dump(mode="json") for r in rows],
                                        },
                                    )
                                )
                        except Exception:
                            log.warning("runtime.data_fetch_failed", symbol=symbol)
                    await asyncio.sleep(interval_seconds)
                except Exception:
                    log.exception("runtime.event_loop_error")
                    await asyncio.sleep(10)

        self._data_task = asyncio.create_task(_loop())
        log.info("runtime.event_loop_started", interval_seconds=interval_seconds)

    async def stop_event_driven_loop(self) -> None:
        """Stop the background data loop."""
        self._event_loop_running = False
        if self._data_task is not None:
            self._data_task.cancel()
            try:
                await self._data_task
            except Exception:
                pass
            self._data_task = None

    def subscribe(self, callback: Any) -> None:
        self._subscribers.append(callback)

    async def _broadcast(self, event: str, payload: dict[str, Any]) -> None:
        for callback in list(self._subscribers):
            try:
                await callback(event, payload)
            except Exception:
                log.exception("runtime.broadcast_failed", event_name=event)

    async def run_cycle(self) -> list[Signal]:
        """Legacy synchronous cycle: evaluates all strategies at once.
        Maintained for manual `Run Cycle` button and backward compatibility."""
        metas = [m for m in self.registry.list_meta() if m.enabled]
        symbols = sorted({s for m in metas for s in m.symbols})
        if not symbols:
            return []

        bars: dict[str, list[Bar]] = {}
        prices: dict[str, float] = {}
        for symbol in symbols:
            rows = await self.data.get_bars(symbol, lookback=120)
            bars[symbol] = rows
            if rows:
                prices[symbol] = rows[-1].close
        self.portfolio.mark(prices)
        snapshot = self.portfolio.snapshot()
        context = StrategyContext(
            as_of=datetime.now(UTC),
            bars=bars,
            positions=snapshot.positions,
        )
        raw_signals = self.registry.generate_all(context)
        signals: list[Signal] = []
        for signal in raw_signals:
            series = bars.get(signal.symbol, [])
            bar_ts = series[-1].timestamp if series else signal.timestamp
            if not self.hold.allow(signal, bar_ts):
                log.info(
                    "runtime.signal_held",
                    strategy_id=signal.strategy_id,
                    symbol=signal.symbol,
                    side=signal.side.value,
                )
                continue
            signals.append(signal)
        for signal in signals:
            self.journal.append(
                JournalEventType.SIGNAL,
                signal.model_dump(mode="json"),
                correlation_id=signal.id,
            )
        self.recent_signals = (signals + self.recent_signals)[:100]

        for signal in signals:
            intent = size_from_signal(
                signal,
                self.portfolio.snapshot(),
                bars.get(signal.symbol, []),
                target_vol=self.settings.target_volatility,
                kelly_fraction=self.settings.kelly_fraction,
                max_position_pct=self.settings.max_position_pct,
            )
            if intent is None:
                continue
            try:
                await self.execution.submit_intent(intent, self.portfolio.snapshot())
            except Exception as exc:
                log.warning(
                    "runtime.intent_skipped",
                    symbol=signal.symbol,
                    reason=str(exc),
                )

        await self.persist(bars=[b for rows in bars.values() for b in rows], signals=signals)
        await self.publish("cycle")
        return signals

    def watchlist(self) -> list[str]:
        symbols = {s for meta in self.registry.list_meta() for s in meta.symbols}
        symbols.update(p.symbol for p in self.portfolio.snapshot().positions)
        return sorted(symbols)

    def quotes(self) -> list[Quote]:
        found: list[Quote] = []
        for symbol in self.watchlist():
            quote = self.data.quote_from_cache(symbol)
            if quote is not None:
                found.append(quote)
        return found

    async def ensure_quotes(self) -> None:
        """Pull a short real-data window for every watched symbol if cache is cold."""
        await self.data.get_quotes(self.watchlist())

    async def warmup_market_data(self) -> None:
        """Load broker contracts and seed quotes so the dashboard is not empty."""
        await self.data.prepare()
        symbols = self.watchlist()
        quotes = await self.data.get_quotes(symbols)
        bars: list[Bar] = []
        for symbol in symbols:
            bars.extend(self.data.cached_bars(symbol))
        if bars:
            await self.persist(bars=bars)
        log.info(
            "data.warmup",
            source=self.data.adapter_name,
            symbols=len(symbols),
            quotes=len(quotes),
            bars=len(bars),
        )

    async def attach_persistence(self, store: PersistenceService) -> None:
        """Connect the store, hydrate memory, and remember the backend name."""
        self.persistence = store
        if not store.enabled:
            return
        loaded = await store.load_book()
        if loaded is None:
            await self.persist()
            self.persistence_backend = "postgres"
            return
        daily_reset = loaded["daily_reset_on"]
        reset_date = daily_reset.date() if hasattr(daily_reset, "date") else daily_reset
        self.journal.load(loaded["journal"])
        self.portfolio.restore(
            cash=loaded["cash"],
            peak_equity=loaded["peak_equity"],
            daily_start_equity=loaded["daily_start_equity"],
            daily_reset_on=reset_date,
            orders_today=loaded["orders_today"],
            realized_pnl=loaded["realized_pnl"],
            positions=loaded["positions"],
            equity_curve=loaded["equity_curve"],
            open_orders=[
                o
                for o in loaded["orders"]
                if o.status.value in {"pending", "submitted", "partially_filled"}
            ],
        )
        self.execution.restore(loaded["orders"], loaded["fills"])
        self.risk.restore_kill_switch(loaded["kill_switch"], loaded["kill_reason"])
        self.registry.apply_enabled(loaded["strategy_enabled"])
        self.recent_signals = list(loaded["signals"])
        self.hold.restore(list(loaded.get("holds", [])))
        self.persistence_backend = "postgres"
        log.info(
            "persist.hydrated",
            positions=len(loaded["positions"]),
            journal=len(loaded["journal"]),
            orders=len(loaded["orders"]),
        )

    async def persist(
        self,
        *,
        bars: list[Bar] | None = None,
        signals: list[Signal] | None = None,
    ) -> None:
        """Flush the in-memory book to Postgres when persistence is enabled."""
        store = self.persistence
        if store is None or not store.enabled:
            return
        try:
            if bars:
                await store.save_bars(bars)
            if signals:
                await store.save_signals(signals)
            await store.save_holds(self.hold.snapshot())
            state = self.portfolio.export_state()
            metas = self.registry.list_meta()
            await store.flush_runtime(
                cash=state["cash"],
                peak_equity=state["peak_equity"],
                daily_start_equity=state["daily_start_equity"],
                daily_reset_on=datetime.combine(state["daily_reset_on"], datetime.min.time()),
                orders_today=state["orders_today"],
                realized_pnl=state["realized_pnl"],
                kill_switch=self.risk.kill_switch_active,
                kill_reason=self.risk.kill_reason,
                positions=state["positions"],
                equity_curve=state["equity_curve"],
                orders=self.execution.orders,
                fills=self.execution.fills,
                journal=list(self.journal.all_entries()),
                strategies=[
                    (
                        m.id,
                        m.name,
                        m.description,
                        m.enabled,
                        list(m.symbols),
                        m.timeframe.value,
                        dict(m.params),
                    )
                    for m in metas
                ],
            )
        except Exception:
            log.exception("persist.flush_failed")

    def dashboard(self) -> dict[str, Any]:
        snap = self.portfolio.snapshot()
        return {
            "mode": self.settings.trading_mode,
            "persistence": self.persistence_backend,
            "kill_switch": self.risk.kill_switch_active,
            "account": snap.account,
            "positions": snap.positions,
            "open_orders": snap.open_orders,
            "recent_signals": self.recent_signals[:20],
            "recent_fills": self.execution.fills[-20:],
            "recent_decisions": [],
            "equity_curve": self.portfolio.equity_curve(),
            "quotes": self.quotes(),
            "data_source": self.data.adapter_name,
        }

    def dashboard_payload(self) -> dict[str, Any]:
        """JSON-safe dashboard snapshot for WebSocket clients."""
        snap = self.portfolio.snapshot()
        return {
            "mode": self.settings.trading_mode,
            "persistence": self.persistence_backend,
            "kill_switch": self.risk.kill_switch_active,
            "account": snap.account.model_dump(mode="json"),
            "positions": [item.model_dump(mode="json") for item in snap.positions],
            "open_orders": [item.model_dump(mode="json") for item in snap.open_orders],
            "recent_signals": [item.model_dump(mode="json") for item in self.recent_signals[:20]],
            "recent_fills": [item.model_dump(mode="json") for item in self.execution.fills[-20:]],
            "recent_decisions": [],
            "equity_curve": [
                item.model_dump(mode="json") for item in self.portfolio.equity_curve()
            ],
            "quotes": [item.model_dump(mode="json") for item in self.quotes()],
            "data_source": self.data.adapter_name,
        }

    async def publish(self, event: str) -> None:
        """Push the current book to all dashboard subscribers."""
        await self._broadcast(event, self.dashboard_payload())
