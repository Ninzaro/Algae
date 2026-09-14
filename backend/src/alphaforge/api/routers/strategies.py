from fastapi import APIRouter

from alphaforge.api.deps import RuntimeDep, SubjectDep
from alphaforge.models.api import StrategyToggleRequest, StrategyView

router = APIRouter(prefix="/api/v1/strategies", tags=["strategies"])


@router.get("", response_model=list[StrategyView])
async def list_strategies(runtime: RuntimeDep, _user: SubjectDep) -> list[StrategyView]:
    return [StrategyView.model_validate(m.model_dump()) for m in runtime.registry.list_meta()]


@router.post("/{strategy_id}/toggle", response_model=StrategyView)
async def toggle_strategy(
    strategy_id: str,
    body: StrategyToggleRequest,
    runtime: RuntimeDep,
    _user: SubjectDep,
) -> StrategyView:
    runtime.registry.set_enabled(strategy_id, body.enabled)
    runtime.refresh_event_subscriptions()
    await runtime.persist()
    await runtime.publish("strategy")
    meta = next(m for m in runtime.registry.list_meta() if m.id == strategy_id)
    return StrategyView.model_validate(meta.model_dump())


@router.post("/cycle")
async def run_cycle(runtime: RuntimeDep, _user: SubjectDep) -> dict[str, int]:
    signals = await runtime.run_cycle()
    return {"signals": len(signals)}
