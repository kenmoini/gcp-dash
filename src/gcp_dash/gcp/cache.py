from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CacheEntry:
    value: Any
    fetched_at: float | None  # wall-clock epoch seconds of last *attempt*
    error: str | None


class TTLCache:
    """Per-key TTL cache. A failing loader records the error but keeps the last good value."""

    def __init__(
        self,
        ttl_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        wall: Callable[[], float] = time.time,
    ) -> None:
        self.ttl = ttl_seconds
        self._clock = clock
        self._wall = wall
        self._lock = threading.Lock()
        self._entries: dict[str, CacheEntry] = {}
        self._expires: dict[str, float] = {}

    def get(self, key: str, loader: Callable[[], Any], force: bool = False) -> CacheEntry:
        with self._lock:
            entry = self._entries.get(key)
            if entry is not None and not force and self._clock() < self._expires.get(key, 0):
                return entry
            previous = entry.value if entry is not None else None
            try:
                entry = CacheEntry(value=loader(), fetched_at=self._wall(), error=None)
            except Exception as exc:
                entry = CacheEntry(value=previous, fetched_at=self._wall(), error=str(exc))
            self._entries[key] = entry
            self._expires[key] = self._clock() + self.ttl
            return entry

    def invalidate_all(self) -> None:
        with self._lock:
            self._entries.clear()
            self._expires.clear()
