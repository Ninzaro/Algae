from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from alphaforge.adapters.symbols import Instrument, parse_symbol, to_nse_tradingsymbol
from alphaforge.core.exceptions import BrokerError, ConfigurationError, DataError, NotFoundError
from alphaforge.core.logging import get_logger
from alphaforge.models.domain import AccountSnapshot, Bar, Fill, Order, Position
from alphaforge.models.enums import AssetClass, OrderSide, OrderStatus, OrderType, Timeframe

log = get_logger(__name__)

_ROOT = "https://apiconnect.angelone.in"
_SCRIP_MASTER = (
    "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
)

_INTERVAL = {
    Timeframe.M1: "ONE_MINUTE",
    Timeframe.M5: "FIVE_MINUTE",
    Timeframe.M15: "FIFTEEN_MINUTE",
    Timeframe.H1: "ONE_HOUR",
    Timeframe.D1: "ONE_DAY",
}

_LOOKBACK_DAYS = {
    Timeframe.M1: 5,
    Timeframe.M5: 30,
    Timeframe.M15: 30,
    Timeframe.H1: 120,
    Timeframe.D1: 2000,
}


class AngelOneClient:
    """Thin async SmartAPI REST client. Login is lazy and TOTP-based."""

    def __init__(
        self,
        api_key: str,
        client_code: str,
        password: str,
        totp_secret: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key or not client_code or not password or not totp_secret:
            raise ConfigurationError(
                "Angel One API key, client code, password, and TOTP secret are required"
            )
        self._api_key = api_key
        self._client_code = client_code
        self._password = password
        self._totp_secret = totp_secret
        self._jwt = ""
        self._http = httpx.AsyncClient(
            base_url=_ROOT,
            timeout=20.0,
            transport=transport,
        )
        self._instruments: dict[tuple[str, str], Instrument] = {}

    async def aclose(self) -> None:
        await self._http.aclose()

    def _headers(self, *, authed: bool = False) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "00:00:00:00:00:00",
            "X-PrivateKey": self._api_key,
        }
        if authed and self._jwt:
            headers["Authorization"] = f"Bearer {self._jwt}"
        return headers

    async def login(self) -> None:
        import pyotp

        totp = pyotp.TOTP(self._totp_secret).now()
        body = {"clientcode": self._client_code, "password": self._password, "totp": totp}
        response = await self._http.post(
            "/rest/auth/angelbroking/user/v1/loginByPassword",
            headers=self._headers(),
            json=body,
        )
        payload = _json(response)
        if not payload.get("status"):
            raise BrokerError(str(payload.get("message") or "Angel One login failed"))
        data = payload.get("data") or {}
        token = str(data.get("jwtToken") or "")
        if token.lower().startswith("bearer "):
            token = token[7:]
        if not token:
            raise BrokerError("Angel One login returned no jwtToken")
        self._jwt = token
        log.info("angelone.login")

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self._jwt:
            await self.login()
        response = await self._http.request(
            method,
            path,
            headers=self._headers(authed=True),
            json=json,
        )
        payload = _json(response)
        if not payload.get("status"):
            raise BrokerError(str(payload.get("message") or f"Angel One {path} failed"))
        data = payload.get("data")
        return data if isinstance(data, dict) else {"data": data}

    async def request_list(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> list[Any]:
        if not self._jwt:
            await self.login()
        response = await self._http.request(
            method,
            path,
            headers=self._headers(authed=True),
            json=json,
        )
        payload = _json(response)
        if not payload.get("status"):
            raise BrokerError(str(payload.get("message") or f"Angel One {path} failed"))
        data = payload.get("data")
        if data is None:
            return []
        if isinstance(data, list):
            return data
        return [data]

    async def load_instruments(self, rows: list[dict[str, Any]] | None = None) -> None:
        if rows is None:
            response = await self._http.get(_SCRIP_MASTER, timeout=60.0)
            response.raise_for_status()
            raw = response.json()
            if not isinstance(raw, list):
                raise DataError("Unexpected Angel One scrip master payload")
            rows = raw
        mapping: dict[tuple[str, str], Instrument] = {}
        for row in rows:
            exchange = str(row.get("exch_seg") or row.get("exchange") or "")
            symbol = str(row.get("symbol") or row.get("tradingsymbol") or "")
            token = str(row.get("token") or row.get("symboltoken") or "")
            if not exchange or not symbol or not token:
                continue
            if not symbol.endswith("-EQ"):
                continue
            root = symbol[: -len("-EQ")]
            mapping[(exchange.upper(), root.upper())] = Instrument(
                exchange=exchange.upper(),
                tradingsymbol=symbol,
                token=token,
                name=str(row.get("name") or root),
            )
        self._instruments = mapping
        log.info("angelone.scrips_loaded", n=len(mapping))

    def resolve(self, symbol: str) -> Instrument:
        exchange, root = parse_symbol(symbol)
        found = self._instruments.get((exchange, root))
        if found is None:
            raise NotFoundError(f"Unknown Angel One contract: {symbol}")
        return found

    def seed_instruments(self, instruments: list[Instrument]) -> None:
        self._instruments = {
            (item.exchange, parse_symbol(item.tradingsymbol)[1]): item for item in instruments
        }


class AngelOneBroker:
    """Live Angel One cash-equity broker. Never used unless TRADING_MODE=live."""

    name = "angelone"

    def __init__(self, client: AngelOneClient, *, product: str = "DELIVERY") -> None:
        self._client = client
        self._product = product

    async def submit_order(
        self, order: Order, *, ref_price: float | None = None
    ) -> tuple[Order, Fill | None]:
        if not self._client._instruments:
            await self._client.load_instruments()
        instrument = self._client.resolve(order.symbol)
        price = "0"
        order_type = "MARKET"
        if order.order_type == OrderType.LIMIT and order.limit_price:
            order_type = "LIMIT"
            price = str(order.limit_price)
        payload = {
            "variety": "NORMAL",
            "tradingsymbol": instrument.tradingsymbol,
            "symboltoken": instrument.token,
            "transactiontype": "BUY" if order.side == OrderSide.BUY else "SELL",
            "exchange": instrument.exchange,
            "ordertype": order_type,
            "producttype": self._product,
            "duration": "DAY",
            "price": price,
            "quantity": str(int(order.quantity)),
        }
        data = await self._client.request(
            "POST",
            "/rest/secure/angelbroking/order/v1/placeOrder",
            json=payload,
        )
        broker_id = str(data.get("orderid") or "")
        updated = order.model_copy(
            update={"broker_order_id": broker_id, "status": OrderStatus.SUBMITTED}
        )
        log.info("angelone.submitted", order_id=order.id, broker_id=broker_id)
        return updated, None

    async def cancel_order(self, order_id: str) -> Order:
        await self._client.request(
            "POST",
            "/rest/secure/angelbroking/order/v1/cancelOrder",
            json={"variety": "NORMAL", "orderid": order_id},
        )
        return Order(
            id=order_id,
            intent_id=order_id,
            strategy_id="",
            symbol="",
            side=OrderSide.BUY,
            quantity=0.0,
            status=OrderStatus.CANCELLED,
        )

    async def cancel_all(self) -> list[Order]:
        book = await self._client.request_list(
            "GET", "/rest/secure/angelbroking/order/v1/getOrderBook"
        )
        cancelled: list[Order] = []
        for row in book:
            if not isinstance(row, dict):
                continue
            status = str(row.get("status") or row.get("orderstatus") or "").lower()
            if status in {"complete", "cancelled", "rejected", "filled"}:
                continue
            order_id = str(row.get("orderid") or "")
            if order_id:
                cancelled.append(await self.cancel_order(order_id))
        return cancelled

    async def get_positions(self) -> list[Position]:
        rows = await self._client.request_list(
            "GET", "/rest/secure/angelbroking/order/v1/getPosition"
        )
        positions: list[Position] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            qty = float(row.get("netqty") or row.get("quantity") or 0)
            if qty == 0:
                continue
            avg = float(row.get("avgnetprice") or row.get("avgprice") or 0)
            mark = float(row.get("ltp") or avg)
            symbol = str(row.get("tradingsymbol") or row.get("symbolname") or "")
            positions.append(
                Position(
                    symbol=symbol.replace("-EQ", ".NS") if symbol.endswith("-EQ") else symbol,
                    quantity=qty,
                    avg_price=avg,
                    market_price=mark,
                    unrealized_pnl=float(row.get("unrealised") or 0),
                )
            )
        return positions

    async def get_account(self) -> AccountSnapshot:
        data = await self._client.request("GET", "/rest/secure/angelbroking/user/v1/getRMS")
        cash = float(data.get("availablecash") or data.get("net") or 0)
        equity = float(data.get("net") or cash)
        return AccountSnapshot(
            cash=cash,
            equity=equity,
            buying_power=cash,
            peak_equity=equity,
            daily_start_equity=equity,
        )


class AngelOneMarketData:
    """NSE/BSE historical candles and LTP via SmartAPI."""

    name = "angelone"

    def __init__(self, client: AngelOneClient) -> None:
        self._client = client

    async def get_bars(
        self,
        symbol: str,
        *,
        timeframe: Timeframe,
        lookback: int,
    ) -> list[Bar]:
        if not self._client._instruments:
            await self._client.load_instruments()
        instrument = self._client.resolve(symbol)
        days = max(_LOOKBACK_DAYS[timeframe], lookback + 5)
        end = datetime.now(UTC)
        start = end - timedelta(days=days)
        payload = {
            "exchange": instrument.exchange,
            "symboltoken": instrument.token,
            "interval": _INTERVAL[timeframe],
            "fromdate": start.strftime("%Y-%m-%d 09:15"),
            "todate": end.strftime("%Y-%m-%d 15:30"),
        }
        raw = await self._client.request(
            "POST",
            "/rest/secure/angelbroking/historical/v1/getCandleData",
            json=payload,
        )
        rows = raw.get("data") if "data" in raw else raw
        if not isinstance(rows, list):
            raise DataError(f"No Angel One candles for {symbol}")
        bars: list[Bar] = []
        for row in rows:
            if not isinstance(row, list) or len(row) < 6:
                continue
            ts = _parse_ts(row[0])
            bars.append(
                Bar(
                    symbol=symbol,
                    timestamp=ts,
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5] or 0),
                    timeframe=timeframe,
                    asset_class=AssetClass.EQUITY,
                )
            )
        return bars[-lookback:]

    async def latest_price(self, symbol: str) -> float:
        if not self._client._instruments:
            await self._client.load_instruments()
        instrument = self._client.resolve(symbol)
        data = await self._client.request(
            "POST",
            "/rest/secure/angelbroking/order/v1/getLtpData",
            json={
                "exchange": instrument.exchange,
                "tradingsymbol": instrument.tradingsymbol,
                "symboltoken": instrument.token,
            },
        )
        inner = data.get("data") if "data" in data and isinstance(data.get("data"), dict) else data
        price = float((inner or {}).get("ltp") or 0)
        if price <= 0:
            raise DataError(f"No Angel One LTP for {symbol}")
        return price


def _json(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise BrokerError(f"Angel One returned non-JSON ({response.status_code})") from exc
    if not isinstance(payload, dict):
        raise BrokerError("Angel One returned an unexpected payload")
    return payload


def _parse_ts(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    text = str(value)
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            parsed = datetime.strptime(text.replace("Z", ""), fmt)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            continue
    return datetime.now(UTC)


def demo_instrument(symbol: str, token: str = "2885") -> Instrument:
    exchange, root = parse_symbol(symbol)
    return Instrument(
        exchange=exchange, tradingsymbol=to_nse_tradingsymbol(root), token=token, name=root
    )
