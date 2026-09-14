from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Instrument:
    exchange: str
    tradingsymbol: str
    token: str
    name: str = ""


def parse_symbol(symbol: str) -> tuple[str, str]:
    """Split a user symbol into (exchange, root). RELIANCE.NS → (NSE, RELIANCE)."""
    raw = symbol.strip().upper()
    if raw.endswith("-EQ"):
        return "NSE", raw[: -len("-EQ")]
    if "." in raw:
        root, suffix = raw.rsplit(".", 1)
        exchange = {"NS": "NSE", "BO": "BSE", "NSE": "NSE", "BSE": "BSE"}.get(suffix, "NSE")
        return exchange, root
    return "NSE", raw


def to_nse_tradingsymbol(root: str) -> str:
    return f"{root}-EQ"
