from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from gcp_dash.config import Settings
from gcp_dash.cpu_load import CpuLoad
from gcp_dash.gcp.cache import TTLCache
from gcp_dash.gcp.provider import LiveGcpProvider
from gcp_dash.gcp.service import GcpService
from gcp_dash.logging_setup import configure_logging
from gcp_dash.routers import controls, gcp, health, pages, runtime
from gcp_dash.state import RuntimeState
from gcp_dash.templating import STATIC_DIR

log = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, *, gcp_provider=None) -> FastAPI:
    settings = settings or Settings.from_env()
    configure_logging(settings)
    log.info(
        "gcp-dash %s starting: project=%s cache_ttl=%ss controls=%s log_level=%s gcp_debug=%s",
        settings.app_version,
        settings.gcp_project,
        settings.gcp_cache_ttl_seconds,
        settings.controls_enabled,
        settings.log_level,
        settings.gcp_debug,
    )

    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        yield
        app.state.cpu_load.stop()

    app = FastAPI(title="gcp-dash", version=settings.app_version, lifespan=_lifespan)
    app.state.settings = settings
    app.state.runtime = RuntimeState()
    app.state.exit_fn = os._exit
    if gcp_provider is not None:
        factory = lambda: gcp_provider
    else:
        factory = lambda: LiveGcpProvider(settings.gcp_project)
    app.state.gcp = GcpService(TTLCache(settings.gcp_cache_ttl_seconds), factory, settings.gcp_project)
    app.state.cpu_load = CpuLoad()

    app.include_router(health.router)
    app.include_router(controls.router)
    app.include_router(runtime.router)
    app.include_router(gcp.router)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.include_router(pages.router)
    return app


app = create_app()
