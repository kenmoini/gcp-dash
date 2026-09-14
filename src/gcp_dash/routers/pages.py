from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool

from gcp_dash import runtime_info
from gcp_dash.deps import get_gcp_service
from gcp_dash.gcp.service import GcpService
from gcp_dash.routers.controls import state_payload
from gcp_dash.routers.gcp import validate_kind
from gcp_dash.templating import render_controls, templates

router = APIRouter(include_in_schema=False)

PANELS = [
    ("project", "Project"),
    ("instances", "Compute Engine instances"),
    ("buckets", "Cloud Storage buckets"),
    ("networks", "VPC networks"),
    ("subnetworks", "Subnetworks"),
    ("firewalls", "Firewall rules"),
]


def _base(request: Request, active: str) -> dict:
    return {"active": active, "version": request.app.state.settings.app_version}


def _runtime_context(request: Request) -> dict:
    return {"info": runtime_info.collect(), "state": state_payload(request)}


@router.get("/")
def index(request: Request):
    ctx = _base(request, "runtime") | _runtime_context(request)
    return templates.TemplateResponse(request, "index.html", ctx)


@router.get("/partials/runtime")
def partial_runtime(request: Request):
    return templates.TemplateResponse(request, "partials/runtime.html", _runtime_context(request))


@router.get("/partials/controls")
def partial_controls(request: Request):
    return render_controls(request)


@router.get("/gcp")
def gcp_page(request: Request, svc: GcpService = Depends(get_gcp_service)):
    ctx = _base(request, "gcp") | {
        "project_id": svc.project_id,
        "ttl": request.app.state.settings.gcp_cache_ttl_seconds,
        "panels": PANELS,
    }
    return templates.TemplateResponse(request, "gcp.html", ctx)


@router.get("/partials/gcp/{kind}")
async def partial_gcp(
    request: Request,
    kind: str = Depends(validate_kind),
    refresh: bool = False,
    svc: GcpService = Depends(get_gcp_service),
):
    entry = await run_in_threadpool(svc.fetch, kind, refresh)
    fetched_at = (
        datetime.fromtimestamp(entry.fetched_at, tz=UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        if entry.fetched_at
        else None
    )
    ctx = {"kind": kind, "entry": entry, "fetched_at": fetched_at}
    return templates.TemplateResponse(request, f"partials/gcp_{kind}.html", ctx)
