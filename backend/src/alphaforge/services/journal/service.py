from collections.abc import Sequence
from typing import Any

from alphaforge.core.logging import get_logger
from alphaforge.models.domain import JournalEntry
from alphaforge.models.enums import JournalEventType

log = get_logger(__name__)


class JournalService:
    """Append-only decision and order log. Entries are never updated or deleted."""

    def __init__(self) -> None:
        self._entries: list[JournalEntry] = []

    def append(
        self,
        event_type: JournalEventType,
        payload: dict[str, Any],
        *,
        correlation_id: str | None = None,
    ) -> JournalEntry:
        """Record an immutable journal event and return the entry."""
        entry = JournalEntry(
            event_type=event_type,
            payload=payload,
            correlation_id=correlation_id,
        )
        self._entries.append(entry)
        log.info(
            "journal.append",
            event_type=event_type.value,
            correlation_id=correlation_id,
            entry_id=entry.id,
        )
        return entry

    def list_entries(
        self,
        *,
        event_type: JournalEventType | None = None,
        limit: int = 100,
        before_id: str | None = None,
    ) -> Sequence[JournalEntry]:
        """Return newest-first entries, optionally filtered."""
        items = self._entries
        if event_type is not None:
            items = [e for e in items if e.event_type == event_type]
        if before_id is not None:
            idx = next((i for i, e in enumerate(items) if e.id == before_id), None)
            if idx is not None:
                items = items[:idx]
        return list(reversed(items[-limit:]))

    def all_entries(self) -> Sequence[JournalEntry]:
        return tuple(self._entries)

    def load(self, entries: Sequence[JournalEntry]) -> None:
        """Replace in-memory history from durable storage."""
        self._entries = list(entries)

    def __len__(self) -> int:
        return len(self._entries)
