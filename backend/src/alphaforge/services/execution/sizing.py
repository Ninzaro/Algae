from math import sqrt

from alphaforge.models.domain import Bar, OrderIntent, PortfolioSnapshot, Signal
from alphaforge.models.enums import OrderSide, SignalSide


def annualized_vol(closes: list[float], periods_per_year: int = 252) -> float:
    """Close-to-close realized volatility. Returns 0 when undefined."""
    if len(closes) < 3:
        return 0.0
    rets = [(closes[i] / closes[i - 1]) - 1.0 for i in range(1, len(closes)) if closes[i - 1] > 0]
    if len(rets) < 2:
        return 0.0
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return sqrt(max(var, 0.0) * periods_per_year)


def size_from_signal(
    signal: Signal,
    portfolio: PortfolioSnapshot,
    bars: list[Bar],
    *,
    target_vol: float,
    kelly_fraction: float,
    max_position_pct: float,
    ref_price: float | None = None,
) -> OrderIntent | None:
    """Convert a pure signal into an OrderIntent using vol targeting and fractional Kelly.

    Returns None when the signal is flat and there is no position, or when size rounds to 0.
    """
    price = ref_price if ref_price and ref_price > 0 else (bars[-1].close if bars else 0.0)
    if price <= 0 or portfolio.account.equity <= 0:
        return None

    existing = portfolio.position_for(signal.symbol)
    existing_qty = existing.quantity if existing else 0.0

    if signal.side == SignalSide.FLAT:
        if abs(existing_qty) < 1e-12:
            return None
        side = OrderSide.SELL if existing_qty > 0 else OrderSide.BUY
        return OrderIntent(
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            side=side,
            quantity=abs(existing_qty),
            signal_id=signal.id,
            reason="flatten",
            metadata={"ref_price": price, "signal_side": signal.side.value},
        )

    closes = [b.close for b in bars]
    vol = annualized_vol(closes)
    if vol <= 0:
        vol = target_vol
    raw_weight = (target_vol / vol) * kelly_fraction * max(abs(signal.strength), 0.25)
    weight = min(raw_weight, max_position_pct / 100.0)
    target_notional = portfolio.account.equity * weight
    target_qty = target_notional / price

    if signal.side == SignalSide.BUY:
        delta = target_qty - max(existing_qty, 0.0)
        if delta <= 1e-8:
            return None
        side = OrderSide.BUY
        qty = delta
    else:
        if existing_qty <= 0:
            return None
        side = OrderSide.SELL
        qty = existing_qty

    qty = _round_qty(qty, signal.symbol)
    if qty <= 0:
        return None

    return OrderIntent(
        strategy_id=signal.strategy_id,
        symbol=signal.symbol,
        side=side,
        quantity=qty,
        signal_id=signal.id,
        reason=signal.reason,
        metadata={
            "ref_price": price,
            "vol": vol,
            "weight": weight,
            "signal_side": signal.side.value,
        },
    )


def _round_qty(qty: float, symbol: str) -> float:
    if symbol.endswith("USD") or "/" in symbol:
        return max(round(qty, 6), 0.0)
    return float(max(int(qty), 0))
