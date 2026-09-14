from __future__ import annotations

import threading
import time


class RuntimeState:
    """Mutable, thread-safe flags that the health endpoints and controls share."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.started_at = time.time()
        self.live = True
        self.ready = True

    def set_live(self, enabled: bool) -> None:
        with self._lock:
            self.live = enabled

    def set_ready(self, enabled: bool) -> None:
        with self._lock:
            self.ready = enabled

    def uptime_seconds(self) -> float:
        return time.time() - self.started_at

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "live": self.live,
                "ready": self.ready,
                "started_at": self.started_at,
                "uptime_seconds": round(self.uptime_seconds(), 1),
            }
