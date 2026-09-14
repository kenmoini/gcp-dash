from __future__ import annotations

import os

from fastapi import FastAPI

from gcp_dash.config import Settings
from gcp_dash.routers import health
from gcp_dash.state import RuntimeState


def create_app(settings: Settings | None = None, *, gcp_provider=None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(title="gcp-dash", version=settings.app_version)
    app.state.settings = settings
    app.state.runtime = RuntimeState()
    app.state.exit_fn = os._exit
    app.state.gcp_provider = gcp_provider  # used by Task 7

    app.include_router(health.router)
    return app


app = create_app()
