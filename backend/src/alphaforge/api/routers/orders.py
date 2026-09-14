from fastapi import APIRouter

from alphaforge.api.deps import RuntimeDep, SubjectDep
from alphaforge.models.domain import Fill, Order

router = APIRouter(prefix="/api/v1", tags=["orders"])


@router.get("/orders", response_model=list[Order])
async def list_orders(runtime: RuntimeDep, _user: SubjectDep) -> list[Order]:
    return runtime.execution.orders


@router.get("/fills", response_model=list[Fill])
async def list_fills(runtime: RuntimeDep, _user: SubjectDep) -> list[Fill]:
    return runtime.execution.fills
