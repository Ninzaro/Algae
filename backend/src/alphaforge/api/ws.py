from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from alphaforge.core.exceptions import AuthenticationError
from alphaforge.core.logging import get_logger
from alphaforge.core.security import decode_token

log = get_logger(__name__)

router = APIRouter()


class Hub:
    def __init__(self) -> None:
        self._clients: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._clients:
            self._clients.remove(ws)

    async def broadcast(self, event: str, payload: dict[str, Any]) -> None:
        stale: list[WebSocket] = []
        message = {"event": event, "payload": payload}
        for client in self._clients:
            try:
                await client.send_json(message)
            except Exception:
                stale.append(client)
        for client in stale:
            self.disconnect(client)


hub = Hub()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    from alphaforge.api.deps import get_runtime, get_settings_dep

    token = ws.query_params.get("token")
    if not token:
        await ws.close(code=4401)
        return
    try:
        payload = decode_token(token, get_settings_dep())
    except (AuthenticationError, RuntimeError):
        await ws.close(code=4401)
        return
    if payload.get("type") != "access":
        await ws.close(code=4401)
        return

    await hub.connect(ws)
    try:
        runtime = get_runtime()
        await ws.send_json({"event": "hello", "payload": runtime.dashboard_payload()})
    except RuntimeError:
        log.warning("ws.runtime_unbound")
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        hub.disconnect(ws)
    except Exception:
        log.exception("ws.error")
        hub.disconnect(ws)
