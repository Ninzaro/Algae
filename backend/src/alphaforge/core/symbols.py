"""Comprehensive scrip database, index constituent baskets (Nifty 50, 100, 150, 250), and symbol normalization."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class Scrip:
    symbol: str  # Standard clean symbol, e.g. RELIANCE, TCS, SPY
    name: str  # Full company name, e.g. Reliance Industries Ltd.
    exchange: Literal["NSE", "BSE", "US"]
    sector: str = ""
    backend_symbol: str = ""  # Symbol passed to data provider (e.g. RELIANCE.NS, SPY)

    def to_dict(self) -> dict[str, str]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "exchange": self.exchange,
            "sector": self.sector,
            "backend_symbol": self.backend_symbol or (f"{self.symbol}.NS" if self.exchange == "NSE" else self.symbol),
        }


# Curated constituent master for major indices
NIFTY_50_DATA: list[tuple[str, str, str]] = [
    ("RELIANCE", "Reliance Industries Ltd.", "Energy"),
    ("TCS", "Tata Consultancy Services Ltd.", "Technology"),
    ("HDFCBANK", "HDFC Bank Ltd.", "Financials"),
    ("ICICIBANK", "ICICI Bank Ltd.", "Financials"),
    ("INFY", "Infosys Ltd.", "Technology"),
    ("BHARTIARTL", "Bharti Airtel Ltd.", "Telecom"),
    ("ITC", "ITC Ltd.", "Consumer Goods"),
    ("SBIN", "State Bank of India", "Financials"),
    ("LICI", "Life Insurance Corporation", "Financials"),
    ("HINDUNILVR", "Hindustan Unilever Ltd.", "Consumer Goods"),
    ("LT", "Larsen & Toubro Ltd.", "Industrials"),
    ("BAJFINANCE", "Bajaj Finance Ltd.", "Financials"),
    ("MARUTI", "Maruti Suzuki India Ltd.", "Automobile"),
    ("HCLTECH", "HCL Technologies Ltd.", "Technology"),
    ("SUNPHARMA", "Sun Pharmaceutical Industries", "Healthcare"),
    ("TATAMOTORS", "Tata Motors Ltd.", "Automobile"),
    ("ONGC", "Oil & Natural Gas Corporation", "Energy"),
    ("NTPC", "NTPC Ltd.", "Utilities"),
    ("KOTAKBANK", "Kotak Mahindra Bank Ltd.", "Financials"),
    ("AXISBANK", "Axis Bank Ltd.", "Financials"),
    ("TITAN", "Titan Company Ltd.", "Consumer Goods"),
    ("ADANIENT", "Adani Enterprises Ltd.", "Diversified"),
    ("ADANIPORTS", "Adani Ports & SEZ Ltd.", "Industrials"),
    ("COALINDIA", "Coal India Ltd.", "Energy"),
    ("POWERGRID", "Power Grid Corp of India", "Utilities"),
    ("WIPRO", "Wipro Ltd.", "Technology"),
    ("ULTRACEMCO", "UltraTech Cement Ltd.", "Materials"),
    ("ASIANPAINT", "Asian Paints Ltd.", "Consumer Goods"),
    ("M&M", "Mahindra & Mahindra Ltd.", "Automobile"),
    ("BAJAJFINSV", "Bajaj Finserv Ltd.", "Financials"),
    ("NESTLEIND", "Nestle India Ltd.", "Consumer Goods"),
    ("JSWSTEEL", "JSW Steel Ltd.", "Materials"),
    ("TATASTEEL", "Tata Steel Ltd.", "Materials"),
    ("GRASIM", "Grasim Industries Ltd.", "Materials"),
    ("TECHM", "Tech Mahindra Ltd.", "Technology"),
    ("CIPLA", "Cipla Ltd.", "Healthcare"),
    ("HINDALCO", "Hindalco Industries Ltd.", "Materials"),
    ("EICHERMOT", "Eicher Motors Ltd.", "Automobile"),
    ("DRREDDY", "Dr. Reddy's Laboratories", "Healthcare"),
    ("TATACONSUM", "Tata Consumer Products Ltd.", "Consumer Goods"),
    ("HEROMOTOCO", "Hero MotoCorp Ltd.", "Automobile"),
    ("DIVISLAB", "Divi's Laboratories Ltd.", "Healthcare"),
    ("APOLLOHOSP", "Apollo Hospitals Enterprise", "Healthcare"),
    ("BRITANNIA", "Britannia Industries Ltd.", "Consumer Goods"),
    ("SBILIFE", "SBI Life Insurance Co.", "Financials"),
    ("HDFCLIFE", "HDFC Life Insurance Co.", "Financials"),
    ("BAJAJ-AUTO", "Bajaj Auto Ltd.", "Automobile"),
    ("INDUSINDBK", "IndusInd Bank Ltd.", "Financials"),
    ("BPCL", "Bharat Petroleum Corp Ltd.", "Energy"),
    ("SHRIRAMFIN", "Shriram Finance Ltd.", "Financials"),
]

NIFTY_NEXT_50_DATA: list[tuple[str, str, str]] = [
    ("BEL", "Bharat Electronics Ltd.", "Industrials"),
    ("HAL", "Hindustan Aeronautics Ltd.", "Industrials"),
    ("TRENT", "Trent Ltd.", "Consumer Goods"),
    ("ZOMATO", "Zomato Ltd.", "Technology"),
    ("VBL", "Varun Beverages Ltd.", "Consumer Goods"),
    ("JIOFIN", "Jio Financial Services Ltd.", "Financials"),
    ("CHOLAFIN", "Cholamandalam Investment", "Financials"),
    ("VEDL", "Vedanta Ltd.", "Materials"),
    ("IOC", "Indian Oil Corporation Ltd.", "Energy"),
    ("DLF", "DLF Ltd.", "Real Estate"),
    ("GAIL", "GAIL (India) Ltd.", "Energy"),
    ("SIEMENS", "Siemens Ltd.", "Industrials"),
    ("ABB", "ABB India Ltd.", "Industrials"),
    ("INDIGO", "InterGlobe Aviation Ltd.", "Industrials"),
    ("PIDILITIND", "Pidilite Industries Ltd.", "Materials"),
    ("BANKBARODA", "Bank of Baroda", "Financials"),
    ("PNB", "Punjab National Bank", "Financials"),
    ("TVSMOTOR", "TVS Motor Company Ltd.", "Automobile"),
    ("GODREJCP", "Godrej Consumer Products Ltd.", "Consumer Goods"),
    ("HAVELLS", "Havells India Ltd.", "Consumer Goods"),
    ("DABUR", "Dabur India Ltd.", "Consumer Goods"),
    ("AMBUJACEM", "Ambuja Cements Ltd.", "Materials"),
    ("SHREECEM", "Shree Cement Ltd.", "Materials"),
    ("CANBK", "Canara Bank", "Financials"),
    ("UNIONBANK", "Union Bank of India", "Financials"),
    ("POLYCAB", "Polycab India Ltd.", "Industrials"),
    ("MOTHERSON", "Samvardhana Motherson Int.", "Automobile"),
    ("NAUKRI", "Info Edge (India) Ltd.", "Technology"),
    ("IRCTC", "IRCTC Ltd.", "Services"),
    ("BOSCHLTD", "Bosch Ltd.", "Automobile"),
]

NIFTY_MIDCAP_150_SAMPLE: list[tuple[str, str, str]] = [
    ("PERSISTENT", "Persistent Systems Ltd.", "Technology"),
    ("COFORGE", "Coforge Ltd.", "Technology"),
    ("MPHASIS", "Mphasis Ltd.", "Technology"),
    ("LTTS", "L&T Technology Services", "Technology"),
    ("TATACOMM", "Tata Communications Ltd.", "Telecom"),
    ("FEDERALBNK", "Federal Bank Ltd.", "Financials"),
    ("IDFCFIRSTB", "IDFC First Bank Ltd.", "Financials"),
    ("AUBANK", "AU Small Finance Bank", "Financials"),
    ("MAXHEALTH", "Max Healthcare Institute", "Healthcare"),
    ("FORTIS", "Fortis Healthcare Ltd.", "Healthcare"),
    ("LUPIN", "Lupin Ltd.", "Healthcare"),
    ("AUROPHARMA", "Aurobindo Pharma Ltd.", "Healthcare"),
    ("VOLTAS", "Voltas Ltd.", "Consumer Goods"),
    ("PAGEIND", "Page Industries Ltd.", "Consumer Goods"),
    ("BATAINDIA", "Bata India Ltd.", "Consumer Goods"),
    ("JUBLFOOD", "Jubilant FoodWorks Ltd.", "Consumer Goods"),
    ("OBEROIRLTY", "Oberoi Realty Ltd.", "Real Estate"),
    ("GODREJPROP", "Godrej Properties Ltd.", "Real Estate"),
    ("PRESTIGE", "Prestige Estates Projects", "Real Estate"),
    ("PHOENIXLTD", "The Phoenix Mills Ltd.", "Real Estate"),
    ("ASTRAL", "Astral Ltd.", "Industrials"),
    ("SUPREMEIND", "Supreme Industries Ltd.", "Industrials"),
    ("KAYNES", "Kaynes Technology India", "Technology"),
    ("DIXON", "Dixon Technologies Ltd.", "Technology"),
    ("SUZLON", "Suzlon Energy Ltd.", "Utilities"),
]

NIFTY_SMALLCAP_250_SAMPLE: list[tuple[str, str, str]] = [
    ("CDSL", "Central Depository Services", "Financials"),
    ("BSE", "BSE Ltd.", "Financials"),
    ("ANGELONE", "Angel One Ltd.", "Financials"),
    ("MCX", "Multi Commodity Exchange", "Financials"),
    ("CAMS", "Computer Age Management", "Financials"),
    ("KIMS", "Krishna Institute of Medical", "Healthcare"),
    ("ERIS", "Eris Lifesciences Ltd.", "Healthcare"),
    ("GLENMARK", "Glenmark Pharmaceuticals", "Healthcare"),
    ("PVRINOX", "PVR INOX Ltd.", "Media"),
    ("ROUTE", "Route Mobile Ltd.", "Technology"),
    ("HAPPSTMNDS", "Happiest Minds Technologies", "Technology"),
    ("CYIENT", "Cyient Ltd.", "Technology"),
    ("SONACOMS", "Sona BLW Precision", "Automobile"),
    ("RADICO", "Radico Khaitan Ltd.", "Consumer Goods"),
    ("REDINGTON", "Redington Ltd.", "Services"),
    ("METROPOLIS", "Metropolis Healthcare", "Healthcare"),
    ("CENTURYPLY", "Century Plyboards Ltd.", "Materials"),
    ("JBCHEPHARM", "JB Chemicals & Pharma", "Healthcare"),
    ("AMBER", "Amber Enterprises India", "Industrials"),
    ("KPITTECH", "KPIT Technologies Ltd.", "Technology"),
]

US_MARKET_DATA: list[tuple[str, str, str]] = [
    ("SPY", "SPDR S&P 500 ETF Trust", "Index ETF"),
    ("QQQ", "Invesco QQQ Trust (Nasdaq 100)", "Index ETF"),
    ("AAPL", "Apple Inc.", "Technology"),
    ("MSFT", "Microsoft Corporation", "Technology"),
    ("NVDA", "NVIDIA Corporation", "Technology"),
    ("GOOGL", "Alphabet Inc. (Google)", "Technology"),
    ("AMZN", "Amazon.com Inc.", "Consumer Discretionary"),
    ("META", "Meta Platforms Inc.", "Technology"),
    ("TSLA", "Tesla Inc.", "Automobile"),
    ("AMD", "Advanced Micro Devices", "Technology"),
]


# Master Registry
ALL_SCRIPS: list[Scrip] = []

for sym, name, sec in NIFTY_50_DATA:
    ALL_SCRIPS.append(Scrip(symbol=sym, name=name, exchange="NSE", sector=sec, backend_symbol=f"{sym}.NS"))

for sym, name, sec in NIFTY_NEXT_50_DATA:
    ALL_SCRIPS.append(Scrip(symbol=sym, name=name, exchange="NSE", sector=sec, backend_symbol=f"{sym}.NS"))

for sym, name, sec in NIFTY_MIDCAP_150_SAMPLE:
    ALL_SCRIPS.append(Scrip(symbol=sym, name=name, exchange="NSE", sector=sec, backend_symbol=f"{sym}.NS"))

for sym, name, sec in NIFTY_SMALLCAP_250_SAMPLE:
    ALL_SCRIPS.append(Scrip(symbol=sym, name=name, exchange="NSE", sector=sec, backend_symbol=f"{sym}.NS"))

for sym, name, sec in US_MARKET_DATA:
    ALL_SCRIPS.append(Scrip(symbol=sym, name=name, exchange="US", sector=sec, backend_symbol=sym))


SCRIP_BY_SYMBOL: dict[str, Scrip] = {s.symbol.upper(): s for s in ALL_SCRIPS}


def normalize_symbol(user_input: str) -> str:
    """Resolve user-typed symbol (e.g. 'RELIANCE', 'TCS', 'SPY') into backend symbol (e.g. 'RELIANCE.NS', 'SPY')."""
    raw = user_input.strip().upper()
    if not raw:
        return ""
    if raw.endswith(".NS") or raw.endswith(".BO"):
        return raw

    # Check scrip dictionary
    if raw in SCRIP_BY_SYMBOL:
        return SCRIP_BY_SYMBOL[raw].backend_symbol

    # Default heuristic: if 1-5 letters and matches US style, leave as is, else append .NS for Indian equity
    if raw in {"SPY", "QQQ", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD"}:
        return raw
    return f"{raw}.NS"


def search_scrips(query: str, limit: int = 15) -> list[Scrip]:
    """Search scrips by symbol, company name, or sector."""
    q = query.strip().upper()
    if not q:
        return ALL_SCRIPS[:limit]

    exact_matches: list[Scrip] = []
    prefix_matches: list[Scrip] = []
    sub_matches: list[Scrip] = []

    for s in ALL_SCRIPS:
        sym = s.symbol.upper()
        name = s.name.upper()
        if sym == q:
            exact_matches.append(s)
        elif sym.startswith(q):
            prefix_matches.append(s)
        elif q in sym or q in name or q in s.sector.upper():
            sub_matches.append(s)

    combined = exact_matches + prefix_matches + sub_matches
    return combined[:limit]


def get_basket(basket_id: str) -> list[str]:
    """Return symbol list for standard index baskets."""
    b = basket_id.lower().replace("-", "_").replace(" ", "_")
    if b in {"nifty50", "nifty_50"}:
        return [f"{sym}.NS" for sym, _, _ in NIFTY_50_DATA]
    if b in {"nifty100", "nifty_100"}:
        return [f"{sym}.NS" for sym, _, _ in NIFTY_50_DATA + NIFTY_NEXT_50_DATA]
    if b in {"nifty150", "nifty_150", "nifty_midcap_150", "midcap"}:
        return [f"{sym}.NS" for sym, _, _ in NIFTY_MIDCAP_150_SAMPLE]
    if b in {"nifty250", "nifty_250", "nifty_smallcap_250", "smallcap"}:
        return [f"{sym}.NS" for sym, _, _ in NIFTY_SMALLCAP_250_SAMPLE]
    if b in {"us_tech", "us", "nasdaq"}:
        return [sym for sym, _, _ in US_MARKET_DATA]
    return [f"{sym}.NS" for sym, _, _ in NIFTY_50_DATA[:10]]
