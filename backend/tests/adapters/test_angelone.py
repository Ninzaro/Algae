from alphaforge.adapters.angelone import AngelOneBroker, AngelOneClient, demo_instrument
from alphaforge.adapters.symbols import parse_symbol, to_nse_tradingsymbol
from alphaforge.models.domain import Order
from alphaforge.models.enums import OrderSide, OrderStatus, OrderType


def test_parse_indian_symbols() -> None:
    assert parse_symbol("RELIANCE.NS") == ("NSE", "RELIANCE")
    assert parse_symbol("INFY.BO") == ("BSE", "INFY")
    assert parse_symbol("HDFCBANK-EQ") == ("NSE", "HDFCBANK")
    assert parse_symbol("tcs") == ("NSE", "TCS")
    assert to_nse_tradingsymbol("RELIANCE") == "RELIANCE-EQ"


def test_resolve_seeded_contract() -> None:
    client = AngelOneClient("k", "c", "p", "JBSWY3DPEHPK3PXP")
    client.seed_instruments([demo_instrument("RELIANCE.NS", "2885")])
    found = client.resolve("RELIANCE.NS")
    assert found.token == "2885"
    assert found.tradingsymbol == "RELIANCE-EQ"
    assert found.exchange == "NSE"


async def test_place_order_payload(monkeypatch: object) -> None:
    client = AngelOneClient("k", "c", "p", "JBSWY3DPEHPK3PXP")
    client.seed_instruments([demo_instrument("RELIANCE.NS", "2885")])
    captured: dict[str, object] = {}

    async def fake_request(
        method: str, path: str, *, json: dict[str, object] | None = None
    ) -> dict[str, object]:
        captured["method"] = method
        captured["path"] = path
        captured["json"] = json
        return {"orderid": "ANGEL-1"}

    client.request = fake_request  # type: ignore[method-assign]
    broker = AngelOneBroker(client)
    order = Order(
        intent_id="i",
        strategy_id="sma-crossover",
        symbol="RELIANCE.NS",
        side=OrderSide.BUY,
        quantity=2,
        order_type=OrderType.MARKET,
        status=OrderStatus.SUBMITTED,
    )
    updated, fill = await broker.submit_order(order)
    assert fill is None
    assert updated.broker_order_id == "ANGEL-1"
    body = captured["json"]
    assert isinstance(body, dict)
    assert body["tradingsymbol"] == "RELIANCE-EQ"
    assert body["symboltoken"] == "2885"
    assert body["transactiontype"] == "BUY"
    assert body["producttype"] == "DELIVERY"
    assert body["quantity"] == "2"
