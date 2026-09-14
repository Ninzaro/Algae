from alphaforge.models.enums import JournalEventType
from alphaforge.services.journal.service import JournalService


def test_append_only_and_newest_first() -> None:
    journal = JournalService()
    a = journal.append(JournalEventType.SIGNAL, {"n": 1})
    b = journal.append(JournalEventType.ORDER_FILLED, {"n": 2})
    listed = journal.list_entries()
    assert [e.id for e in listed] == [b.id, a.id]
    assert len(journal) == 2


def test_filter_by_type() -> None:
    journal = JournalService()
    journal.append(JournalEventType.SIGNAL, {})
    journal.append(JournalEventType.KILL_SWITCH, {"active": True})
    items = journal.list_entries(event_type=JournalEventType.KILL_SWITCH)
    assert len(items) == 1
    assert items[0].event_type == JournalEventType.KILL_SWITCH
