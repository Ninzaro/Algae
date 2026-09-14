from fastapi import APIRouter, HTTPException, status

from alphaforge.api.deps import RuntimeDep, SubjectDep
from alphaforge.core.logging import get_logger
from alphaforge.core.symbols import normalize_symbol
from alphaforge.models.api import (
    BacktestRequest,
    BacktestResult,
    GridSearchRequest,
    GridSearchResponse,
    StrategyLabInfo,
    WalkForwardRequest,
    WalkForwardResult,
)
from alphaforge.models.domain import Bar
from alphaforge.services.backtest.grid_search import get_lab_info, run_grid_search

log = get_logger(__name__)

router = APIRouter(prefix="/api/v1/backtests", tags=["backtest"])


@router.post("", response_model=BacktestResult)
async def run_backtest(
    body: BacktestRequest,
    runtime: RuntimeDep,
    _user: SubjectDep,
) -> BacktestResult:
    bars: dict[str, list[Bar]] = {}
    normalized_symbols: list[str] = []

    for raw_symbol in body.symbols:
        norm_sym = normalize_symbol(raw_symbol)
        if not norm_sym:
            continue
        try:
            rows = await runtime.data.get_bars(norm_sym, timeframe=body.timeframe, lookback=2000)
            if rows:
                bars[norm_sym] = rows
                normalized_symbols.append(norm_sym)
        except Exception as exc:
            log.warning("backtest.fetch_symbol_failed", symbol=raw_symbol, normalized=norm_sym, error=str(exc))

    if not bars:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No historical price bars available for symbols: {', '.join(body.symbols)}",
        )

    await runtime.persist(bars=[b for rows in bars.values() for b in rows])
    updated_request = body.model_copy(update={"symbols": normalized_symbols})
    return runtime.backtest.run(updated_request, bars)


@router.post("/walk-forward", response_model=WalkForwardResult)
async def run_walk_forward(
    body: WalkForwardRequest,
    runtime: RuntimeDep,
    _user: SubjectDep,
) -> WalkForwardResult:
    bars: dict[str, list[Bar]] = {}
    normalized_symbols: list[str] = []

    for raw_symbol in body.symbols:
        norm_sym = normalize_symbol(raw_symbol)
        if not norm_sym:
            continue
        try:
            rows = await runtime.data.get_bars(norm_sym, timeframe=body.timeframe, lookback=2000)
            if rows:
                filtered = [b for b in rows if body.start <= b.timestamp <= body.end] or rows
                bars[norm_sym] = filtered
                normalized_symbols.append(norm_sym)
        except Exception as exc:
            log.warning("walkforward.fetch_symbol_failed", symbol=raw_symbol, normalized=norm_sym, error=str(exc))

    if not bars:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No historical price bars available for symbols: {', '.join(body.symbols)}",
        )

    await runtime.persist(bars=[b for rows in bars.values() for b in rows])
    strategy = runtime.registry.get(body.strategy_id)
    updated_request = body.model_copy(update={"symbols": normalized_symbols})
    return runtime.walkforward.run(updated_request, strategy, bars)


@router.get("/lab/{strategy_id}", response_model=StrategyLabInfo)
async def get_strategy_lab(
    strategy_id: str,
    runtime: RuntimeDep,
    _user: SubjectDep,
) -> StrategyLabInfo:
    strategy = runtime.registry.get(strategy_id)
    meta = next((m for m in runtime.registry.list_meta() if m.id == strategy_id), None)
    if meta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Strategy '{strategy_id}' not found")
    name = meta.name if meta else strategy.name
    description = meta.description if meta else strategy.description
    return get_lab_info(strategy_id, name, description)


@router.post("/grid-search", response_model=GridSearchResponse)
async def run_grid_search_endpoint(
    body: GridSearchRequest,
    runtime: RuntimeDep,
    _user: SubjectDep,
) -> GridSearchResponse:
    bars: dict[str, list[Bar]] = {}
    normalized_symbols: list[str] = []

    for raw_symbol in body.symbols:
        norm_sym = normalize_symbol(raw_symbol)
        if not norm_sym:
            continue
        try:
            rows = await runtime.data.get_bars(norm_sym, timeframe=body.timeframe, lookback=2000)
            if rows:
                filtered = [b for b in rows if body.start <= b.timestamp <= body.end] or rows
                bars[norm_sym] = filtered
                normalized_symbols.append(norm_sym)
        except Exception as exc:
            log.warning("grid_search.fetch_failed", symbol=raw_symbol, error=str(exc))

    if not bars:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No historical bars for symbols: {', '.join(body.symbols)}",
        )

    strategy = runtime.registry.get(body.strategy_id)
    return await run_grid_search(
        strategy=strategy,
        strategy_id=body.strategy_id,
        bars=bars,
        start=body.start,
        end=body.end,
        starting_cash=body.starting_cash,
        backtest_engine=runtime.backtest,
        max_combinations=body.max_combinations,
    )
