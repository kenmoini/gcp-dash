from __future__ import annotations

import threading
from collections.abc import Callable

from gcp_dash.gcp.cache import CacheEntry, TTLCache
from gcp_dash.gcp.provider import GcpProvider

KINDS: tuple[str, ...] = ("project", "instances", "buckets", "networks", "subnetworks", "firewalls")

_METHODS = {
    "project": "get_project",
    "instances": "list_instances",
    "buckets": "list_buckets",
    "networks": "list_networks",
    "subnetworks": "list_subnetworks",
    "firewalls": "list_firewalls",
}


class GcpService:
    """Resolves a provider lazily (so missing credentials surface as panel errors) and caches per kind."""

    def __init__(
        self,
        cache: TTLCache,
        provider_factory: Callable[[], GcpProvider],
        configured_project: str | None,
    ) -> None:
        self._cache = cache
        self._factory = provider_factory
        self._configured_project = configured_project
        self._provider: GcpProvider | None = None
        self._lock = threading.Lock()

    def _get_provider(self) -> GcpProvider:
        with self._lock:
            if self._provider is None:
                self._provider = self._factory()
            return self._provider

    @property
    def project_id(self) -> str | None:
        if self._provider is not None:
            return self._provider.project_id
        return self._configured_project

    def fetch(self, kind: str, force: bool = False) -> CacheEntry:
        method = _METHODS[kind]  # KeyError for unknown kinds
        return self._cache.get(kind, lambda: getattr(self._get_provider(), method)(), force=force)

    def refresh_all(self) -> None:
        self._cache.invalidate_all()
