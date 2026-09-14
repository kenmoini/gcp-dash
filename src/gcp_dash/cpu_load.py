from __future__ import annotations

import multiprocessing
import os
import threading

_ctx = multiprocessing.get_context("spawn")


def _burn() -> None:  # runs in a child process; must be importable for spawn
    while True:
        pass


class CpuLoad:
    """Spawns N busy-loop processes so each can saturate one core (threads would share the GIL)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._procs: list[multiprocessing.Process] = []

    def start(self, workers: int) -> None:
        with self._lock:
            if self._procs:
                return
            workers = max(1, min(workers, os.cpu_count() or 1))
            for _ in range(workers):
                p = _ctx.Process(target=_burn, daemon=True)
                p.start()
                self._procs.append(p)

    def stop(self) -> None:
        with self._lock:
            for p in self._procs:
                p.terminate()
            for p in self._procs:
                p.join(timeout=2)
            self._procs = []

    def status(self) -> dict:
        with self._lock:
            alive = [p for p in self._procs if p.is_alive()]
            return {"active": bool(alive), "workers": len(alive)}
