from fastapi import APIRouter, HTTPException, status

from alphaforge.api.deps import RuntimeDep, SubjectDep
from alphaforge.core.logging import get_logger
from alphaforge.core.symbols import normalize_symbol
from alphaforge.models.api import (
    BacktestRequest,
    BacktestResult,
    WalkForwardRequest,
    WalkForwardResult,
)
from alphaforge.models.domain import Bar

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
