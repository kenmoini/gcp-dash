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
    """Per-key TTL cache. A failing loader records the error but keeps the last good value.

    Each key is guarded by its own lock, so a slow loader for one key never blocks a
    read or a load for a different key. A short-lived global lock protects only the
    bookkeeping: creating a key's lock, and clearing the cache in invalidate_all. The
    same key is still loaded at most once at a time.
    """

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
        self._key_locks: dict[str, threading.Lock] = {}
        self._entries: dict[str, CacheEntry] = {}
        self._expires: dict[str, float] = {}

    def _lock_for(self, key: str) -> threading.Lock:
        with self._lock:
            lock = self._key_locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._key_locks[key] = lock
            return lock

    def get(self, key: str, loader: Callable[[], Any], force: bool = False) -> CacheEntry:
        lock = self._lock_for(key)
        with lock:
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
