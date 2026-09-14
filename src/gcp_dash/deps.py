from __future__ import annotations

from fastapi import Request

from gcp_dash.config import Settings
from gcp_dash.state import RuntimeState


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_runtime_state(request: Request) -> RuntimeState:
    return request.app.state.runtime
