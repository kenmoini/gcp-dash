from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass

from gcp_dash import __version__

_TRUE = {"1", "true", "yes", "on"}


def _parse_log_level(value: str) -> str:
    name = value.strip().upper()
    names = logging.getLevelNamesMapping()
    if name not in names:
        raise ValueError(f"LOG_LEVEL must be one of {sorted(names)}, got {value!r}")
    return name


@dataclass(frozen=True)
class Settings:
    port: int = 8080
    gcp_project: str | None = None
    gcp_cache_ttl_seconds: int = 60
    controls_enabled: bool = True
    log_level: str = "INFO"
    gcp_debug: bool = False
    app_version: str = __version__

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if env is None else env
        return cls(
            port=int(env.get("PORT", "8080")),
            gcp_project=env.get("GCP_PROJECT") or None,
            gcp_cache_ttl_seconds=int(env.get("GCP_CACHE_TTL_SECONDS", "60")),
            controls_enabled=env.get("CONTROLS_ENABLED", "true").strip().lower() in _TRUE,
            log_level=_parse_log_level(env.get("LOG_LEVEL", "INFO")),
            gcp_debug=env.get("GCP_DEBUG", "false").strip().lower() in _TRUE,
        )
