from __future__ import annotations

import threading

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse

from gcp_dash.config import Settings
from gcp_dash.cpu_load import CpuLoad
from gcp_dash.deps import get_cpu_load, get_runtime_state, get_settings
from gcp_dash.state import RuntimeState

router = APIRouter(tags=["controls"])

CRASH_DELAY_SECONDS = 0.5


def require_controls_enabled(settings: Settings = Depends(get_settings)) -> None:
    if not settings.controls_enabled:
        raise HTTPException(status_code=403, detail="controls are disabled (CONTROLS_ENABLED=false)")


def state_payload(request: Request) -> dict:
    """Current control state; extended with CPU load info in Task 5."""
    payload = request.app.state.runtime.snapshot()
    payload["controls_enabled"] = request.app.state.settings.controls_enabled
    cpu = getattr(request.app.state, "cpu_load", None)
    payload["cpu_load"] = cpu.status() if cpu is not None else {"active": False, "workers": 0}
    return payload


@router.get("/api/state")
def api_state(request: Request) -> dict:
    return state_payload(request)


@router.post("/controls/liveness", dependencies=[Depends(require_controls_enabled)])
def set_liveness(
    request: Request,
    enabled: bool = Form(...),
    state: RuntimeState = Depends(get_runtime_state),
):
    state.set_live(enabled)
    return JSONResponse(state_payload(request))


@router.post("/controls/readiness", dependencies=[Depends(require_controls_enabled)])
def set_readiness(
    request: Request,
    enabled: bool = Form(...),
    state: RuntimeState = Depends(get_runtime_state),
):
    state.set_ready(enabled)
    return JSONResponse(state_payload(request))


@router.post("/controls/crash", dependencies=[Depends(require_controls_enabled)])
def crash(request: Request, exit_code: int = Form(..., ge=0, le=255)):
    exit_fn = request.app.state.exit_fn
    cpu = getattr(request.app.state, "cpu_load", None)

    def _die() -> None:
        if cpu is not None:
            cpu.stop()
        exit_fn(exit_code)

    threading.Timer(CRASH_DELAY_SECONDS, _die).start()
    return JSONResponse(
        {"message": f"process will exit with code {exit_code} in {CRASH_DELAY_SECONDS}s",
         "exit_code": exit_code},
        status_code=202,
    )


@router.post("/controls/cpu", dependencies=[Depends(require_controls_enabled)])
def set_cpu_load(
    request: Request,
    enabled: bool = Form(...),
    workers: int = Form(1, ge=1, le=64),
    cpu: CpuLoad = Depends(get_cpu_load),
):
    if enabled:
        cpu.start(workers)
    else:
        cpu.stop()
    return JSONResponse(state_payload(request))
