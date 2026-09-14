from __future__ import annotations

import os

from fastapi import FastAPI

from gcp_dash.config import Settings
from gcp_dash.cpu_load import CpuLoad
from gcp_dash.routers import controls, health, runtime
from gcp_dash.state import RuntimeState


def create_app(settings: Settings | None = None, *, gcp_provider=None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(title="gcp-dash", version=settings.app_version)
    app.state.settings = settings
    app.state.runtime = RuntimeState()
    app.state.exit_fn = os._exit
    app.state.gcp_provider = gcp_provider  # used by Task 7
    app.state.cpu_load = CpuLoad()

    @app.on_event("shutdown")
    def _stop_cpu_load() -> None:
        app.state.cpu_load.stop()

    app.include_router(health.router)
    app.include_router(controls.router)
    app.include_router(runtime.router)
    return app


app = create_app()
