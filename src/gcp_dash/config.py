from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from gcp_dash import __version__

_TRUE = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    port: int = 8080
    gcp_project: str | None = None
    gcp_cache_ttl_seconds: int = 60
    controls_enabled: bool = True
    app_version: str = __version__

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if env is None else env
        return cls(
            port=int(env.get("PORT", "8080")),
            gcp_project=env.get("GCP_PROJECT") or None,
            gcp_cache_ttl_seconds=int(env.get("GCP_CACHE_TTL_SECONDS", "60")),
            controls_enabled=env.get("CONTROLS_ENABLED", "true").strip().lower() in _TRUE,
        )
