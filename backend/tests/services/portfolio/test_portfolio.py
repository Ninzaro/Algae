from alphaforge.models.domain import Fill
from alphaforge.models.enums import OrderSide
from alphaforge.services.portfolio.service import PortfolioService


def test_apply_buy_then_mark() -> None:
    book = PortfolioService(100_000.0)
    book.apply_fill(Fill(order_id="1", symbol="SPY", side=OrderSide.BUY, quantity=10, price=100.0))
    book.mark({"SPY": 110.0})
    snap = book.snapshot()
    pos = snap.position_for("SPY")
    assert pos is not None
    assert pos.quantity == 10
    assert abs(pos.unrealized_pnl - 100.0) < 1e-6
    assert abs(snap.account.equity - 100_100.0) < 1e-6


def test_round_trip_realizes_pnl() -> None:
    book = PortfolioService(100_000.0)
    book.apply_fill(Fill(order_id="1", symbol="SPY", side=OrderSide.BUY, quantity=10, price=100.0))
    book.apply_fill(Fill(order_id="2", symbol="SPY", side=OrderSide.SELL, quantity=10, price=110.0))
    snap = book.snapshot()
    assert snap.position_for("SPY") is None
    assert abs(snap.account.cash - 100_100.0) < 1e-6


def test_partial_close_avg_price() -> None:
    book = PortfolioService(100_000.0)
    book.apply_fill(Fill(order_id="1", symbol="SPY", side=OrderSide.BUY, quantity=10, price=100.0))
    book.apply_fill(Fill(order_id="2", symbol="SPY", side=OrderSide.SELL, quantity=4, price=120.0))
    pos = book.snapshot().position_for("SPY")
    assert pos is not None
    assert pos.quantity == 6
    assert abs(pos.avg_price - 100.0) < 1e-6
    assert abs(pos.realized_pnl - 80.0) < 1e-6
