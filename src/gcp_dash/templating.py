from __future__ import annotations

from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request", "").lower() == "true"


def render_controls(request: Request):
    from gcp_dash.routers.controls import state_payload  # local import avoids a cycle

    return templates.TemplateResponse(
        request, "partials/controls.html", {"state": state_payload(request)}
    )
