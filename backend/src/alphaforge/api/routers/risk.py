from fastapi import APIRouter

from alphaforge.api.deps import RuntimeDep, SubjectDep
from alphaforge.models.api import KillSwitchRequest, KillSwitchResponse
from alphaforge.services.alerts import AlertService

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])


@router.get("/kill-switch", response_model=KillSwitchResponse)
async def get_kill_switch(runtime: RuntimeDep, _user: SubjectDep) -> KillSwitchResponse:
    return KillSwitchResponse(
        active=runtime.risk.kill_switch_active,
        reason=runtime.risk.kill_reason,
    )


@router.post("/kill-switch", response_model=KillSwitchResponse)
async def set_kill_switch(
    body: KillSwitchRequest,
    runtime: RuntimeDep,
    _user: SubjectDep,
) -> KillSwitchResponse:
    cancelled = 0
    if body.active:
        cancelled = await runtime.execution.engage_kill_switch(body.reason, flatten=body.flatten)
        alerts = AlertService(runtime.settings)
        await alerts.send(f"AlphaForge kill switch ENGAGED: {body.reason or 'no reason'}")
    else:
        runtime.risk.set_kill_switch(False, body.reason)
    await runtime.persist()
    await runtime.publish("kill_switch")
    return KillSwitchResponse(
        active=runtime.risk.kill_switch_active,
        reason=runtime.risk.kill_reason,
        cancelled_orders=cancelled,
    )
