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
    read or a load for a different key. The same key is still loaded at most once at
    a time. A short-lived global lock protects the bookkeeping: creating a key's lock,
    every read or write of the `_entries`/`_expires` dicts, and the epoch counter. The
    epoch counter guards against a race with `invalidate_all`: a load that starts
    before an `invalidate_all` call but finishes after it must not write its (now
    stale) result back into the cache, even though it still returns that fresh
    `CacheEntry` to its own caller.
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
        self._epoch = 0

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
            # All reads of _entries/_expires/_epoch happen under the global lock, so
            # they never race with invalidate_all's writes to those same structures.
            with self._lock:
                entry = self._entries.get(key)
                fresh = entry is not None and not force and self._clock() < self._expires.get(key, 0)
                epoch_at_start = self._epoch
            if fresh:
                return entry
            previous = entry.value if entry is not None else None
            try:
                entry = CacheEntry(value=loader(), fetched_at=self._wall(), error=None)
            except Exception as exc:  # noqa: BLE001 - any loader failure must become a cache error, not a 500
                entry = CacheEntry(value=previous, fetched_at=self._wall(), error=str(exc))
            with self._lock:
                # If invalidate_all ran while loader() was in flight, the epoch moved
                # on. Skip the write-back so we don't resurrect a stale entry, but
                # still hand this fresh CacheEntry to our own caller.
                if self._epoch == epoch_at_start:
                    self._entries[key] = entry
                    self._expires[key] = self._clock() + self.ttl
            return entry

    def invalidate_all(self) -> None:
        with self._lock:
            self._entries.clear()
            self._expires.clear()
            self._epoch += 1
