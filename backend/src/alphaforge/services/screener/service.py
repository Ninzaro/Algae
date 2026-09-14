"""Quantitative Screener Service for scanning stock baskets against systematic trading strategies."""


from alphaforge.core.logging import get_logger
from alphaforge.core.symbols import SCRIP_BY_SYMBOL, get_basket, normalize_symbol
from alphaforge.models.api import ScreenerHit, ScreenerRequest, ScreenerResponse
from alphaforge.models.domain import StrategyContext
from alphaforge.models.enums import SignalSide
from alphaforge.quant.indicators import atr, rsi
from alphaforge.services.backtest.engine import BacktestEngine
from alphaforge.services.data.service import MarketDataService
from alphaforge.services.journal.service import JournalService
from alphaforge.services.risk.manager import RiskLimits, RiskManager
from alphaforge.services.strategy.registry import StrategyRegistry

log = get_logger(__name__)


class QuantitativeScreenerService:
    """Scans market universe for high-conviction strategy setups while filtering noise."""

    def __init__(
        self,
        data_service: MarketDataService,
        strategy_registry: StrategyRegistry,
        backtest_engine: BacktestEngine,
    ) -> None:
        self._data = data_service
        self._registry = strategy_registry
        self._backtest = backtest_engine

    async def scan(self, req: ScreenerRequest) -> ScreenerResponse:
        # Resolve target symbol universe
        if req.custom_symbols:
            symbols = [normalize_symbol(s) for s in req.custom_symbols if s.strip()]
        else:
            symbols = get_basket(req.basket_id)

        if not symbols:
            symbols = get_basket("nifty50")

        # Resolve candidate strategies
        available_ids = [m.id for m in self._registry.list_meta()]
        target_strat_ids = req.strategy_ids if req.strategy_ids else available_ids
        target_strats = [
            self._registry.get(sid) for sid in target_strat_ids if sid in available_ids
        ]

        hits: list[ScreenerHit] = []
        total_scanned = 0

        for sym in symbols[:50]:  # Cap scan batch to 50 for performance
            total_scanned += 1
            try:
                bars = await self._data.get_bars(sym, timeframe=req.timeframe, lookback=180)
            except Exception as exc:
                log.warning("screener.fetch_failed", symbol=sym, error=str(exc))
                continue

            if len(bars) < 25:
                continue

            # Compute technical snapshot
            closes = [b.close for b in bars]
            highs = [b.high for b in bars]
            lows = [b.low for b in bars]

            rsi_series = rsi(closes, window=14)
            latest_rsi = rsi_series[-1] if rsi_series else None

            atr_series = atr(highs, lows, closes, window=14)
            latest_atr = atr_series[-1] if atr_series else None

            # 50-day SMA distance
            dist_sma50: float | None = None
            if len(closes) >= 50:
                sma50 = sum(closes[-50:]) / 50.0
                dist_sma50 = ((closes[-1] - sma50) / sma50) * 100.0 if sma50 > 0 else 0.0

            ltp = closes[-1]
            prev_close = closes[-2] if len(closes) > 1 else ltp
            change_pct = ((ltp - prev_close) / prev_close) * 100.0 if prev_close else 0.0

            clean_sym = sym.split(".")[0].upper()
            scrip_info = SCRIP_BY_SYMBOL.get(clean_sym)
            company_name = scrip_info.name if scrip_info else clean_sym
            exchange = scrip_info.exchange if scrip_info else ("NSE" if ".NS" in sym else "US")

            # Context for strategy evaluation
            now_ts = bars[-1].timestamp
            context = StrategyContext(
                as_of=now_ts,
                bars={sym: bars, clean_sym: bars},
                positions=[],
            )

            # Evaluate each strategy
            for strat in target_strats:
                signals = strat.generate_signals(context)
                for sig in signals:
                    # Noise Filter 1: Ignore FLAT signals
                    if sig.side == SignalSide.FLAT:
                        continue

                    # Noise Filter 2: Minimum Signal Strength
                    if sig.strength < req.min_strength:
                        continue

                    # Noise Filter 3: Side filter
                    if req.side_filter == "buy" and sig.side != SignalSide.BUY:
                        continue
                    if req.side_filter == "sell" and sig.side != SignalSide.SELL:
                        continue

                    # Quick 1-Year historical backtest scorecard for context
                    hist_win_rate: float | None = None
                    hist_sharpe: float | None = None
                    hist_max_dd: float | None = None

                    try:
                        start_time = bars[0].timestamp
                        end_time = bars[-1].timestamp
                        window_res = self._backtest.run_window(
                            strat,
                            {sym: bars},
                            start=start_time,
                            end=end_time,
                            starting_cash=100_000.0,
                            risk=RiskManager(
                                limits=RiskLimits(
                                    max_daily_loss_pct=5.0,
                                    max_drawdown_pct=10.0,
                                    max_gross_exposure_pct=20.0,
                                    max_position_pct=10.0,
                                    max_orders_per_day=10,
                                ),
                                journal=JournalService(),
                            ),
                        )
                        hist_sharpe = window_res.sharpe
                        hist_max_dd = window_res.max_drawdown_pct
                        if window_res.metrics:
                            hist_win_rate = window_res.metrics.win_rate * 100.0
                    except Exception:
                        pass

                    hits.append(
                        ScreenerHit(
                            symbol=clean_sym,
                            name=company_name,
                            exchange=exchange,
                            strategy_id=strat.id,
                            strategy_name=strat.name,
                            side=sig.side,
                            strength=round(sig.strength, 2),
                            reason=sig.reason,
                            ltp=ltp,
                            change_pct=round(change_pct, 2),
                            rsi=round(latest_rsi, 1) if latest_rsi is not None else None,
                            atr=round(latest_atr, 2) if latest_atr is not None else None,
                            dist_sma50_pct=round(dist_sma50, 1) if dist_sma50 is not None else None,
                            hist_win_rate_pct=round(hist_win_rate, 1) if hist_win_rate is not None else None,
                            hist_sharpe=round(hist_sharpe, 2) if hist_sharpe is not None else None,
                            hist_max_dd_pct=round(hist_max_dd, 1) if hist_max_dd is not None else None,
                            timestamp=now_ts,
                        )
                    )

        # Sort by conviction score descending
        hits.sort(key=lambda h: (h.strength, abs(h.change_pct)), reverse=True)
        limited_hits = hits[: req.limit]

        return ScreenerResponse(
            total_scanned=total_scanned,
            hits_count=len(limited_hits),
            hits=limited_hits,
        )
