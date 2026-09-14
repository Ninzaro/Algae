from fastapi import APIRouter, Query

from alphaforge.api.deps import RuntimeDep, SubjectDep
from alphaforge.models.api import JournalPage
from alphaforge.models.enums import JournalEventType

router = APIRouter(prefix="/api/v1/journal", tags=["journal"])


@router.get("", response_model=JournalPage)
async def list_journal(
    runtime: RuntimeDep,
    _user: SubjectDep,
    event_type: JournalEventType | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> JournalPage:
    items = runtime.journal.list_entries(event_type=event_type, limit=limit)
    return JournalPage(items=list(items))
