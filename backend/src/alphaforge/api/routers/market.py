from fastapi import APIRouter, Query

from alphaforge.api.deps import RuntimeDep, SubjectDep
from alphaforge.core.symbols import get_basket, normalize_symbol, search_scrips
from alphaforge.models.api import BasketInfo, ScripInfo
from alphaforge.models.domain import Bar, Quote
from alphaforge.models.enums import Timeframe

router = APIRouter(prefix="/api/v1/market", tags=["market"])


@router.get("/bars", response_model=list[Bar])
async def get_bars(
    runtime: RuntimeDep,
    _user: SubjectDep,
    symbol: str,
    timeframe: Timeframe = Timeframe.D1,
    lookback: int = Query(default=120, ge=5, le=2000),
) -> list[Bar]:
    backend_sym = normalize_symbol(symbol)
    bars = await runtime.data.get_bars(backend_sym, timeframe=timeframe, lookback=lookback)
    await runtime.persist(bars=bars)
    return bars


@router.get("/quotes", response_model=list[Quote])
async def get_quotes(
    runtime: RuntimeDep,
    _user: SubjectDep,
    symbols: str = Query(default=""),
) -> list[Quote]:
    raw_symbols = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not raw_symbols:
        wanted = runtime.watchlist()
    else:
        wanted = [normalize_symbol(s) for s in raw_symbols if s]
    return await runtime.data.get_quotes(wanted)


@router.get("/search", response_model=list[ScripInfo])
async def search_market_scrips(
    _user: SubjectDep,
    q: str = Query(default="", description="Search query by symbol or company name"),
    limit: int = Query(default=15, ge=1, le=50),
) -> list[ScripInfo]:
    results = search_scrips(q, limit=limit)
    return [
        ScripInfo(
            symbol=s.symbol,
            name=s.name,
            exchange=s.exchange,
            sector=s.sector,
            backend_symbol=s.backend_symbol or (f"{s.symbol}.NS" if s.exchange == "NSE" else s.symbol),
        )
        for s in results
    ]


@router.get("/baskets", response_model=list[BasketInfo])
async def get_index_baskets(_user: SubjectDep) -> list[BasketInfo]:
    return [
        BasketInfo(
            id="nifty50",
            name="NIFTY 50",
            description="India's top 50 bluechip companies by market cap",
            count=50,
            symbols=get_basket("nifty50"),
        ),
        BasketInfo(
            id="nifty100",
            name="NIFTY 100",
            description="Top 100 large-cap Indian companies",
            count=80,
            symbols=get_basket("nifty100"),
        ),
        BasketInfo(
            id="nifty150",
            name="NIFTY MIDCAP 150",
            description="High-growth mid-cap market leaders",
            count=25,
            symbols=get_basket("nifty150"),
        ),
        BasketInfo(
            id="nifty250",
            name="NIFTY SMALLCAP 250",
            description="Emerging small-cap companies",
            count=20,
            symbols=get_basket("nifty250"),
        ),
        BasketInfo(
            id="us_tech",
            name="US TECH & INDICES",
            description="Leading US ETFs and Mega-cap Tech",
            count=10,
            symbols=get_basket("us_tech"),
        ),
    ]
