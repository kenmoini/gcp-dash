from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

from gcp_dash.gcp.cache import CacheEntry, TTLCache
from gcp_dash.gcp.provider import GcpProvider

log = logging.getLogger(__name__)

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
            if self._provider is not None:
                return self._provider
        provider = self._factory()
        with self._lock:
            if self._provider is None:
                self._provider = provider
            return self._provider

    @property
    def project_id(self) -> str | None:
        if self._provider is not None:
            return self._provider.project_id
        return self._configured_project

    def _load(self, kind: str, method: str):
        """Call the provider for one kind, logging outcome and duration.

        Provider construction happens inside the `try`, so a credentials failure is logged
        the same way as an API failure. The exception is re-raised so `TTLCache` records it
        for the UI; with GCP debug on, the log line carries the full exception chain.
        """
        log.debug("gcp fetch start kind=%s", kind)
        started = time.monotonic()
        try:
            result = getattr(self._get_provider(), method)()
        except Exception as exc:
            log.warning(
                "gcp fetch failed kind=%s after %.0f ms: %s: %s",
                kind,
                (time.monotonic() - started) * 1000,
                type(exc).__name__,
                exc,
                exc_info=log.isEnabledFor(logging.DEBUG),
            )
            raise
        count = len(result) if isinstance(result, list) else 1
        log.info(
            "gcp fetch ok kind=%s items=%d in %.0f ms",
            kind,
            count,
            (time.monotonic() - started) * 1000,
        )
        return result

    def fetch(self, kind: str, force: bool = False) -> CacheEntry:
        method = _METHODS[kind]  # KeyError for unknown kinds
        return self._cache.get(kind, lambda: self._load(kind, method), force=force)

    def refresh_all(self) -> None:
        self._cache.invalidate_all()
