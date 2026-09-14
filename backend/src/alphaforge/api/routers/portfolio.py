from fastapi import APIRouter

from alphaforge.api.deps import RuntimeDep, SubjectDep
from alphaforge.models.api import (
    DashboardSnapshot,
    PortfolioBlendRequest,
    PortfolioBlendResponse,
    PortfolioResponse,
)

router = APIRouter(prefix="/api/v1", tags=["portfolio"])


@router.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio(runtime: RuntimeDep, _user: SubjectDep) -> PortfolioResponse:
    return PortfolioResponse(snapshot=runtime.portfolio.snapshot())


@router.get("/dashboard", response_model=DashboardSnapshot)
async def get_dashboard(runtime: RuntimeDep, _user: SubjectDep) -> DashboardSnapshot:
    await runtime.ensure_quotes()
    data = runtime.dashboard()
    return DashboardSnapshot.model_validate(data)


@router.post("/portfolio/blend", response_model=PortfolioBlendResponse)
async def blend_portfolio(
    body: PortfolioBlendRequest,
    runtime: RuntimeDep,
    _user: SubjectDep,
) -> PortfolioBlendResponse:
    return await runtime.allocator.blend(body)
