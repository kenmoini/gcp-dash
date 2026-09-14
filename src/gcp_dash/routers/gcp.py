from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.concurrency import run_in_threadpool

from gcp_dash.deps import get_gcp_service
from gcp_dash.gcp.cache import CacheEntry
from gcp_dash.gcp.service import KINDS, GcpService

router = APIRouter(prefix="/api/gcp", tags=["gcp"])


def _serialize(value):
    if value is None:
        return None
    if is_dataclass(value):
        return asdict(value)
    return [asdict(v) for v in value]


def entry_to_payload(kind: str, entry: CacheEntry) -> dict:
    fetched = (
        datetime.fromtimestamp(entry.fetched_at, tz=UTC).isoformat()
        if entry.fetched_at
        else None
    )
    return {"kind": kind, "fetched_at": fetched, "error": entry.error, "items": _serialize(entry.value)}


def validate_kind(kind: str) -> str:
    if kind not in KINDS:
        raise HTTPException(status_code=404, detail=f"unknown kind '{kind}'")
    return kind


@router.post("/refresh", status_code=204)
def refresh(svc: GcpService = Depends(get_gcp_service)) -> Response:
    svc.refresh_all()
    return Response(status_code=204)


@router.get("/{kind}")
async def get_kind(
    kind: str = Depends(validate_kind),
    refresh: bool = False,
    svc: GcpService = Depends(get_gcp_service),
) -> dict:
    entry = await run_in_threadpool(svc.fetch, kind, refresh)
    return entry_to_payload(kind, entry)
