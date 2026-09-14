from __future__ import annotations

from fastapi import APIRouter, Request

from gcp_dash import runtime_info
from gcp_dash.routers.controls import state_payload

router = APIRouter(tags=["runtime"])


@router.get("/api/runtime")
def api_runtime(request: Request) -> dict:
    data = runtime_info.to_dict(runtime_info.collect())
    data["state"] = state_payload(request)
    return data
