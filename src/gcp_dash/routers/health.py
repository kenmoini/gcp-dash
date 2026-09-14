from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from gcp_dash.deps import get_runtime_state
from gcp_dash.state import RuntimeState

router = APIRouter(prefix="/healthz", tags=["health"])


def _probe(ok: bool, name: str) -> JSONResponse:
    if ok:
        return JSONResponse({"status": "ok"})
    return JSONResponse(
        {"status": "failing", "reason": f"{name} disabled via controls"}, status_code=503
    )


@router.get("/live")
def live(state: RuntimeState = Depends(get_runtime_state)) -> JSONResponse:
    return _probe(state.live, "liveness")


@router.get("/ready")
def ready(state: RuntimeState = Depends(get_runtime_state)) -> JSONResponse:
    return _probe(state.ready, "readiness")
