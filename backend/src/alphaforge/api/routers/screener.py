from fastapi import APIRouter

from alphaforge.api.deps import RuntimeDep, SubjectDep
from alphaforge.models.api import ScreenerRequest, ScreenerResponse

router = APIRouter(prefix="/api/v1/screener", tags=["screener"])


@router.post("/scan", response_model=ScreenerResponse)
async def scan_market(
    body: ScreenerRequest,
    runtime: RuntimeDep,
    _user: SubjectDep,
) -> ScreenerResponse:
    return await runtime.screener.scan(body)
