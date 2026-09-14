"""Lightweight in-process event bus.

Strategies subscribe to symbol+timeframe events. When market data
arrives for a symbol, only strategies watching that symbol fire.
This replaces the monolithic 5-minute polling scheduler with
timeframe-aware, symbol-scoped dispatch.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable
from uuid import uuid4

from alphaforge.core.logging import get_logger
from alphaforge.models.enums import Timeframe

log = get_logger(__name__)

SubscriberId = str
Handler = Callable[["Event"], Awaitable[None]]


@dataclass(slots=True)
class Event:
    """An event emitted on the bus, consumed by subscribers."""

    id: str = field(default_factory=lambda: str(uuid4()))
    topic: str = ""
    symbol: str = ""
    timeframe: str = "1d"
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class Subscription:
    id: SubscriberId
    topics: list[str]
    symbols: list[str]
    handler: Handler


class EventBus:
    """In-process publish/subscribe event bus.

    Each strategy registers with the bus for the symbols it tracks.
    When new bars arrive, only the relevant strategies are invoked
    instead of running a monolithic cycle over everything.
    """

    def __init__(self) -> None:
        self._subscriptions: dict[SubscriberId, Subscription] = {}
        self._topic_index: dict[str, list[SubscriberId]] = defaultdict(list)
        self._symbol_topic_index: dict[str, dict[str, list[SubscriberId]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._stats: dict[str, int] = {"events_fired": 0, "handlers_invoked": 0}

    def subscribe(
        self,
        topics: list[str],
        symbols: list[str],
        handler: Handler,
        subscriber_id: str | None = None,
    ) -> SubscriberId:
        """Register a handler for one or more topics, scoped to symbols.

        Args:
            topics: Event topics to listen on (e.g. ["bars_updated", "quote_updated"]).
            symbols: Symbols to filter on. An empty list means all symbols.
            handler: Async callback invoked when an event matches.
            subscriber_id: Optional stable id; one is generated if omitted.
        """
        sid = subscriber_id or str(uuid4())
        sub = Subscription(id=sid, topics=list(topics), symbols=list(symbols), handler=handler)
        self._subscriptions[sid] = sub
        for topic in topics:
            self._topic_index[topic].append(sid)
            for sym in symbols:
                self._symbol_topic_index[sym][topic].append(sid)
        log.debug(
            "eventbus.subscribe",
            subscriber_id=sid,
            topics=topics,
            symbols=symbols,
        )
        return sid

    def unsubscribe(self, subscriber_id: SubscriberId) -> None:
        """Remove a subscriber and all its registrations."""
        sub = self._subscriptions.pop(subscriber_id, None)
        if sub is None:
            return
        for topic in sub.topics:
            tids = self._topic_index.get(topic, [])
            if subscriber_id in tids:
                tids.remove(subscriber_id)
            for sym in sub.symbols:
                sids = self._symbol_topic_index.get(sym, {}).get(topic, [])
                if subscriber_id in sids:
                    sids.remove(subscriber_id)
        log.debug("eventbus.unsubscribe", subscriber_id=subscriber_id)

    async def fire(self, event: Event) -> int:
        """Dispatch an event to all matching subscribers concurrently.

        Returns the number of handlers invoked.
        """
        self._stats["events_fired"] += 1
        seen: set[SubscriberId] = set()

        for sid in self._topic_index.get(event.topic, []):
            seen.add(sid)

        if event.symbol:
            for sid in self._symbol_topic_index.get(event.symbol, {}).get(event.topic, []):
                seen.add(sid)

        if not seen:
            return 0

        tasks: list[asyncio.Task[None]] = []
        for sid in seen:
            sub = self._subscriptions.get(sid)
            if sub is None:
                continue
            if sub.symbols and event.symbol and event.symbol not in sub.symbols:
                continue
            self._stats["handlers_invoked"] += 1
            tasks.append(asyncio.create_task(self._safe_invoke(sub, event)))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        return len(tasks)

    async def fire_and_forget(self, event: Event) -> None:
        """Fire an event without waiting for handlers to complete."""
        self._stats["events_fired"] += 1
        seen: set[SubscriberId] = set()
        for sid in self._topic_index.get(event.topic, []):
            seen.add(sid)
        if event.symbol:
            for sid in self._symbol_topic_index.get(event.symbol, {}).get(event.topic, []):
                seen.add(sid)
        for sid in seen:
            sub = self._subscriptions.get(sid)
            if sub is None:
                continue
            if sub.symbols and event.symbol and event.symbol not in sub.symbols:
                continue
            self._stats["handlers_invoked"] += 1
            asyncio.create_task(self._safe_invoke(sub, event))

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)

    def subscriber_count(self) -> int:
        return len(self._subscriptions)

    async def _safe_invoke(self, sub: Subscription, event: Event) -> None:
        try:
            await sub.handler(event)
        except Exception:
            log.exception(
                "eventbus.handler_failed",
                subscriber_id=sub.id,
                topic=event.topic,
            )
