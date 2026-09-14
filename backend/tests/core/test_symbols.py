"""Unit tests for symbol normalizer, scrip search, and index constituent baskets."""

from alphaforge.core.symbols import get_basket, normalize_symbol, search_scrips


def test_normalize_symbol() -> None:
    assert normalize_symbol("RELIANCE") == "RELIANCE.NS"
    assert normalize_symbol("TCS") == "TCS.NS"
    assert normalize_symbol("INFY.NS") == "INFY.NS"
    assert normalize_symbol("SPY") == "SPY"
    assert normalize_symbol("QQQ") == "QQQ"
    assert normalize_symbol("AAPL") == "AAPL"
    assert normalize_symbol("") == ""


def test_search_scrips() -> None:
    res_rel = search_scrips("RELIANCE")
    assert len(res_rel) >= 1
    assert res_rel[0].symbol == "RELIANCE"
    assert res_rel[0].exchange == "NSE"

    res_tata = search_scrips("TATA")
    assert len(res_tata) >= 2
    symbols = [s.symbol for s in res_tata]
    assert "TCS" in symbols or "TATAMOTORS" in symbols or "TATASTEEL" in symbols

    res_spy = search_scrips("SPY")
    assert any(s.symbol == "SPY" for s in res_spy)


def test_get_baskets() -> None:
    nifty50 = get_basket("nifty50")
    assert len(nifty50) == 50
    assert "RELIANCE.NS" in nifty50
    assert "HDFCBANK.NS" in nifty50

    nifty100 = get_basket("nifty100")
    assert len(nifty100) >= 80

    midcap = get_basket("midcap")
    assert len(midcap) >= 20

    us = get_basket("us_tech")
    assert "SPY" in us
    assert "AAPL" in us
